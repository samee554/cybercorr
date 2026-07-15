"""Canonical Pydantic models for CyberCorr data exchanged across the API."""

from datetime import datetime

from pydantic import BaseModel


class CyberEvent(BaseModel):
    """A raw cybersecurity telemetry event."""

    event_id: str
    timestamp: datetime
    event_type: str
    user_id: str
    ip_address: str
    device_id: str
    severity: int
    metadata: dict


class TransactionEvent(BaseModel):
    """A raw transaction or account activity event."""

    event_id: str
    timestamp: datetime
    tx_type: str
    user_id: str
    ip_address: str
    device_id: str
    amount: float
    destination: str
    metadata: dict


class AlertExplanation(BaseModel):
    """A plain-English explanation generated for a correlated alert."""

    threat_summary: str
    risk_level: str
    risk_reason: str
    attack_pattern: str
    recommended_action: str
    false_positive_likelihood: int
    generated_at: datetime


class CorrelatedAlert(BaseModel):
    """A correlated cybersecurity and transaction alert."""

    alert_id: str
    created_at: datetime
    user_id: str
    cyber_events: list[CyberEvent]
    transaction_events: list[TransactionEvent]
    correlation_score: float
    anomaly_score: float
    quantum_risk_score: int
    overall_risk: str
    explanation: AlertExplanation | None
    status: str


class StatusUpdateRequest(BaseModel):
    """Request body for updating an alert's status."""

    status: str

