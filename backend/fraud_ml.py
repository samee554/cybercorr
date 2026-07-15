"""Isolation Forest fraud scoring and transaction behaviour baselines."""

import math
import random
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.ensemble import IsolationForest

from backend.config import (
    ANOMALY_CONTAMINATION,
    EARTH_RADIUS_KM,
    EVENT_STORE_MAXLEN,
    FRAUD_ANOMALY_THRESHOLD,
    FRAUD_FEATURE_COUNT,
    FRAUD_TRAINING_SAMPLES,
    HEATMAP_BUCKET_MINUTES,
    HEATMAP_BUCKET_COUNT,
    HEATMAP_WINDOW_HOURS,
    HOURS_PER_DAY,
    ISOLATION_FOREST_ESTIMATORS,
    MIN_TRANSACTION_AMOUNT,
    RANDOM_SEED,
    USER_BASELINE_HISTORY_SIZE,
)
from backend.models import CyberEvent, TransactionEvent
from backend.simulator import EVENT_STORE, USERS


class UserBaseline:
    """Maintain a rolling transaction amount baseline for one simulated user."""

    def __init__(self) -> None:
        """Initialize an empty bounded history of transaction amounts."""
        self.amounts: deque[float] = deque(maxlen=USER_BASELINE_HISTORY_SIZE)

    @property
    def mean(self) -> float:
        """Return the rolling mean transaction amount."""
        return float(np.mean(self.amounts)) if self.amounts else MIN_TRANSACTION_AMOUNT

    @property
    def stddev(self) -> float:
        """Return the rolling standard deviation of transaction amounts."""
        return float(np.std(self.amounts)) if self.amounts else MIN_TRANSACTION_AMOUNT

    def add(self, amount: float) -> None:
        """Append a transaction amount to the bounded baseline history."""
        self.amounts.append(amount)


USER_BASELINES: dict[str, UserBaseline] = defaultdict(UserBaseline)
USER_TRANSACTION_HISTORY: dict[str, deque[TransactionEvent]] = defaultdict(
    lambda: deque(maxlen=USER_BASELINE_HISTORY_SIZE)
)
TRANSACTION_SCORES: dict[str, dict[str, object]] = {}
FRAUD_SCORE_HISTORY: deque[tuple[datetime, float]] = deque(maxlen=EVENT_STORE_MAXLEN)


def _utc_timestamp(timestamp: datetime) -> datetime:
    """Normalize an event timestamp to UTC for consistent comparisons."""
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _haversine_distance_km(
    source_geo: tuple[float, float],
    destination_geo: tuple[float, float],
) -> float:
    """Calculate the great-circle distance between two latitude/longitude pairs."""
    source_latitude, source_longitude = map(math.radians, source_geo)
    destination_latitude, destination_longitude = map(math.radians, destination_geo)
    latitude_delta = destination_latitude - source_latitude
    longitude_delta = destination_longitude - source_longitude
    haversine_value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(source_latitude)
        * math.cos(destination_latitude)
        * math.sin(longitude_delta / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(haversine_value))


def _failed_logins_last_hour(tx_event: TransactionEvent) -> int:
    """Count failed logins for the transaction user during the prior hour."""
    event_time = _utc_timestamp(tx_event.timestamp)
    lookback_start = event_time - timedelta(hours=1)
    return sum(
        isinstance(event, CyberEvent)
        and event.user_id == tx_event.user_id
        and event.event_type == "failed_login"
        and lookback_start <= _utc_timestamp(event.timestamp) <= event_time
        for event in EVENT_STORE
    )


def _ip_geo(tx_event: TransactionEvent, home_geo: tuple[float, float]) -> tuple[float, float]:
    """Read a supplied IP location or use the home location for normal traffic."""
    metadata_geo = tx_event.metadata.get("ip_geo")
    if isinstance(metadata_geo, dict) and {"lat", "lon"}.issubset(metadata_geo):
        return float(metadata_geo["lat"]), float(metadata_geo["lon"])
    return home_geo


def extract_features(
    tx_event: TransactionEvent,
    user_history: list[TransactionEvent] | deque[TransactionEvent],
) -> np.ndarray:
    """Build the eight fraud-model features for a transaction event."""
    baseline = USER_BASELINES[tx_event.user_id]
    amount_stddev = baseline.stddev
    amount_zscore = (
        (tx_event.amount - baseline.mean) / amount_stddev
        if amount_stddev > MIN_TRANSACTION_AMOUNT
        else MIN_TRANSACTION_AMOUNT
    )
    event_hour = _utc_timestamp(tx_event.timestamp).hour
    hour_angle = math.tau * event_hour / HOURS_PER_DAY
    prior_transactions = list(user_history)
    last_transaction = prior_transactions[-1] if prior_transactions else None
    days_since_last_tx = (
        (_utc_timestamp(tx_event.timestamp) - _utc_timestamp(last_transaction.timestamp)).days
        if last_transaction is not None
        else MIN_TRANSACTION_AMOUNT
    )
    known_devices = {event.device_id for event in prior_transactions}
    known_beneficiaries = {event.destination for event in prior_transactions}
    user = USERS[tx_event.user_id]
    features = np.array(
        [
            amount_zscore,
            math.sin(hour_angle),
            math.cos(hour_angle),
            days_since_last_tx,
            _failed_logins_last_hour(tx_event),
            float(tx_event.device_id not in known_devices),
            _haversine_distance_km(user.home_geo, _ip_geo(tx_event, user.home_geo)),
            float(tx_event.destination not in known_beneficiaries),
        ],
        dtype=float,
    )
    if features.size != FRAUD_FEATURE_COUNT:
        raise ValueError("Fraud feature extraction did not produce eight features")
    return features


