"""Attack scenario injection functions for CyberCorr demo and testing.

Each scenario injects a timed sequence of cyber and transaction events directly
into the shared EVENT_STORE and immediately triggers the correlator so that
correlated alerts appear on the dashboard within seconds.

Usage (via HTTP endpoint):
    POST /simulate/inject?scenario=1   # Account Takeover
    POST /simulate/inject?scenario=2   # HNDL + Insider Threat
    POST /simulate/inject?scenario=3   # API Fraud / Money Mule Network

These functions are also called at startup for demo pre-caching.
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from backend.correlator import process_event
from backend.models import CyberEvent, TransactionEvent
from backend.simulator import EVENT_STORE, USERS, _device_id, _ip_address

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FOREIGN_IP = "185.220.101.42"      # Tor exit / foreign IP used for scenarios 1
_NEW_DEVICE_ALICE = "d-unknown-991"
_ENCRYPTED_ARCHIVE_HASH = "sha256:4a8f2c1d9e3b7f6a"  # Same hash repeated for HNDL staging


def _cyber(
    user_id: str,
    event_type: str,
    ip_address: str | None = None,
    device_id: str | None = None,
    severity: int = 9,
    metadata: dict | None = None,
) -> CyberEvent:
    """Build a CyberEvent for a scenario step."""
    user = USERS[user_id]
    return CyberEvent(
        event_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        user_id=user_id,
        ip_address=ip_address or _ip_address(user),
        device_id=device_id or _device_id(user),
        severity=severity,
        metadata={**(metadata or {}), "source": "attack_scenario"},
    )


def _tx(
    user_id: str,
    tx_type: str,
    amount: float,
    destination: str,
    ip_address: str | None = None,
    device_id: str | None = None,
    timestamp: datetime | None = None,
    metadata: dict | None = None,
) -> TransactionEvent:
    """Build a TransactionEvent for a scenario step."""
    user = USERS[user_id]
    return TransactionEvent(
        event_id=str(uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc),
        tx_type=tx_type,
        user_id=user_id,
        ip_address=ip_address or _ip_address(user),
        device_id=device_id or _device_id(user),
        amount=amount,
        destination=destination,
        metadata={**(metadata or {}), "source": "attack_scenario"},
    )


def _inject(event: CyberEvent | TransactionEvent) -> None:
    """Store event and immediately run correlation."""
    EVENT_STORE.append(event)
    process_event(event)


# ---------------------------------------------------------------------------
# Scenario 1 — Credential Stuffing + Account Takeover
# User: alice_kumar
# ---------------------------------------------------------------------------

async def scenario_1() -> None:
    """
    Simulate a credential stuffing attack followed by a large fraudulent transfer.

    Timeline:
      T+0s:   20x failed_login from foreign IP (rapid succession)
      T+45s:  geo_anomaly — same foreign IP signals impossible travel
      T+90s:  new_device_login — attacker pivots to unknown device
      T+120s: $47,500 transfer to new beneficiary
    """
    user_id = "alice_kumar"
    logger.info(f"[Scenario 1] Starting Account Takeover sequence for {user_id}")

    # T+0s — 20 rapid failed logins from a foreign IP
    for i in range(20):
        event = _cyber(
            user_id,
            "failed_login",
            ip_address=_FOREIGN_IP,
            severity=8,
            metadata={"attempt": i + 1, "reason": "invalid_password"},
        )
        _inject(event)
        await asyncio.sleep(0.3)   # rapid succession — 300ms apart

    logger.info("[Scenario 1] T+45s — injecting geo_anomaly")
    await asyncio.sleep(45 - 20 * 0.3)  # remaining wait to hit 45s mark

    # T+45s — geo anomaly (foreign country login attempt)
    _inject(_cyber(
        user_id,
        "geo_anomaly",
        ip_address=_FOREIGN_IP,
        severity=9,
        metadata={"country": "RU", "distance_km": 7800, "impossible_travel": True},
    ))

    logger.info("[Scenario 1] T+90s — injecting new_device_login")
    await asyncio.sleep(45)   # T+45 -> T+90

    # T+90s — login from unknown device
    _inject(_cyber(
        user_id,
        "new_device_login",
        ip_address=_FOREIGN_IP,
        device_id=_NEW_DEVICE_ALICE,
        severity=9,
        metadata={"device_fingerprint": "unknown", "os": "Windows NT 10.0"},
    ))

    logger.info("[Scenario 1] T+120s — injecting $47,500 transfer")
    await asyncio.sleep(30)   # T+90 -> T+120

    # T+120s — large transfer to new beneficiary (never seen before)
    _inject(_tx(
        user_id,
        tx_type="transfer",
        amount=47500.00,
        destination="ACC-88210000",
        ip_address=_FOREIGN_IP,
        device_id=_NEW_DEVICE_ALICE,
        metadata={"new_beneficiary": True, "wire_transfer": True},
    ))

    logger.info("[Scenario 1] Account Takeover sequence complete.")


# ---------------------------------------------------------------------------
# Scenario 2 — HNDL Staging + Insider Threat
# User: bob_sharma
# ---------------------------------------------------------------------------

async def scenario_2() -> None:
    """
    Simulate a Harvest-Now-Decrypt-Later (HNDL) staging operation combined
    with suspicious insider financial activity.

    Timeline:
      T+0s:   3x repeated_blob_transfer (same encrypted archive hash)
      T+30s:  bulk_encrypted_exfil (2.3 GB exfiltration)
      T+60s:  tls_rsa_key_exchange (quantum-vulnerable cipher)
      T+90s:  Off-hours large transfer at 02:30 UTC ($8,200)
    """
    user_id = "bob_sharma"
    logger.info(f"[Scenario 2] Starting HNDL + Insider sequence for {user_id}")

    # T+0s — 3x repeated blob transfers (same encrypted archive = HNDL staging)
    for i in range(3):
        _inject(_cyber(
            user_id,
            "repeated_blob_transfer",
            severity=8,
            metadata={
                "archive_hash": _ENCRYPTED_ARCHIVE_HASH,
                "transfer_index": i + 1,
                "size_mb": 340,
            },
        ))
        await asyncio.sleep(3)   # 3 seconds apart

    logger.info("[Scenario 2] T+30s — injecting bulk_encrypted_exfil")
    await asyncio.sleep(30 - 3 * 3)   # remaining wait to 30s mark

    # T+30s — bulk exfiltration (2.3 GB)
    _inject(_cyber(
        user_id,
        "bulk_encrypted_exfil",
        severity=10,
        metadata={"size_gb": 2.3, "destination_domain": "s3.external-backup.io", "encrypted": True},
    ))

    logger.info("[Scenario 2] T+60s — injecting tls_rsa_key_exchange")
    await asyncio.sleep(30)   # T+30 -> T+60

    # T+60s — quantum-vulnerable TLS key exchange
    _inject(_cyber(
        user_id,
        "tls_rsa_key_exchange",
        severity=7,
        metadata={"cipher": "TLS_RSA_WITH_AES_128_CBC_SHA", "key_bits": 2048},
    ))

    logger.info("[Scenario 2] T+90s — injecting off-hours $8,200 transfer")
    await asyncio.sleep(30)   # T+60 -> T+90

    # T+90s — off-hours large transfer at 02:30 AM UTC
    off_hours_ts = datetime.now(timezone.utc)
    _inject(_tx(
        user_id,
        tx_type="transfer",
        amount=8200.00,
        destination="ACC-55501234",
        timestamp=off_hours_ts,
        metadata={"off_hours": True, "hour_utc": 2, "new_beneficiary": True},
    ))

    logger.info("[Scenario 2] HNDL + Insider sequence complete.")


# ---------------------------------------------------------------------------
# Scenario 3 — API Abuse + Rapid Transfers (Money Mule Network)
# User: carol_nair
# ---------------------------------------------------------------------------

async def scenario_3() -> None:
    """
    Simulate automated API abuse driving a money-mule fraud network.

    Timeline:
      T+0s:   api_rate_exceeded (500 req/min — scripted bot)
      T+15s:  5x rapid_transfer ($200–$800 each, different destinations)
      T+30s:  api_rate_exceeded again (bot continues)
      T+60s:  3x beneficiary_add (new mule recipients registered)
    """
    user_id = "carol_nair"
    logger.info(f"[Scenario 3] Starting API Fraud / Money Mule sequence for {user_id}")

    # T+0s — API rate exceeded (bot traffic, 500 req/min)
    _inject(_cyber(
        user_id,
        "api_abuse",
        severity=8,
        metadata={"req_per_min": 500, "endpoint": "/api/transfer", "user_agent": "python-requests/2.31"},
    ))

    logger.info("[Scenario 3] T+15s — injecting 5x rapid_transfer")
    await asyncio.sleep(15)

    # T+15s — 5 rapid small transfers to different mule accounts
    mule_destinations = [
        "ACC-11112222", "ACC-33334444", "ACC-55556666", "ACC-77778888", "ACC-99990000"
    ]
    amounts = [200.00, 450.00, 300.00, 780.00, 520.00]
    for dest, amount in zip(mule_destinations, amounts):
        _inject(_tx(
            user_id,
            tx_type="rapid_transfer",
            amount=amount,
            destination=dest,
            metadata={"automated": True, "mule_network": True},
        ))
        await asyncio.sleep(1)   # 1 second apart (rapid)

    logger.info("[Scenario 3] T+30s — injecting second api_rate_exceeded")
    await asyncio.sleep(30 - 15 - 5)   # remaining wait to T+30

    # T+30s — second API spike (bot hasn't stopped)
    _inject(_cyber(
        user_id,
        "api_abuse",
        severity=9,
        metadata={"req_per_min": 480, "endpoint": "/api/beneficiary", "escalated": True},
    ))

    logger.info("[Scenario 3] T+60s — injecting 3x beneficiary_add")
    await asyncio.sleep(30)   # T+30 -> T+60

    # T+60s — 3 new mule recipients registered
    mule_beneficiaries = ["ACC-MULE-0001", "ACC-MULE-0002", "ACC-MULE-0003"]
    for beneficiary in mule_beneficiaries:
        _inject(_tx(
            user_id,
            tx_type="beneficiary_add",
            amount=0.0,
            destination=beneficiary,
            metadata={"automated_registration": True},
        ))
        await asyncio.sleep(2)

    logger.info("[Scenario 3] API Fraud / Money Mule sequence complete.")


# ---------------------------------------------------------------------------
# Registry — maps scenario number -> coroutine function
# ---------------------------------------------------------------------------

SCENARIOS: dict[int, object] = {
    1: scenario_1,
    2: scenario_2,
    3: scenario_3,
}
