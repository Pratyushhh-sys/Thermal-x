"""
backend/api/stream.py
======================
GET  /api/events/stream          — SSE endpoint for real-time thermal event streaming.
POST /api/events/stream/simulate — Test & validation: process an observation through
                                  the existing pipeline and broadcast via SSE.
GET  /api/events/stream/status   — SSE manager connection status and heartbeat info.
POST /api/events/stream/broadcast — Administrative broadcast helper.

ADDITIVE ONLY. Does not alter any existing endpoint or model logic.

Authentication:
  SSE connections are authenticated via the HttpOnly 'access_token' cookie.
  The browser sends it automatically when EventSource is opened with withCredentials=true.
  Unauthenticated connections receive HTTP 401 before the stream starts.
  Both ADMIN and VIEWER roles may receive live updates.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from backend.services.sse_service import (
    sse_manager,
    publish_thermal_event,
    publish_high_risk_alert,
    publish_dashboard_update,
    publish_notification,
    publish_system_status,
    process_and_broadcast_observation,
    _iso_now,
)
from backend.api.dependencies import get_current_user, require_role

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /api/events/stream  — SSE endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/events/stream",
    tags=["SSE"],
    summary="Real-time Server-Sent Events stream for thermal observations",
    description=(
        "Establishes a persistent SSE connection. Emits: thermal_event, "
        "high_risk_alert, dashboard_update, notification, system_status, heartbeat. "
        "Requires authentication via HttpOnly cookie (withCredentials=true on EventSource)."
    ),
)
async def sse_stream(request: Request, current_user: dict = Depends(require_role("ADMIN", "VIEWER"))):
    """
    SSE endpoint. Returns text/event-stream with required non-buffering headers.
    Supports Last-Event-ID for transparent reconnection replay.
    Authentication: HttpOnly cookie validated before streaming begins.
    """
    last_event_id = request.headers.get("last-event-id") or request.query_params.get("last_event_id")
    client = sse_manager.connect(last_event_id=last_event_id)

    logger.debug("SSE: new authenticated client %s (role=%s)", current_user.get("email"), current_user.get("role"))

    return StreamingResponse(
        sse_manager.stream(client),
        media_type="text/event-stream",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# GET /api/events/stream/status  — connection status (public, no auth required)
# ---------------------------------------------------------------------------

@router.get(
    "/events/stream/status",
    tags=["SSE"],
    summary="SSE connection status and diagnostics",
)
async def sse_status():
    """Returns the number of currently active SSE clients and status."""
    return {
        "active_clients": sse_manager.client_count,
        "server_time": _iso_now(),
        "heartbeat_interval_seconds": 20,
        "service": "Thermal Source Attribution SSE",
        "status": "online",
    }


# ---------------------------------------------------------------------------
# POST /api/events/stream/simulate — test & validation injection endpoint (ADMIN only)
# ---------------------------------------------------------------------------

@router.post(
    "/events/stream/simulate",
    tags=["SSE"],
    summary="[Test/Validation] Process observation through pipeline and broadcast via SSE",
    description=(
        "Simulates receiving a thermal observation. Passes it through the existing "
        "preprocessing, Experiment C ML classification, and risk assessment pipeline, "
        "registers it, and broadcasts thermal_event, high_risk_alert, and dashboard_update. "
        "Requires ADMIN role."
    ),
)
async def simulate_event(
    request: Request,
    body: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(require_role("ADMIN")),
):
    """
    Process observation through the real pipeline and broadcast over SSE.
    """
    if body is None:
        body = {}

    # Defaults provide a realistic Indian industrial thermal observation
    observation = {
        "id": body.get("id") or f"SIM-{uuid.uuid4().hex[:6].upper()}",
        "latitude": body.get("latitude", 21.115),
        "longitude": body.get("longitude", 72.652),
        "frp": float(body.get("frp", 65.0)),
        "brightness": float(body.get("brightness", 345.2)),
        "brightness_ti5": float(body.get("brightness_ti5", 298.5)),
        "scan": float(body.get("scan", 0.4)),
        "track": float(body.get("track", 0.38)),
        "acq_date": body.get("acq_date") or _iso_now()[:10],
        "acq_time": body.get("acq_time", "0830"),
        "satellite": body.get("satellite", "VIIRS-SNPP"),
        "day_night": body.get("day_night", "D"),
        "active_days_last_7": int(body.get("active_days_last_7", 5)),
    }

    # If user explicitly overrode source or risk_level, include them
    if "source" in body:
        observation["source"] = body["source"]
    if "risk_level" in body:
        observation["risk_level"] = body["risk_level"]

    # Run through the pipeline and broadcast!
    processed_payload = process_and_broadcast_observation(
        observation=observation,
        app_state=request.app.state,
        is_simulated=True,
    )

    return {
        "status": "processed_and_broadcast",
        "event": processed_payload,
        "active_clients": sse_manager.client_count,
        "warning": "Simulated event processed through ML pipeline. Labeled simulated=true.",
    }


# ---------------------------------------------------------------------------
# POST /api/events/stream/broadcast — administrative broadcast (ADMIN only)
# ---------------------------------------------------------------------------

@router.post(
    "/events/stream/broadcast",
    tags=["SSE"],
    summary="Broadcast a custom SSE event",
)
async def broadcast_event(
    request: Request,
    payload: Dict[str, Any],
    current_user: dict = Depends(require_role("ADMIN")),
):
    """
    Broadcast a custom event name and data to all connected clients.
    Requires ADMIN role.
    """
    event_name = payload.get("event", "thermal_event")
    data = payload.get("data", {})
    event_id = payload.get("id") or str(uuid.uuid4())

    sse_manager.broadcast(event_name, data, event_id=event_id)
    return {
        "status": "broadcast_sent",
        "event": event_name,
        "event_id": event_id,
        "active_clients": sse_manager.client_count,
    }