class FraudDetector:
    """Train and apply an Isolation Forest model to transaction behaviour."""

    def __init__(self) -> None:
        """Create an untrained detector with the configured model parameters."""
        self.model = IsolationForest(
            n_estimators=ISOLATION_FOREST_ESTIMATORS,
            contamination=ANOMALY_CONTAMINATION,
            random_state=RANDOM_SEED,
        )
        self.is_fitted = False

    def fit(self) -> None:
        """Pre-train the detector on one thousand synthetic normal transactions."""
        samples: list[np.ndarray] = []
        user_ids = list(USERS)
        for sample_index in range(FRAUD_TRAINING_SAMPLES):
            user_id = user_ids[sample_index % len(user_ids)]
            user = USERS[user_id]
            baseline = USER_BASELINES[user_id]
            amount = max(
                MIN_TRANSACTION_AMOUNT,
                random.gauss(*user.typical_tx_amount),
            )
            baseline.add(amount)
            timestamp = datetime.now(timezone.utc)
            training_event = TransactionEvent(
                event_id=f"training-{sample_index}",
                timestamp=timestamp,
                tx_type="transfer",
                user_id=user_id,
                ip_address="0.0.0.0",
                device_id=f"training-device-{user_id}",
                amount=amount,
                destination=f"training-destination-{user_id}",
                metadata={},
            )
            samples.append(extract_features(training_event, []))

        self.model.fit(np.vstack(samples))
        self.is_fitted = True

    def score(self, tx_event: TransactionEvent) -> dict[str, object]:
        """Return the Isolation Forest score and feature values for one transaction."""
        if not self.is_fitted:
            self.fit()

        features = extract_features(tx_event, USER_TRANSACTION_HISTORY[tx_event.user_id])
        anomaly_score = float(self.model.decision_function(features.reshape(1, -1))[0])
        feature_names = (
            "tx_amount_zscore",
            "hour_sin",
            "hour_cos",
            "days_since_last_tx",
            "failed_logins_1hr",
            "new_device_flag",
            "geo_distance_km",
            "new_beneficiary_flag",
        )
        feature_contributions = dict(zip(feature_names, features.tolist(), strict=True))
        return {
            "anomaly_score": anomaly_score,
            "is_anomaly": anomaly_score < FRAUD_ANOMALY_THRESHOLD,
            "feature_contributions": feature_contributions,
        }


FRAUD_DETECTOR = FraudDetector()


def score_transaction(tx_event: TransactionEvent) -> dict[str, object]:
    """Score a transaction once, then record it in the rolling user history."""
    cached_score = TRANSACTION_SCORES.get(tx_event.event_id)
    if cached_score is not None:
        return cached_score

    score = FRAUD_DETECTOR.score(tx_event)
    USER_BASELINES[tx_event.user_id].add(tx_event.amount)
    USER_TRANSACTION_HISTORY[tx_event.user_id].append(tx_event)
    TRANSACTION_SCORES[tx_event.event_id] = score
    FRAUD_SCORE_HISTORY.append((_utc_timestamp(tx_event.timestamp), float(score["anomaly_score"])))
    return score


def alert_anomaly_score(tx_events: list[TransactionEvent]) -> float:
    """Return the average fraud score for all transactions included in an alert."""
    scores = [float(score_transaction(event)["anomaly_score"]) for event in tx_events]
    return float(np.mean(scores)) if scores else MIN_TRANSACTION_AMOUNT


def fraud_heatmap() -> list[dict[str, object]]:
    """Bucket fraud scores from the last two hours into five-minute averages."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=HEATMAP_WINDOW_HOURS)
    bucket_scores: dict[datetime, list[float]] = defaultdict(list)
    for timestamp, score in FRAUD_SCORE_HISTORY:
        if _utc_timestamp(timestamp) < window_start:
            continue
        bucket_minute = timestamp.minute - (timestamp.minute % HEATMAP_BUCKET_MINUTES)
        bucket = timestamp.replace(minute=bucket_minute, second=0, microsecond=0)
        bucket_scores[bucket].append(score)

    current_bucket = now.replace(
        minute=now.minute - (now.minute % HEATMAP_BUCKET_MINUTES),
        second=0,
        microsecond=0,
    )
    buckets = [
        current_bucket - timedelta(minutes=HEATMAP_BUCKET_MINUTES * offset)
        for offset in range(HEATMAP_BUCKET_COUNT - 1, -1, -1)
    ]
    return [
        {
            "timestamp": bucket.isoformat(),
            "average_anomaly_score": float(np.mean(bucket_scores[bucket]))
            if bucket_scores[bucket]
            else MIN_TRANSACTION_AMOUNT,
        }
        for bucket in buckets
    ]
