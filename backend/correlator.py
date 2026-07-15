"""Time-window correlation, entity graph construction, and alert storage."""

from datetime import datetime, timedelta, timezone
from typing import TypeVar
from uuid import uuid4

import networkx as nx

from backend.config import (
    ALERT_DEDUP_WINDOW_MINUTES,
    ATTACK_SEVERITY_MAX,
    CORRELATION_RISK_THRESHOLDS,
    CORRELATION_SCORE_MAX,
    CORRELATION_SCORE_WEIGHTS,
    CORRELATION_WINDOW_SECONDS,
    CYBER_EVENTS_FOR_MAX_SCORE,
    DEFAULT_ANOMALY_SCORE,
    MAX_GRAPH_NODES,
    OPEN_ALERT_STATUSES,
    TX_BASELINE_STDDEV_MULTIPLIER,
)
from backend.fraud_ml import alert_anomaly_score, score_transaction
from backend.models import CorrelatedAlert, CyberEvent, TransactionEvent
from backend.quantum_detector import record_quantum_scan
from backend.simulator import EVENT_STORE, USERS, Event

from backend.alert_manager import ALERT_STORE

EventType = TypeVar("EventType", CyberEvent, TransactionEvent)


def _utc_timestamp(timestamp: datetime) -> datetime:
    """Return a timestamp normalized to UTC for reliable time comparisons."""
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def time_window_join(
    user_id: str,
    ip_address: str,
    device_id: str,
    timestamp: datetime,
) -> list[CyberEvent]:
    """Find matching cyber events within the configured correlation window."""
    window_start = _utc_timestamp(timestamp) - timedelta(seconds=CORRELATION_WINDOW_SECONDS)
    matching_events: list[CyberEvent] = []

    for event in EVENT_STORE:
        if not isinstance(event, CyberEvent):
            continue

        event_timestamp = _utc_timestamp(event.timestamp)
        matches_entity = (
            event.user_id == user_id
            or event.ip_address == ip_address
            or event.device_id == device_id
        )
        if matches_entity and window_start <= event_timestamp <= _utc_timestamp(timestamp):
            matching_events.append(event)

    return matching_events


def _add_weighted_edge(graph: nx.DiGraph, source: str, target: str, relationship: str) -> None:
    """Create or increment a typed relationship edge in the entity graph."""
    if graph.has_edge(source, target):
        graph[source][target]["weight"] += 1
        return

    graph.add_edge(source, target, relationship=relationship, weight=1)


def build_entity_graph() -> nx.DiGraph:
    """Build a bounded directed graph of users, IP addresses, and devices."""
    graph = nx.DiGraph()

    for event in EVENT_STORE:
        user_node = f"user:{event.user_id}"
        ip_node = f"ip:{event.ip_address}"
        device_node = f"device:{event.device_id}"
        graph.add_node(user_node, type="user", value=event.user_id)
        graph.add_node(ip_node, type="ip", value=event.ip_address)
        graph.add_node(device_node, type="device", value=event.device_id)
        _add_weighted_edge(graph, user_node, ip_node, "connected_from")
        _add_weighted_edge(graph, user_node, device_node, "used_device")
        _add_weighted_edge(graph, ip_node, device_node, "seen_together")

    if graph.number_of_nodes() <= MAX_GRAPH_NODES:
        return graph

    highest_degree_nodes = sorted(graph.degree, key=lambda item: item[1], reverse=True)
    selected_nodes = [node for node, _ in highest_degree_nodes[:MAX_GRAPH_NODES]]
    return graph.subgraph(selected_nodes).copy()


def _transaction_amount_score(tx_events: list[TransactionEvent]) -> float:
    """Score transaction amounts according to each user's simulated baseline."""
    if not tx_events:
        return DEFAULT_ANOMALY_SCORE

    scores: list[float] = []
    for event in tx_events:
        user = USERS.get(event.user_id)
        if user is None:
            continue
        mean, stddev = user.typical_tx_amount
        denominator = stddev * TX_BASELINE_STDDEV_MULTIPLIER
        z_score = (event.amount - mean) / denominator if denominator else DEFAULT_ANOMALY_SCORE
        scores.append(max(DEFAULT_ANOMALY_SCORE, min(z_score, CORRELATION_SCORE_MAX)))

    return sum(scores) / len(scores) if scores else DEFAULT_ANOMALY_SCORE


