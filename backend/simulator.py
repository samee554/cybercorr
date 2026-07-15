"""Synthetic cybersecurity and transaction event generation for CyberCorr."""

import asyncio
import logging
import random
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, TypeAlias
from uuid import NAMESPACE_URL, uuid5

from faker import Faker

from backend.config import (
    ACCOUNT_ID_MAX,
    ACCOUNT_ID_MIN,
    ATTACK_SEVERITY_MAX,
    ATTACK_SEVERITY_MIN,
    CURRENCY_DECIMAL_PLACES,
    CYBER_EVENT_PROBABILITY,
    DEVICE_ID_DIGITS,
    DEVICE_ID_MODULUS,
    EVENT_STORE_MAXLEN,
    HOME_GEOS,
    IP_HOST_MAX,
    IP_HOST_MIN,
    IP_NETWORK_PREFIX,
    IP_OCTET_MAX,
    IP_OCTET_MIN,
    MIN_TRANSACTION_AMOUNT,
    MONETARY_TRANSACTION_TYPES,
    NORMAL_CYBER_EVENT_TYPES,
    NORMAL_CYBER_EVENT_WEIGHTS,
    NORMAL_SEVERITY_MAX,
    NORMAL_SEVERITY_MIN,
    RANDOM_SEED,
    RANDOM_CHOICE_COUNT,
    SIMULATION_INTERVAL_MAX,
    SIMULATION_INTERVAL_MIN,
    SIMULATION_USERS,
    SUBNET_PREFIX_LENGTH,
    TRANSACTION_TYPES,
    TRANSACTION_TYPE_WEIGHTS,
    USUAL_HOUR_RANGES,
    USER_AMOUNT_MEAN_MAX,
    USER_AMOUNT_MEAN_MIN,
    USER_AMOUNT_STDDEV_RATIO,
)
from backend.models import CyberEvent, TransactionEvent

logger = logging.getLogger(__name__)

Event: TypeAlias = CyberEvent | TransactionEvent


@dataclass(frozen=True)
class SyntheticUser:
    """A stable profile used to generate believable events for one user."""

    user_id: str
    name: str
    usual_ip_range: str
    usual_hour_range: tuple[int, int]
    typical_tx_amount: tuple[float, float]
    home_geo: tuple[float, float]


random.seed(RANDOM_SEED)
_faker = Faker()
_faker.seed_instance(RANDOM_SEED)
_event_sequence = 0
EVENT_STORE: deque[Event] = deque(maxlen=EVENT_STORE_MAXLEN)

# ---------------------------------------------------------------------------
# Demo scenario users — fixed profiles guaranteed to exist in USERS
# ---------------------------------------------------------------------------
DEMO_USERS: dict[str, tuple[str, str]] = {
    "alice_kumar": ("Alice Kumar", "10.42.11.0/24"),
    "bob_sharma":  ("Bob Sharma",  "10.55.22.0/24"),
    "carol_nair":  ("Carol Nair",  "10.77.33.0/24"),
}


def create_synthetic_users() -> dict[str, SyntheticUser]:
    """Create reproducible user profiles with stable locations and spending baselines.

    The three demo scenario users (alice_kumar, bob_sharma, carol_nair) are
    inserted first with deterministic profiles so attack scenarios can rely on
    their existence regardless of random seed state.
    """
    users: dict[str, SyntheticUser] = {}

    # Seed deterministic demo users first.
    for uid, (name, ip_range) in DEMO_USERS.items():
        users[uid] = SyntheticUser(
            user_id=uid,
            name=name,
            usual_ip_range=ip_range,
            usual_hour_range=(9, 17),
            typical_tx_amount=(2000.0, 400.0),
            home_geo=HOME_GEOS[0],
        )

    while len(users) < SIMULATION_USERS:
        name = _faker.name()
        user_id = name.lower().replace("'", "").replace(".", "").replace(" ", "_")
        if user_id in users:
            continue

        amount_mean = random.uniform(USER_AMOUNT_MEAN_MIN, USER_AMOUNT_MEAN_MAX)
        amount_stddev = amount_mean * USER_AMOUNT_STDDEV_RATIO
        second_octet = random.randint(IP_OCTET_MIN, IP_OCTET_MAX)
        third_octet = random.randint(IP_OCTET_MIN, IP_OCTET_MAX)
        usual_ip_range = (
            f"{IP_NETWORK_PREFIX}.{second_octet}.{third_octet}.0/{SUBNET_PREFIX_LENGTH}"
        )
        users[user_id] = SyntheticUser(
            user_id=user_id,
            name=name,
            usual_ip_range=usual_ip_range,
            usual_hour_range=random.choice(USUAL_HOUR_RANGES),
            typical_tx_amount=(amount_mean, amount_stddev),
            home_geo=random.choice(HOME_GEOS),
        )

    return users


USERS = create_synthetic_users()


def _next_event_id() -> str:
    """Create a deterministic UUID for the next simulated event."""
    global _event_sequence
    _event_sequence += 1
    return str(uuid5(NAMESPACE_URL, f"cybercorr-event-{_event_sequence}"))


