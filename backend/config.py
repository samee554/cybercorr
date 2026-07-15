"""Application-wide configuration constants for CyberCorr."""

# ---------------------------------------------------------------------------
# Correlation engine
# ---------------------------------------------------------------------------
CORRELATION_WINDOW_SECONDS = 300
ALERT_DEDUP_WINDOW_MINUTES = 10
CORRELATION_SCORE_WEIGHTS = (0.3, 0.3, 0.2, 0.2)
CYBER_EVENTS_FOR_MAX_SCORE = 5
TX_BASELINE_STDDEV_MULTIPLIER = 3.0
CORRELATION_SCORE_MAX = 1.0
CORRELATION_RISK_THRESHOLDS = ((0.7, "CRITICAL"), (0.5, "HIGH"), (0.3, "MEDIUM"))
DEFAULT_ANOMALY_SCORE = 0.0
DEFAULT_QUANTUM_RISK_SCORE = 0
OPEN_ALERT_STATUSES = ("new", "investigating")
DEFAULT_ALERT_PAGE = 1
DEFAULT_ALERT_LIMIT = 20

# ---------------------------------------------------------------------------
# Alert lifecycle
# ---------------------------------------------------------------------------
ALERT_EXPIRY_MINUTES = 60
AUTO_EXPIRE_LOOP_INTERVAL_SECONDS = 60

# ---------------------------------------------------------------------------
# AI / Explainer
# ---------------------------------------------------------------------------
MAX_CONCURRENT_AI_CALLS = 10
# Model served through Groq
AI_MODEL = "llama-3.3-70b-versatile"
AI_MAX_TOKENS = 800
# Aliases matching memory.md spec names (kept for cross-reference)
CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS = 800

# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------
SIMULATION_USERS = 50
EVENT_STORE_MAXLEN = 10000
SIMULATION_INTERVAL_MIN = 2.0   # seconds between events
SIMULATION_INTERVAL_MAX = 5.0
RECENT_EVENTS_LIMIT = 100
RANDOM_SEED = 42
CYBER_EVENT_PROBABILITY = 0.6

# IP generation constants
IP_NETWORK_PREFIX = 10
IP_OCTET_MIN = 1
IP_OCTET_MAX = 254
IP_HOST_MIN = 2
IP_HOST_MAX = 254
SUBNET_PREFIX_LENGTH = 24

# Transaction constants
USER_AMOUNT_MEAN_MIN = 250.0
USER_AMOUNT_MEAN_MAX = 5000.0
USER_AMOUNT_STDDEV_RATIO = 0.20
MIN_TRANSACTION_AMOUNT = 0.0
CURRENCY_DECIMAL_PLACES = 2
MONETARY_TRANSACTION_TYPES = ("transfer", "rapid_transfer")

# Device / account ID constants
DEVICE_ID_DIGITS = 6
DEVICE_ID_MODULUS = 1000000
ACCOUNT_ID_DIGITS = 8
ACCOUNT_ID_MIN = 10000000
ACCOUNT_ID_MAX = 99999999
RANDOM_CHOICE_COUNT = 1

# Severity bands
NORMAL_SEVERITY_MIN = 1
NORMAL_SEVERITY_MAX = 6
ATTACK_SEVERITY_MIN = 7
ATTACK_SEVERITY_MAX = 10

# Event-type distributions
USUAL_HOUR_RANGES = ((8, 16), (9, 17), (10, 18))
HOME_GEOS = (
    (19.0760, 72.8777),
    (28.6139, 77.2090),
    (12.9716, 77.5946),
    (17.3850, 78.4867),
    (13.0827, 80.2707),
)
NORMAL_CYBER_EVENT_TYPES = (
    "failed_login",
    "port_scan",
    "api_abuse",
    "geo_anomaly",
    "tls_downgrade",
    "large_key_exchange",
    "tls_rsa_key_exchange",
    "archive_download_off_hours",
    "repeated_blob_transfer",
    "bulk_encrypted_exfil",
)
NORMAL_CYBER_EVENT_WEIGHTS = (55, 12, 15, 7, 2, 3, 2, 1, 1, 1)
TRANSACTION_TYPES = (
    "transfer",
    "login",
    "balance_inquiry",
    "beneficiary_add",
    "rapid_transfer",
)
TRANSACTION_TYPE_WEIGHTS = (45, 20, 20, 10, 5)

# ---------------------------------------------------------------------------
# Fraud ML
# ---------------------------------------------------------------------------
ANOMALY_CONTAMINATION = 0.05
FRAUD_FEATURE_COUNT = 8
FRAUD_TRAINING_SAMPLES = 1000
USER_BASELINE_HISTORY_SIZE = 100
ISOLATION_FOREST_ESTIMATORS = 100
FRAUD_NORMAL_THRESHOLD = 0.1
FRAUD_ANOMALY_THRESHOLD = -0.1
EARTH_RADIUS_KM = 6371.0
HOURS_PER_DAY = 24
HEATMAP_WINDOW_HOURS = 2
HEATMAP_BUCKET_MINUTES = 5
HEATMAP_BUCKET_COUNT = 24

# ---------------------------------------------------------------------------
# Quantum detector
# ---------------------------------------------------------------------------
QUANTUM_CRITICAL_THRESHOLD = 70
QUANTUM_HIGH_THRESHOLD = 40
QUANTUM_MEDIUM_THRESHOLD = 15
MAX_GRAPH_NODES = 100
QUANTUM_SCORE_MAX = 100
QUANTUM_TREND_HOURS = 24
MINUTES_PER_HOUR = 60
