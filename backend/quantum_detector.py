"""Rule-based detection of Harvest Now, Decrypt Later indicators."""

from collections import deque
from datetime import datetime, timedelta, timezone

from backend.config import (
    EVENT_STORE_MAXLEN,
    HEATMAP_BUCKET_COUNT,
    QUANTUM_CRITICAL_THRESHOLD,
    QUANTUM_HIGH_THRESHOLD,
    QUANTUM_MEDIUM_THRESHOLD,
    QUANTUM_SCORE_MAX,
    QUANTUM_TREND_HOURS,
)
from backend.models import CyberEvent

HNDL_RULES = (
    {
        "id": "Q001",
        "name": "Bulk Encrypted Exfiltration",
        "event_type": "bulk_encrypted_exfil",
        "weight": 35,
        "description": "Large volumes of encrypted data leaving network boundary",
    },
    {
        "id": "Q002",
        "name": "RSA Key Exchange Detected",
        "event_type": "tls_rsa_key_exchange",
        "weight": 20,
        "description": "TLS session using quantum-vulnerable RSA key exchange",
    },
    {
        "id": "Q003",
        "name": "TLS Downgrade Attempt",
        "event_type": "tls_downgrade",
        "weight": 25,
        "description": "Forced downgrade to cipher suite vulnerable to quantum decryption",
    },
    {
        "id": "Q004",
        "name": "Off-Hours Archive Download",
        "event_type": "archive_download_off_hours",
        "weight": 15,
        "description": "Encrypted archive downloaded outside business hours",
    },
    {
        "id": "Q005",
        "name": "Repeated Encrypted Blob Transfer",
        "event_type": "repeated_blob_transfer",
        "weight": 30,
        "description": "Same encrypted payload transferred multiple times (HNDL staging)",
    },
)


class QuantumDetector:
    """Apply the configured HNDL rules to a collection of cyber events."""

    def scan(self, events: list[CyberEvent]) -> dict[str, object]:
        """Return matched HNDL rules, capped score, and the resulting risk level."""
        event_types = {event.event_type for event in events}
        triggered_rules = [rule for rule in HNDL_RULES if rule["event_type"] in event_types]
        quantum_risk_score = min(
            sum(int(rule["weight"]) for rule in triggered_rules),
            QUANTUM_SCORE_MAX,
        )
        return {
            "quantum_risk_score": quantum_risk_score,
            "triggered_rules": triggered_rules,
            "risk_level": self._risk_level(quantum_risk_score),
        }

    def _risk_level(self, score: int) -> str:
        """Map a quantum risk score to the configured risk level."""
        if score >= QUANTUM_CRITICAL_THRESHOLD:
            return "CRITICAL"
        if score >= QUANTUM_HIGH_THRESHOLD:
            return "HIGH"
        if score >= QUANTUM_MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "LOW"


QUANTUM_DETECTOR = QuantumDetector()
QUANTUM_SCORE_HISTORY: deque[tuple[datetime, dict[str, object]]] = deque(maxlen=EVENT_STORE_MAXLEN)


def record_quantum_scan(events: list[CyberEvent]) -> dict[str, object]:
    """Scan alert events and record the result for the quantum-risk trend."""
    result = QUANTUM_DETECTOR.scan(events)
    QUANTUM_SCORE_HISTORY.append((datetime.now(timezone.utc), result))
    return result


def quantum_summary() -> dict[str, object]:
    """Return the latest quantum score, triggered rules, and a 24-hour hourly trend."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=QUANTUM_TREND_HOURS)
    hourly_scores: dict[datetime, list[int]] = {}
    latest_result: dict[str, object] = {
        "quantum_risk_score": 0,
        "triggered_rules": [],
        "risk_level": "LOW",
    }
    for timestamp, result in QUANTUM_SCORE_HISTORY:
        if timestamp < window_start:
            continue
        latest_result = result
        hour = timestamp.replace(minute=0, second=0, microsecond=0)
        hourly_scores.setdefault(hour, []).append(int(result["quantum_risk_score"]))

    trend = [
        {"timestamp": hour.isoformat(), "quantum_risk_score": max(hourly_scores.get(hour, [0]))}
        for hour in [
            now.replace(minute=0, second=0, microsecond=0)
            - timedelta(hours=offset)
            for offset in range(HEATMAP_BUCKET_COUNT - 1, -1, -1)
        ]
    ]
    return {
        **latest_result,
        "current_score": latest_result["quantum_risk_score"],
        "top_triggered_rules": latest_result["triggered_rules"],
        "trend": trend,
    }