def _entity_overlap_score(
    cyber_events: list[CyberEvent],
    tx_events: list[TransactionEvent],
) -> float:
    """Measure how often related cyber and transaction events share an IP or device."""
    if not cyber_events or not tx_events:
        return DEFAULT_ANOMALY_SCORE

    matches = 0
    comparisons = 0
    for cyber_event in cyber_events:
        for tx_event in tx_events:
            comparisons += 1
            if (
                cyber_event.ip_address == tx_event.ip_address
                or cyber_event.device_id == tx_event.device_id
            ):
                matches += 1

    return matches / comparisons if comparisons else DEFAULT_ANOMALY_SCORE


def compute_correlation_score(
    cyber_events: list[CyberEvent],
    tx_events: list[TransactionEvent],
) -> float:
    """Compute the architecture-defined weighted correlation score from zero to one."""
    if not cyber_events or not tx_events:
        return DEFAULT_ANOMALY_SCORE

    count_score = min(len(cyber_events) / CYBER_EVENTS_FOR_MAX_SCORE, CORRELATION_SCORE_MAX)
    severity_score = sum(event.severity for event in cyber_events) / (
        len(cyber_events) * ATTACK_SEVERITY_MAX
    )
    amount_score = _transaction_amount_score(tx_events)
    overlap_score = _entity_overlap_score(cyber_events, tx_events)
    count_weight, severity_weight, amount_weight, overlap_weight = CORRELATION_SCORE_WEIGHTS
    score = (
        count_score * count_weight
        + severity_score * severity_weight
        + amount_score * amount_weight
        + overlap_score * overlap_weight
    )
    return min(score, CORRELATION_SCORE_MAX)


def _overall_risk(correlation_score: float) -> str:
    """Map a correlation score to the configured alert risk level."""
    for threshold, risk_level in CORRELATION_RISK_THRESHOLDS:
        if correlation_score > threshold:
            return risk_level
    return "LOW"


def create_correlated_alert(
    user_id: str,
    cyber_events: list[CyberEvent],
    tx_events: list[TransactionEvent],
) -> CorrelatedAlert:
    """Assemble a new correlated alert with fraud and quantum intelligence scores."""
    correlation_score = compute_correlation_score(cyber_events, tx_events)
    anomaly_score = alert_anomaly_score(tx_events)
    quantum_result = record_quantum_scan(cyber_events)
    return CorrelatedAlert(
        alert_id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
        user_id=user_id,
        cyber_events=cyber_events,
        transaction_events=tx_events,
        correlation_score=correlation_score,
        anomaly_score=anomaly_score,
        quantum_risk_score=int(quantum_result["quantum_risk_score"]),
        overall_risk=_overall_risk(correlation_score),
        explanation=None,
        status="new",
    )
def _open_alert_for_user(user_id: str, now: datetime) -> CorrelatedAlert | None:
    """Find a recent alert for the same user that is still open."""
    dedup_start = now - timedelta(minutes=ALERT_DEDUP_WINDOW_MINUTES)
    open_alerts = (
        alert
        for alert in ALERT_STORE.values()
        if alert.user_id == user_id
        and alert.status in OPEN_ALERT_STATUSES
        and _utc_timestamp(alert.created_at) >= dedup_start
    )
    return max(open_alerts, key=lambda alert: _utc_timestamp(alert.created_at), default=None)


def correlate_transaction(transaction_event: TransactionEvent) -> CorrelatedAlert | None:
    """Create or update an alert when a transaction matches recent cyber activity."""
    score_transaction(transaction_event)
    cyber_events = time_window_join(
        transaction_event.user_id,
        transaction_event.ip_address,
        transaction_event.device_id,
        transaction_event.timestamp,
    )
    if not cyber_events:
        return None

    existing_alert = _open_alert_for_user(transaction_event.user_id, datetime.now(timezone.utc))
    if existing_alert is None:
        alert = create_correlated_alert(
            transaction_event.user_id,
            cyber_events,
            [transaction_event],
        )
        ALERT_STORE.add_alert(alert)
        return alert

    return ALERT_STORE.update_alert(
        existing_alert.alert_id,
        cyber_events,
        [transaction_event],
    )


def process_event(event: Event) -> CorrelatedAlert | None:
    """Process a newly stored event, correlating it only when it is a transaction."""
    if isinstance(event, TransactionEvent):
        return correlate_transaction(event)
    return None


def graph_data() -> dict[str, list[dict[str, object]]]:
    """Serialize the entity graph into frontend force-graph nodes and links."""
    graph = build_entity_graph()
    nodes = [
        {"id": node_id, "type": attributes["type"], "label": attributes["value"]}
        for node_id, attributes in graph.nodes(data=True)
    ]
    links = [
        {
            "source": source,
            "target": target,
            "relationship": attributes["relationship"],
            "weight": attributes["weight"],
        }
        for source, target, attributes in graph.edges(data=True)
    ]
    return {"nodes": nodes, "links": links}
