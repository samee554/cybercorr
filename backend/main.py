"""FastAPI application entry point for CyberCorr."""
# load_dotenv MUST be first — before any backend imports that read env vars
from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.alert_manager import ALERT_STORE
from backend.config import (
    DEFAULT_ALERT_LIMIT,
    DEFAULT_ALERT_PAGE,
    OPEN_ALERT_STATUSES,
    RECENT_EVENTS_LIMIT,
)
from backend.correlator import graph_data, process_event
from backend.explainer import EXPLAINER
from backend.fraud_ml import FRAUD_DETECTOR, fraud_heatmap
from backend.models import StatusUpdateRequest
from backend.quantum_detector import quantum_summary
from backend.simulator import SIMULATOR, get_recent_events
from scripts.attack_scenarios import SCENARIOS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CyberCorr", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """Manages active WebSocket connections, enabling broadcasts."""

    def __init__(self) -> None:
        """Initialize the connection manager with an empty active list."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a WebSocket connection and register it."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New WebSocket connection registered.")

    def disconnect(self, websocket: WebSocket) -> None:
        """Deregister a closed WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket connection deregistered.")

    async def broadcast(self, message: str) -> None:
        """Broadcast a text message to all registered WebSocket connections."""
        disconnected_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                disconnected_connections.append(connection)

        for connection in disconnected_connections:
            self.disconnect(connection)


manager = ConnectionManager()
background_tasks: list[asyncio.Task] = []


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _ok(data: object) -> dict[str, object]:
    """Wrap a successful response in the standard API envelope."""
    return {"success": True, "data": data, "error": None, "timestamp": _now_iso()}


def _err(code: str, message: str) -> dict[str, object]:
    """Wrap an error response in the standard API envelope."""
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "timestamp": _now_iso(),
    }


async def broadcast_alerts_task() -> None:
    """Pull alerts from ALERT_STORE.broadcast_queue and broadcast them to all WS clients."""
    while True:
        try:
            alert = await ALERT_STORE.broadcast_queue.get()
            envelope = _ok(alert.model_dump(mode="json"))
            await manager.broadcast(json.dumps(envelope))
            ALERT_STORE.broadcast_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Error in broadcast_alerts_task: {exc}")
            await asyncio.sleep(1)


async def heartbeat_task() -> None:
    """Send a heartbeat ping every 30 seconds to keep connections alive."""
    while True:
        try:
            await asyncio.sleep(30)
            envelope = _ok({"type": "ping"})
            await manager.broadcast(json.dumps(envelope))
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Error in heartbeat_task: {exc}")


@app.on_event("startup")
async def startup() -> None:
    """Pre-train fraud detection, start simulator, and launch background tasks."""
    # Register the correlator as the event handler INSIDE startup (not at module level)
    SIMULATOR.set_event_handler(process_event)

    # Pre-train Isolation Forest before first request
    FRAUD_DETECTOR.fit()
    logger.info("Isolation Forest model pre-trained.")

    # Start background event generator
    await SIMULATOR.start()

    # Start background tasks
    task_expire = asyncio.create_task(ALERT_STORE.auto_expire_loop(), name="auto-expire")
    task_broadcast = asyncio.create_task(broadcast_alerts_task(), name="broadcast")
    task_heartbeat = asyncio.create_task(heartbeat_task(), name="heartbeat")
    background_tasks.extend([task_expire, task_broadcast, task_heartbeat])

    # Pre-cache demo scenario explanations in background (non-blocking)
    asyncio.create_task(_precache_demo_scenarios(), name="precache")

    logger.info("CyberCorr ready. Simulator running.")


async def _precache_demo_scenarios() -> None:
    """Run all 3 attack scenarios silently to pre-warm the AI explanation cache.

    Runs in the background after startup so the main server is immediately responsive.
    Each scenario is run, a short wait allows the correlator to produce alerts,
    those alerts are explained, and then marked resolved so the dashboard starts clean.
    """
    try:
        logger.info("Pre-caching demo scenario explanations...")

        for scenario_num in (1, 2, 3):
            pre_alert_ids = {a.alert_id for a in ALERT_STORE.values()}

            scenario_fn = SCENARIOS.get(scenario_num)
            if scenario_fn is None:
                continue
            await scenario_fn()  # type: ignore[operator]

            # Allow correlator time to create and score the alert
            await asyncio.sleep(5)

            # Find new alerts created by this scenario
            new_alerts = [
                a for a in ALERT_STORE.values()
                if a.alert_id not in pre_alert_ids
            ]

            for alert in new_alerts:
                if alert.overall_risk in ("MEDIUM", "HIGH", "CRITICAL"):
                    try:
                        explanation = await EXPLAINER.explain(alert)
                        ALERT_STORE.set_explanation(alert.alert_id, explanation)
                        logger.info(
                            f"Pre-cached explanation for scenario {scenario_num} "
                            f"alert {alert.alert_id[:8]}"
                        )
                    except Exception as exc:
                        logger.warning(
                            f"Pre-cache explain failed for {alert.alert_id[:8]}: {exc}"
                        )

                # Resolve so the dashboard starts clean
                ALERT_STORE.update_status(alert.alert_id, "resolved")

            await asyncio.sleep(1)

        logger.info("Demo scenarios pre-cached. Ready.")
    except Exception as exc:
        logger.error(f"Failed to pre-cache demo scenarios: {exc}")


@app.on_event("shutdown")
async def shutdown() -> None:
    """Stop synthetic event generation and cancel background tasks."""
    await SIMULATOR.stop()
    for task in background_tasks:
        task.cancel()
    background_tasks.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check() -> dict[str, object]:
    """Return the backend health status in the standard envelope."""
    return _ok({"status": "ok", "simulator_running": SIMULATOR.is_running})


# ---------------------------------------------------------------------------
# Simulator routes
# ---------------------------------------------------------------------------

@app.get("/simulate/events")
async def list_simulated_events() -> dict[str, object]:
    """Return the latest simulated cybersecurity and transaction events."""
    events = [event.model_dump(mode="json") for event in get_recent_events(RECENT_EVENTS_LIMIT)]
    return _ok(events)


@app.post("/simulate/start")
async def start_simulation() -> dict[str, object]:
    """Start the simulator if it is not already running."""
    started = await SIMULATOR.start()
    return _ok({"running": SIMULATOR.is_running, "started": started})


@app.post("/simulate/stop")
async def stop_simulation() -> dict[str, object]:
    """Stop the simulator if it is currently running."""
    stopped = await SIMULATOR.stop()
    return _ok({"running": SIMULATOR.is_running, "stopped": stopped})


@app.post("/simulate/inject")
async def inject_scenario(
    scenario: int = Query(..., ge=1, le=3),
) -> dict[str, object]:
    """Trigger one of the 3 pre-built attack scenarios by number (1, 2, or 3).

    The scenario runs asynchronously so the HTTP response returns in <200ms.
    Events appear on the dashboard within the scenario's own timing delays.
    """
    scenario_fn = SCENARIOS.get(scenario)
    if scenario_fn is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario: {scenario}. Must be 1, 2, or 3.",
        )

    asyncio.create_task(scenario_fn(), name=f"scenario-{scenario}")  # type: ignore[operator]
    return _ok({"scenario": scenario, "status": "running"})


# ---------------------------------------------------------------------------
# Alert routes
# ---------------------------------------------------------------------------

@app.get("/alerts")
async def list_alerts(
    page: int = Query(DEFAULT_ALERT_PAGE, ge=DEFAULT_ALERT_PAGE),
    limit: int = Query(DEFAULT_ALERT_LIMIT, ge=DEFAULT_ALERT_PAGE),
    risk: str | None = Query(None),
) -> dict[str, object]:
    """Return correlated alerts, paginated and optionally filtered by risk, newest first."""
    result = ALERT_STORE.get_alerts(page, limit, risk)
    # Serialize alert objects to JSON-safe dicts
    serialized = {
        **result,
        "alerts": [a.model_dump(mode="json") for a in result["alerts"]],
    }
    return _ok(serialized)


@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str) -> dict[str, object]:
    """Return one correlated alert by its UUID."""
    alert = ALERT_STORE.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    return _ok(alert.model_dump(mode="json"))


@app.post("/alerts/{alert_id}/status")
async def update_alert_status(
    alert_id: str, request: StatusUpdateRequest
) -> dict[str, object]:
    """Update the status of a specific alert."""
    if request.status not in ("investigating", "resolved", "false_positive"):
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be 'investigating', 'resolved', or 'false_positive'.",
        )

    updated_alert = ALERT_STORE.update_status(alert_id, request.status)
    if updated_alert is None:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")

    return _ok(updated_alert.model_dump(mode="json"))


@app.post("/alerts/{alert_id}/explain")
async def explain_alert(alert_id: str) -> dict[str, object]:
    """Generate or retrieve threat intelligence explanation for an alert."""
    alert = ALERT_STORE.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")

    explanation = await EXPLAINER.explain(alert)
    ALERT_STORE.set_explanation(alert_id, explanation)

    return _ok(explanation.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Graph, quantum, fraud routes
# ---------------------------------------------------------------------------

@app.get("/graph")
async def get_graph() -> dict[str, object]:
    """Return entity-graph nodes and links for the frontend force graph."""
    return _ok(graph_data())


@app.get("/fraud/heatmap")
async def get_fraud_heatmap() -> dict[str, object]:
    """Return average transaction anomaly scores in five-minute buckets."""
    return _ok(fraud_heatmap())


@app.get("/quantum/summary")
async def get_quantum_summary() -> dict[str, object]:
    """Return current HNDL risk, triggered rules, and the hourly trend."""
    return _ok(quantum_summary())


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Register WebSocket connection and stream open alerts and updates."""
    await manager.connect(websocket)
    try:
        # On connection, send all currently open alerts
        open_alerts = [
            alert.model_dump(mode="json")
            for alert in ALERT_STORE.values()
            if alert.status in OPEN_ALERT_STATUSES
        ]
        envelope = _ok({"alerts": open_alerts})
        await websocket.send_json(envelope)

        # Keep connection open — receive loop detects client disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}")
        manager.disconnect(websocket)