def _user_or_raise(user_id: str) -> SyntheticUser:
    """Return a user profile or raise a clear error for an unknown user."""
    try:
        return USERS[user_id]
    except KeyError as exc:
        raise ValueError(f"Unknown simulated user: {user_id}") from exc


def _ip_address(user: SyntheticUser) -> str:
    """Generate an address inside a user's regular /24 subnet."""
    subnet = user.usual_ip_range.split("/")[0].rsplit(".", maxsplit=1)[0]
    host = random.randint(IP_HOST_MIN, IP_HOST_MAX)
    return f"{subnet}.{host}"


def _device_id(user: SyntheticUser) -> str:
    """Create a stable-looking device identifier for a generated event."""
    suffix = uuid5(NAMESPACE_URL, user.user_id).int % DEVICE_ID_MODULUS
    return f"d-{suffix:0{DEVICE_ID_DIGITS}d}"


def _event_metadata(user: SyntheticUser, source: str) -> dict[str, object]:
    """Build shared metadata for an event without including real PII."""
    return {
        "source": source,
        "home_geo": {"lat": user.home_geo[0], "lon": user.home_geo[1]},
        "usual_hour_range": user.usual_hour_range,
    }


def generate_cyber_event(user_id: str) -> CyberEvent:
    """Generate a weighted normal cybersecurity event for one user."""
    user = _user_or_raise(user_id)
    event_type = random.choices(
        NORMAL_CYBER_EVENT_TYPES,
        weights=NORMAL_CYBER_EVENT_WEIGHTS,
        k=RANDOM_CHOICE_COUNT,
    )[0]
    return CyberEvent(
        event_id=_next_event_id(),
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        user_id=user.user_id,
        ip_address=_ip_address(user),
        device_id=_device_id(user),
        severity=random.randint(NORMAL_SEVERITY_MIN, NORMAL_SEVERITY_MAX),
        metadata=_event_metadata(user, "simulator"),
    )


def generate_transaction_event(user_id: str) -> TransactionEvent:
    """Generate a transaction using the user's normal spending baseline."""
    user = _user_or_raise(user_id)
    tx_type = random.choices(
        TRANSACTION_TYPES,
        weights=TRANSACTION_TYPE_WEIGHTS,
        k=RANDOM_CHOICE_COUNT,
    )[0]
    amount = MIN_TRANSACTION_AMOUNT
    if tx_type in MONETARY_TRANSACTION_TYPES:
        amount = max(MIN_TRANSACTION_AMOUNT, random.gauss(*user.typical_tx_amount))

    destination_suffix = random.randint(ACCOUNT_ID_MIN, ACCOUNT_ID_MAX)
    return TransactionEvent(
        event_id=_next_event_id(),
        timestamp=datetime.now(timezone.utc),
        tx_type=tx_type,
        user_id=user.user_id,
        ip_address=_ip_address(user),
        device_id=_device_id(user),
        amount=round(amount, CURRENCY_DECIMAL_PLACES),
        destination=f"ACC-{destination_suffix}",
        metadata=_event_metadata(user, "simulator"),
    )


def generate_attack_event(user_id: str, event_type: str) -> CyberEvent:
    """Generate a specific high-severity cyber event for an attack scenario."""
    user = _user_or_raise(user_id)
    metadata = _event_metadata(user, "attack_scenario")
    metadata["attack_event"] = True
    return CyberEvent(
        event_id=_next_event_id(),
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        user_id=user.user_id,
        ip_address=_ip_address(user),
        device_id=_device_id(user),
        severity=random.randint(ATTACK_SEVERITY_MIN, ATTACK_SEVERITY_MAX),
        metadata=metadata,
    )


def get_recent_events(limit: int) -> list[Event]:
    """Return up to the requested number of most recent generated events."""
    return list(EVENT_STORE)[-limit:]


class SimulatorLoop:
    """Manage the asynchronous background generation of synthetic events."""

    def __init__(self) -> None:
        """Initialize a stopped simulator loop."""
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._event_handler: Callable[[Event], object] | None = None

    @property
    def is_running(self) -> bool:
        """Report whether the generator loop is active."""
        return self._running

    def set_event_handler(self, event_handler: Callable[[Event], object]) -> None:
        """Register the function called after each generated event is stored."""
        self._event_handler = event_handler

    async def start(self) -> bool:
        """Start the event generator unless it is already running."""
        if self._running:
            return False

        self._running = True
        self._task = asyncio.create_task(self.run(), name="cybercorr-simulator")
        return True

    async def stop(self) -> bool:
        """Stop the event generator and wait for its background task to end."""
        if not self._running:
            return False

        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        return True

    async def run(self) -> None:
        """Generate and store one randomly selected event every configured interval."""
        while self._running:
            try:
                user_id = random.choice(tuple(USERS))
                event = (
                    generate_cyber_event(user_id)
                    if random.random() < CYBER_EVENT_PROBABILITY
                    else generate_transaction_event(user_id)
                )
                EVENT_STORE.append(event)
                if self._event_handler is not None:
                    self._event_handler(event)
                interval = random.uniform(SIMULATION_INTERVAL_MIN, SIMULATION_INTERVAL_MAX)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(f"Simulator failed to generate an event: {exc}")


SIMULATOR = SimulatorLoop()
