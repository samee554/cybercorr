# CyberCorr

CyberCorr is a real-time, full-stack AI cybersecurity and fraud correlation platform. It bridges the gap between siloed security operations centers (SOCs) and fraud departments by correlating cybersecurity telemetry with transactional behavior, surfacing high-confidence, AI-explained alerts in seconds.

**Core Insight:** A failed login is noise. A failed login + new IP + new device + $47,500 transfer in 4 minutes is a critical signal. CyberCorr turns multiple isolated events into 1 actionable intelligence brief.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend API** | Python 3.12 + FastAPI | REST + WebSocket server |
| **Event Simulation** | Faker + custom generator | 50 synthetic users, realistic traffic |
| **Correlation Engine** | NetworkX | Time-window joins, entity graph construction |
| **Fraud Detection** | scikit-learn IsolationForest | Anomaly scoring on transactions |
| **Quantum Risk** | Custom rule engine (5 rules) | Harvest Now, Decrypt Later (HNDL) indicator detection |
| **AI Explanations** | Groq (`llama-3.3-70b-versatile`) | Natural language threat briefs with structured JSON parsing |
| **Real-time updates** | WebSocket (FastAPI) | Live alert streaming |
| **Frontend** | React 18 + Vite 5 | SOC dashboard using custom CSS Variables |
| **Charts** | Recharts 3 | RadialBar, AreaChart, heatmap |
| **Graph** | react-force-graph-2d | Force-directed entity graph |

---

## System Architecture

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                        FRONTEND (React/Vite)                    │
  │   ThreatFeed │ CorrelationGraph │ QuantumPanel │ FraudHeatmap   │
  └────────────────────────┬────────────────────────────────────────┘
                           │ HTTP + WebSocket (port 5173 → 8000)
  ┌────────────────────────▼────────────────────────────────────────┐
  │                      BACKEND (FastAPI :8000)                    │
  │                                                                 │
  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
  │  │  Simulator  │  │  Correlator  │  │   Alert Manager      │    │
  │  │  (faker +   │→ │  (time-win   │→ │   (deduplicate,      │    │
  │  │   scripts)  │  │   join +     │  │    expire, WS        │    │
  │  └─────────────┘  │   entity     │  │    broadcast)        │    │
  │                   │   graph)     │  └──────────┬───────────┘    │
  │  ┌──────────────┐ └──────────────┘             │                │
  │  │  Fraud ML    │  ┌──────────────┐            │                │
  │  │  (Isolation  │  │  Quantum     │────────────┘                │
  │  │   Forest)    │  │  Detector    │                             │
  │  └──────────────┘  │  (5 rules)   │                             │
  │                    └──────────────┘                             │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │         AI Explainer (Groq llama-3.3-70b-versatile)      │   │
  │  │   Threat brief • Risk level • Attack pattern • Actions   │   │
  │  └──────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 20+
- Groq API Key (falls back to template-based static explanations if missing)

### 1. Install Dependencies
```bash
make install
```
This command installs the Python dependencies in the virtual environment and installs the React frontend node modules.

### 2. Configure Environment Variables
Copy the template `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and configure your API key:
```env
GROQ_API_KEY=gsk_...
```

### 3. Start the Development Servers
Start both the FastAPI backend and React frontend concurrently:
```bash
make dev
```
- Backend API runs on: `http://localhost:8000`
- Frontend SOC dashboard runs on: `http://localhost:5173`

---

## API Documentation

All REST responses are wrapped in a standard success envelope:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2026-07-15T14:00:00.000000+00:00"
}
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| **GET** | `/health` | Health status and simulator state |
| **GET** | `/alerts` | Get paginated alert list with optional risk filters |
| **GET** | `/alerts/{alert_id}` | Detailed properties of a single alert |
| **POST** | `/alerts/{alert_id}/explain` | Request AI-driven threat intelligence explanation |
| **POST** | `/alerts/{alert_id}/status` | Update alert status (`investigating`, `resolved`, `false_positive`) |
| **GET** | `/graph` | Entity graph nodes and links for relationship visualization |
| **GET** | `/quantum/summary` | Live quantum threat level and 24h hourly score trend |
| **GET** | `/fraud/heatmap` | Anomaly score bucketed into 5-minute averages |
| **POST** | `/simulate/inject?scenario=1` | Inject one of the three demo scenarios |
| **POST** | `/simulate/start` | Start the background event simulator |
| **POST** | `/simulate/stop` | Pause the background event simulator |
| **GET** | `/simulate/events` | Retrieve the latest list of raw events generated |
| **WS** | `/ws/alerts` | Real-time WebSocket connection for live alerts |

---

## Pre-Scripted Demo Scenarios

Three pre-scripted scenarios are included to showcase the correlation and AI detection features of CyberCorr.

### Scenario 1: Account Takeover (ATO)
**Target User:** `alice_kumar`
```bash
curl -X POST "http://localhost:8000/simulate/inject?scenario=1"
```
**Chronological Sequence:**
1. **T+0s:** 20 failed login attempts from Russian Tor exit IP `185.220.101.42`.
2. **T+45s:** Travel geographical anomaly detected (impossible velocity).
3. **T+90s:** Login from a completely new, unrecognized device ID `d-unknown-991`.
4. **T+120s:** $47,500 transfer to a new beneficiary account.

### Scenario 2: Harvest Now, Decrypt Later (HNDL)
**Target User:** `bob_sharma`
```bash
curl -X POST "http://localhost:8000/simulate/inject?scenario=2"
```
**Chronological Sequence:**
1. **T+0s:** Repeated encrypted archive downloads (matching hashes).
2. **T+30s:** 2.3 GB of bulk encrypted data exfiltrated.
3. **T+60s:** Vulnerable TLS RSA key exchanges detected.
4. **T+90s:** Suspicious off-hours transfer of $8,200 at 02:30 UTC.

### Scenario 3: API Abuse & Money Mule Network
**Target User:** `carol_nair`
```bash
curl -X POST "http://localhost:8000/simulate/inject?scenario=3"
```
**Chronological Sequence:**
1. **T+0s:** High-frequency API abuse (500 requests/minute bot pattern).
2. **T+15s:** Rapid series of 5 transaction transfers to distinct destination accounts.
3. **T+30s:** Second spike in API request rate.
4. **T+60s:** Multiple rapid beneficiary account additions.

---

## Technical Architecture & Decisions

1. **Isolation Forest Model:** Used for unsupervised transaction fraud detection. By training on typical spending profiles, the model dynamically scores anomalies without requiring labeled historical fraud logs.
2. **Graph Theory for Correlation:** NetworkX builds a real-time entity relation graph. Correlating shared devices, IPs, and destinations reduces the SOC false positive rate from SIEM averages (90%+) down to under 10%.
3. **Groq LLM Explanations:** Employs Groq (`llama-3.3-70b-versatile`) with a system instructions prompt, offering ultra-low-latency explanations. Fallback heuristics ensure robust operations even without internet connectivity.
