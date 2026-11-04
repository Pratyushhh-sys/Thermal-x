"""
backend/services/sse_service.py
================================
Server-Sent Events connection manager, event broadcaster, and pipeline bridge.

This module is additive and self-contained. No existing service logic is altered.

Responsibilities:
  - Register and manage connected SSE clients.
  - Broadcast named events (thermal_event, high_risk_alert, dashboard_update,
    notification, system_status, heartbeat) to active clients.
  - Heartbeat background task (every 20s).
  - Bounded asyncio.Queue per client with FIFO backpressure.
  - Last-Event-ID reconnection replay buffer (last 100 events).
  - Non-blocking asynchronous streaming with proxy keepalive comments.
  - Integration bridge to consume output of the existing thermal ML and
    risk assessment pipeline without modifying model code.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_CLIENT_QUEUE_SIZE = 64
_HEARTBEAT_INTERVAL = 20
_MAX_EVENT_HISTORY = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_sse(event_name: str, data: Any, event_id: Optional[str] = None) -> str:
    """Format a single SSE message frame (RFC 8895 standard)."""
    if event_id is None:
        event_id = str(uuid.uuid4())
    try:
        payload = json.dumps(data, default=str, ensure_ascii=False)
    except Exception as exc:
        logger.warning("SSE: JSON serialization failed: %s", exc)
        payload = json.dumps({"error": "serialization_failed"})
    return (
        f"id: {event_id}\n"
        f"event: {event_name}\n"
        f"data: {payload}\n\n"
    )


# ---------------------------------------------------------------------------
# SSEClient
# ---------------------------------------------------------------------------

class SSEClient:
    """Represents a connected SSE client with a bounded delivery queue."""

    def __init__(self, last_event_id: Optional[str] = None) -> None:
        self.client_id: str = str(uuid.uuid4())
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=_CLIENT_QUEUE_SIZE)
        self.last_event_id: Optional[str] = last_event_id
        self.connected_at: datetime = datetime.now(timezone.utc)

    def enqueue(self, frame: str) -> None:
        """Enqueue an SSE frame; drop oldest item if queue is full (backpressure)."""
        if self.queue.full():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            self.queue.put_nowait(frame)
        except asyncio.QueueFull:
            pass


# ---------------------------------------------------------------------------
# SSEConnectionManager
# ---------------------------------------------------------------------------

class SSEConnectionManager:
    """
    Manages active SSE client connections, event broadcasting, Last-Event-ID
    replay, and periodic heartbeat task.
    """

    def __init__(self) -> None:
        self._clients: Set[SSEClient] = set()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._recent_events: List[Tuple[str, str]] = []  # [(event_id, formatted_frame), ...]

    # --- Lifecycle --------------------------------------------------------

    def start(self) -> None:
        """Start the heartbeat background task. Called at app startup."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.ensure_future(self._heartbeat_loop())
            logger.info("SSE: connection manager & heartbeat started (interval=%ds)", _HEARTBEAT_INTERVAL)

    def stop(self) -> None:
        """Cancel the heartbeat task. Called at app shutdown."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            logger.info("SSE: heartbeat task stopped.")

    # --- Client management -----------------------------------------------

    def connect(self, last_event_id: Optional[str] = None) -> SSEClient:
        """
        Register a new client. If last_event_id is provided, replay any
        missed events from the recent event buffer.
        """
        client = SSEClient(last_event_id=last_event_id)
        self._clients.add(client)

        # Last-Event-ID replay support
        if last_event_id:
            replay_started = False
            for evt_id, frame in self._recent_events:
                if replay_started:
                    client.enqueue(frame)
                elif evt_id == last_event_id:
                    replay_started = True

        logger.info(
            "SSE: client %s connected (total=%d, last_event_id=%s)",
            client.client_id[:8], len(self._clients), last_event_id
        )
        return client

    def disconnect(self, client: SSEClient) -> None:
        """Remove a client upon disconnection."""
        self._clients.discard(client)
        logger.info(
            "SSE: client %s disconnected (total=%d)",
            client.client_id[:8], len(self._clients)
        )

    @property
    def client_count(self) -> int:
        return len(self._clients)

    # --- Broadcasting ------------------------------------------------------

    def broadcast(
        self,
        event_name: str,
        data: Any,
        event_id: Optional[str] = None,
    ) -> None:
        """
        Synchronously format and enqueue an SSE frame to all active clients.
        Also records frame in recent events ring buffer for Last-Event-ID replay.
        """
        if event_id is None:
            event_id = str(uuid.uuid4())
        frame = _format_sse(event_name, data, event_id)

        # Store in recent event buffer (bounded ring buffer)
        self._recent_events.append((event_id, frame))
        if len(self._recent_events) > _MAX_EVENT_HISTORY:
            self._recent_events.pop(0)

        if not self._clients:
            return

        for client in list(self._clients):
            client.enqueue(frame)

    # --- Async stream generator -------------------------------------------

    async def stream(self, client: SSEClient) -> AsyncGenerator[str, None]:
        """
        Async generator yielding SSE frames for StreamingResponse.
        Emits system_status immediately on connection, then drains queue.
        Sends keepalive comments periodically to keep proxy connections alive.
        """
        # Initial greeting / connection status
        yield _format_sse(
            "system_status",
            {
                "status": "connected",
                "client_id": client.client_id,
                "server_time": _iso_now(),
                "message": "SSE connection established — Thermal Source Attribution stream active.",
            },
            event_id=str(uuid.uuid4()),
        )

        try:
            while True:
                try:
                    frame = await asyncio.wait_for(client.queue.get(), timeout=25.0)
                    yield frame
                except asyncio.TimeoutError:
                    # SSE comment keepalive — prevents proxy/timeout closure
                    yield ": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            self.disconnect(client)

    # --- Heartbeat loop ---------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                if self._clients:
                    self.broadcast(
                        "heartbeat",
                        {
                            "server_time": _iso_now(),
                            "active_clients": len(self._clients),
                            "status": "ok",
                        },
                    )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("SSE: heartbeat error: %s", exc)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

sse_manager = SSEConnectionManager()


# ---------------------------------------------------------------------------
# High-level publish helpers
# ---------------------------------------------------------------------------

def publish_thermal_event(event_data: Dict[str, Any]) -> None:
    """
    Broadcast a thermal_event frame.
    Automatically promotes to high_risk_alert and notification if risk is HIGH or CRITICAL.
    """
    event_id = str(event_data.get("id") or uuid.uuid4())
    sse_manager.broadcast("thermal_event", event_data, event_id=event_id)

    risk = str(event_data.get("risk_level") or event_data.get("risk_tier") or "").upper()
    if risk in {"HIGH", "CRITICAL"}:
        alert_data = {
            "event_id": event_id,
            "risk_level": risk,
            "source": event_data.get("source") or event_data.get("source_label") or "Industrial",
            "confidence": event_data.get("confidence", 0.90),
            "latitude": event_data.get("latitude") or (event_data.get("location") or {}).get("lat"),
            "longitude": event_data.get("longitude") or (event_data.get("location") or {}).get("lon"),
            "frp": event_data.get("frp", 0.0),
            "timestamp": event_data.get("timestamp", _iso_now()),
        }
        sse_manager.broadcast("high_risk_alert", alert_data, event_id=f"alert_{event_id}")

        # Seamless notification for high risk anomaly
        source_name = alert_data["source"]
        frp_val = alert_data["frp"]
        publish_notification({
            "id": f"notif_{event_id}",
            "event_id": event_id,
            "eventId": event_id,
            "type": "urgent",
            "title": f"High Risk Anomaly: {source_name}",
            "message": f"Critical FRP ({frp_val} MW) detected for {source_name}. Immediate review required.",
            "description": f"Critical FRP ({frp_val} MW) detected for {source_name}. Immediate review required.",
            "timestamp": alert_data["timestamp"],
            "read": False,
        })
        logger.info("SSE: high_risk_alert & notification broadcast for event %s (risk=%s)", event_id, risk)


def publish_high_risk_alert(alert_data: Dict[str, Any]) -> None:
    """Broadcast an explicit high_risk_alert frame."""
    alert_id = f"alert_{alert_data.get('event_id', uuid.uuid4())}"
    sse_manager.broadcast("high_risk_alert", alert_data, event_id=alert_id)


def publish_dashboard_update(summary_data: Dict[str, Any]) -> None:
    """Broadcast a dashboard_update frame with summary statistics."""
    payload = {**summary_data, "timestamp": _iso_now()}
    sse_manager.broadcast("dashboard_update", payload)


def publish_notification(notification_data: Dict[str, Any]) -> None:
    """Broadcast a notification frame."""
    payload = {
        **notification_data,
        "timestamp": notification_data.get("timestamp", _iso_now()),
    }
    notif_id = str(notification_data.get("id") or f"notif_{uuid.uuid4()}")
    sse_manager.broadcast("notification", payload, event_id=notif_id)


def publish_system_status(status: str, message: str = "") -> None:
    """Broadcast a system_status frame."""
    sse_manager.broadcast("system_status", {
        "status": status,
        "message": message,
        "server_time": _iso_now(),
        "active_clients": sse_manager.client_count,
    })


# ---------------------------------------------------------------------------
# Pipeline Integration Bridge (Section 5)
# ---------------------------------------------------------------------------

def process_and_broadcast_observation(
    observation: Dict[str, Any],
    app_state: Any,
    is_simulated: bool = False,
) -> Dict[str, Any]:
    """
    Executes the existing thermal processing pipeline on an incoming observation
    and broadcasts the result via SSE:
      1. Preprocessing & feature assembly
      2. Model classification with Experiment C (primary thermal-only runtime model)
      3. Geospatial context (OSM) & 7-day persistence extraction
      4. Risk engine evaluation (compute_risk)
      5. Registration in EventService store
      6. SSE broadcast: thermal_event, high_risk_alert (if High), notification,
         and dashboard_update
    """
    model_svc = getattr(app_state, "model_service", None)
    event_svc = getattr(app_state, "event_service", None)
    osm_svc = getattr(app_state, "osm_service", None)

    lat = float(observation.get("latitude") or observation.get("lat") or 0.0)
    lon = float(observation.get("longitude") or observation.get("lon") or observation.get("lng") or 0.0)
    frp = float(observation.get("frp") or 0.0)
    event_id = observation.get("id") or observation.get("event_id") or f"TH{uuid.uuid4().hex[:6].upper()}"

    # 1. Feature row assembly
    row = dict(observation)
    row["latitude"] = lat
    row["longitude"] = lon
    row["frp"] = frp
    row["event_id"] = event_id
    if "brightness" not in row:
        row["brightness"] = observation.get("brightness", 330.0)
    if "brightness_ti5" not in row:
        row["brightness_ti5"] = observation.get("brightness_ti5", 300.0)
    if "brightness_diff" not in row:
        row["brightness_diff"] = float(row["brightness"]) - float(row["brightness_ti5"])

    # 2. OSM Context lookup
    osm_dict = {}
    nearest_hazard_type = None
    if osm_svc:
        try:
            osm_dict = osm_svc.get_osm_context(lat, lon)
            from backend.api.events import _nearest_hazard_type
            nearest_hazard_type = _nearest_hazard_type(osm_dict)
        except Exception as exc:
            logger.warning("SSE pipeline: OSM context lookup failed: %s", exc)

    # 3. 7-Day Persistence extraction
    from backend.services.persistence_service import extract_persistence_from_row
    pers_dict = extract_persistence_from_row(row)
    active_days = pers_dict.get("active_days_last_7", 0)

    # 4. Classification via Experiment C (Primary runtime model)
    source = observation.get("source") or observation.get("source_label")
    confidence = float(observation.get("confidence") or 0.85)

    if model_svc and hasattr(model_svc, "is_loaded") and model_svc.is_loaded:
        from backend.services.classification_service import classify_event
        clf_result = classify_event(row, model_svc)
        pred_c = clf_result.get("thermal_only_estimate", {})
        source = pred_c.get("source", source)
        confidence = float(pred_c.get("confidence", confidence))

    if not source:
        source = "Industrial"

    # 5. Risk Assessment Engine
    from backend.services.risk_service import compute_risk
    nearest_dist = osm_dict.get("nearest_hazard_distance_m") if osm_dict else None
    risk_dict = compute_risk(
        frp=frp,
        active_days_last_7=active_days,
        nearest_hazard_distance_m=nearest_dist,
        classification_confidence=confidence,
        predicted_source=source,
        nearest_hazard_type=nearest_hazard_type,
    )
    risk_tier = risk_dict.get("tier", "LOW").upper()
    risk_score = float(risk_dict.get("score", 0.0))

    # Candidate facility name resolution
    from backend.services.facility_service import resolve_facility_name
    fac_info = resolve_facility_name(lat, lon, source)
    candidate_source = fac_info.get("name", "Regional Industrial Zone")
    candidate_type = fac_info.get("type", "Industrial Facility")

    # 6. Save into EventService in-memory store
    row["source_label"] = source
    row["_risk_score"] = risk_score
    row["_risk_tier"] = risk_tier
    row["candidate_source"] = candidate_source
    row["candidate_type"] = candidate_type
    row["simulated"] = is_simulated
    if event_svc:
        try:
            event_svc.add_event(row)
        except Exception as exc:
            logger.warning("SSE pipeline: failed to register event in event_service: %s", exc)

    # 7. Construct standard event payload
    now_iso = _iso_now()
    event_payload = {
        "id": event_id,
        "latitude": lat,
        "longitude": lon,
        "location": {"lat": lat, "lon": lon},
        "source": source,
        "source_label": source,
        "confidence": round(confidence, 4),
        "frp": round(frp, 2),
        "risk_level": risk_tier,
        "risk_tier": risk_tier,
        "risk_score": risk_score,
        "active_days_last_7": active_days,
        "candidate_source": candidate_source,
        "candidate_type": candidate_type,
        "timestamp": now_iso,
        "acq_date": observation.get("acq_date") or now_iso[:10],
        "satellite": observation.get("satellite") or "VIIRS-SNPP",
        "simulated": is_simulated,
    }

    # Broadcast event (and high_risk_alert + notification if High/Critical)
    publish_thermal_event(event_payload)

    # Broadcast updated dashboard statistics
    if event_svc:
        try:
            stats = event_svc.summary_stats()
            publish_dashboard_update({
                "total_events": stats.get("total_events", 0),
                "high_frp_events": stats.get("high_frp_events", 0),
                "source_distribution": stats.get("source_distribution", {}),
                "triggered_by": event_id,
            })
        except Exception as exc:
            logger.warning("SSE pipeline: could not publish dashboard update: %s", exc)

    return event_payload
