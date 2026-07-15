"""Thread-safe alert storage, pagination, status updates, auto-expiration, and AI explanations."""

import asyncio
import logging
import threading
from datetime import datetime, timedelta, timezone

from backend.config import ALERT_EXPIRY_MINUTES, OPEN_ALERT_STATUSES, AUTO_EXPIRE_LOOP_INTERVAL_SECONDS
from backend.models import AlertExplanation, CorrelatedAlert, CyberEvent, TransactionEvent

logger = logging.getLogger(__name__)


class AlertStore:
    """A thread-safe in-memory store for correlated alerts."""

    def __init__(self) -> None:
        """Initialize the alert store with a thread lock and empty mapping."""
        self._alerts: dict[str, CorrelatedAlert] = {}
        self._lock = threading.Lock()
        self.broadcast_queue: asyncio.Queue[CorrelatedAlert] = asyncio.Queue()

    def add_alert(self, alert: CorrelatedAlert) -> None:
        """Add a new alert to the store and enqueue it for WebSocket broadcast."""
        with self._lock:
            self._alerts[alert.alert_id] = alert
        self.broadcast_queue.put_nowait(alert)
        logger.info(f"Alert {alert.alert_id} added to store.")
        self._trigger_auto_explain(alert)

    def update_alert(
        self,
        alert_id: str,
        new_cyber_events: list[CyberEvent],
        new_tx_events: list[TransactionEvent],
    ) -> CorrelatedAlert | None:
        """Merge new events into an existing alert, recalculate scores, and broadcast."""
        # Local imports to avoid circular dependency with correlator
        from backend.correlator import compute_correlation_score, _overall_risk
        from backend.fraud_ml import alert_anomaly_score
        from backend.quantum_detector import record_quantum_scan

        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None:
                return None

            # Merge cyber events uniquely by event_id
            existing_cyber_ids = {e.event_id for e in alert.cyber_events}
            for event in new_cyber_events:
                if event.event_id not in existing_cyber_ids:
                    alert.cyber_events.append(event)

            # Merge transaction events uniquely by event_id
            existing_tx_ids = {e.event_id for e in alert.transaction_events}
            for event in new_tx_events:
                if event.event_id not in existing_tx_ids:
                    alert.transaction_events.append(event)

            # Recalculate scores and risk
            alert.correlation_score = compute_correlation_score(
                alert.cyber_events, alert.transaction_events
            )
            alert.anomaly_score = alert_anomaly_score(alert.transaction_events)
            quantum_result = record_quantum_scan(alert.cyber_events)
            alert.quantum_risk_score = int(quantum_result["quantum_risk_score"])
            alert.overall_risk = _overall_risk(alert.correlation_score)

        self.broadcast_queue.put_nowait(alert)
        logger.info(f"Alert {alert_id} updated and enqueued for broadcast.")
        self._trigger_auto_explain(alert)
        return alert

    def update_status(self, alert_id: str, status: str) -> CorrelatedAlert | None:
        """Update the status of an alert and enqueue it for WebSocket broadcast."""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None:
                return None
            alert.status = status

        self.broadcast_queue.put_nowait(alert)
        logger.info(f"Alert {alert_id} status updated to {status}.")
        return alert

    def set_explanation(
        self, alert_id: str, explanation: AlertExplanation
    ) -> CorrelatedAlert | None:
        """Set the explanation for an alert and enqueue it for WebSocket broadcast."""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None:
                return None
            alert.explanation = explanation

        self.broadcast_queue.put_nowait(alert)
        logger.info(f"Alert {alert_id} explanation updated and enqueued for broadcast.")
        return alert

    def get_alerts(
        self, page: int, limit: int, risk_filter: str | None = None
    ) -> dict[str, object]:
        """Return a filtered, paginated list of alerts, sorted by newest first."""
        with self._lock:
            alerts = list(self._alerts.values())

        if risk_filter:
            alerts = [a for a in alerts if a.overall_risk == risk_filter.upper()]

        # Sort newest first
        alerts.sort(key=lambda a: a.created_at, reverse=True)

        start_index = (page - 1) * limit
        paginated_alerts = alerts[start_index : start_index + limit]

        return {
            "alerts": paginated_alerts,
            "total": len(alerts),
            "page": page,
            "limit": limit,
        }

    def auto_expire(self) -> None:
        """Mark alerts older than ALERT_EXPIRY_MINUTES as resolved."""
        now = datetime.now(timezone.utc)
        expiry_threshold = now - timedelta(minutes=ALERT_EXPIRY_MINUTES)
        expired_alerts = []

        with self._lock:
            for alert in self._alerts.values():
                if alert.status in OPEN_ALERT_STATUSES:
                    alert_time = alert.created_at
                    if alert_time.tzinfo is None:
                        alert_time = alert_time.replace(tzinfo=timezone.utc)
                    if alert_time < expiry_threshold:
                        alert.status = "resolved"
                        expired_alerts.append(alert)

        for alert in expired_alerts:
            self.broadcast_queue.put_nowait(alert)
            logger.info(f"Alert {alert.alert_id} automatically expired to resolved.")

    async def auto_expire_loop(self) -> None:
        """Asynchronous background loop that runs auto_expire periodically."""
        while True:
            try:
                self.auto_expire()
            except Exception as exc:
                logger.error(f"Error in auto_expire loop: {exc}")
            await asyncio.sleep(AUTO_EXPIRE_LOOP_INTERVAL_SECONDS)

    def values(self) -> list[CorrelatedAlert]:
        """Return a list of all alerts in the store."""
        with self._lock:
            return list(self._alerts.values())

    def get(self, alert_id: str) -> CorrelatedAlert | None:
        """Retrieve a single alert by its ID."""
        with self._lock:
            return self._alerts.get(alert_id)

    def _trigger_auto_explain(self, alert: CorrelatedAlert) -> None:
        """Trigger AI explanation in the background if the alert is MEDIUM/HIGH/CRITICAL and lacks one."""
        if alert.overall_risk in ("MEDIUM", "HIGH", "CRITICAL") and alert.explanation is None:
            from backend.explainer import EXPLAINER

            async def explain_task() -> None:
                try:
                    logger.info(f"Triggering background auto-explain for alert {alert.alert_id}")
                    explanation = await EXPLAINER.explain(alert)
                    self.set_explanation(alert.alert_id, explanation)
                except Exception as exc:
                    logger.error(f"Error in background auto-explain for alert {alert.alert_id}: {exc}")

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(explain_task())
            except RuntimeError:
                # If no running event loop is available, log and skip background task execution
                logger.warning(f"No active event loop found to run auto-explain for alert {alert.alert_id}")


ALERT_STORE = AlertStore()
