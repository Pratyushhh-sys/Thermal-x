"""
backend/api/alerts.py
======================
Alert forwarding endpoints for HIGH/CRITICAL risk thermal events.

  GET  /api/authorities                        — list selectable authorities
  POST /api/alerts/{event_id}/forward          — forward an alert
  GET  /api/alerts/{event_id}/forward-history  — history of forwarding actions

Validation:
  - Event must exist in the event service.
  - Risk tier must be HIGH or CRITICAL (>= 70 risk score).
  - Authority must be non-empty.
  - Message must be at least 10 characters.

Prototype note:
  Forwarding status is SUBMITTED_FOR_FORWARDING.
  No actual email/SMS/government API integration exists in this prototype.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request

from backend.schemas.alert_forward_schema import (
    AlertForwardRequest,
    AlertForwardResponse,
    AuthorityRecord,
    ForwardHistoryResponse,
)
from backend.services import alert_forward_service as fwd_svc
from backend.services.classification_service import classify_event
from backend.services.persistence_service import extract_persistence_from_row
from backend.services.risk_service import compute_risk
from backend.api.events import _nearest_hazard_type

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /api/authorities
# ---------------------------------------------------------------------------
@router.get("/authorities", response_model=List[AuthorityRecord], tags=["Alert Forwarding"])
async def list_authorities() -> List[AuthorityRecord]:
    """
    Return the list of selectable concerned authorities for alert forwarding.
    These are configurable mock records for the SIH prototype.
    """
    return fwd_svc.get_authorities()


# ---------------------------------------------------------------------------
# POST /api/alerts/{event_id}/forward
# ---------------------------------------------------------------------------
@router.post(
    "/alerts/{event_id}/forward",
    response_model=AlertForwardResponse,
    tags=["Alert Forwarding"],
)
async def forward_alert(
    event_id: str,
    payload: AlertForwardRequest,
    request: Request,
) -> AlertForwardResponse:
    """
    Forward a HIGH or CRITICAL risk thermal event to a concerned authority.

    Validation:
      1. Event must exist.
      2. Event must be HIGH or CRITICAL risk tier (computed by the backend pipeline).
      3. Authority information must be present.
      4. Message must be non-empty (min 10 chars).

    Prototype status: SUBMITTED_FOR_FORWARDING
    This does NOT deliver the alert to any real government system.
    """
    event_svc = request.app.state.event_service
    model_svc = request.app.state.model_service
    osm_svc = request.app.state.osm_service

    # --- 1. Validate event exists ---
    try:
        row = event_svc.get_event_row(event_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")

    lat = float(row.get("latitude", 0))
    lon = float(row.get("longitude", 0))
    frp = float(row.get("frp", 0) or 0)

    # --- 2. Run pipeline to get actual risk tier (do NOT trust frontend) ---
    try:
        pers_dict = extract_persistence_from_row(row)
    except Exception as exc:
        logger.warning("Persistence extraction failed for %s: %s", event_id, exc)
        pers_dict = {
            "active_days_last_7": 0, "persistence_ratio": 0.0,
            "observation_count_last_7": 0, "avg_frp": None, "max_frp": None,
            "min_frp": None, "frp_trend": 0.0, "frp_std": 0.0,
            "night_count": 0, "day_count": 0, "trend_label": "unknown",
        }

    osm_dict = {}
    try:
        osm_dict = osm_svc.get_osm_context(lat, lon)
    except Exception as exc:
        logger.warning("OSM context failed for %s: %s — using empty", event_id, exc)
        osm_dict = {"buffers": {"100m": [], "500m": [], "1000m": []}, "nearest_hazard_distance_m": None}

    try:
        clf_result = classify_event(row, model_svc)
        pred_c = clf_result["thermal_only_estimate"]
    except Exception as exc:
        logger.warning("Classification failed for %s: %s — using defaults", event_id, exc)
        pred_c = {"source": "Other", "confidence": 0.0, "probabilities": {}, "model_experiment": "fallback"}

    nearest_hazard_type = _nearest_hazard_type(osm_dict)
    risk_dict = compute_risk(
        frp=frp,
        active_days_last_7=pers_dict["active_days_last_7"],
        nearest_hazard_distance_m=osm_dict.get("nearest_hazard_distance_m"),
        classification_confidence=pred_c["confidence"],
        predicted_source=pred_c["source"],
        nearest_hazard_type=nearest_hazard_type,
    )

    risk_tier = risk_dict["tier"]       # HIGH / MEDIUM / LOW
    risk_score = risk_dict["score"]

    # --- 3. Validate eligibility ---
    if risk_tier not in fwd_svc.ELIGIBLE_TIERS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Event {event_id} has risk tier '{risk_tier}' (score {risk_score:.1f}). "
                "Only HIGH and CRITICAL risk events are eligible for authority forwarding."
            ),
        )

    # --- 4. Validate payload (Pydantic handles message min_length) ---
    if not payload.authority_id or not payload.authority_name:
        raise HTTPException(status_code=422, detail="Authority must be selected before forwarding.")

    if not payload.message or len(payload.message.strip()) < 10:
        raise HTTPException(status_code=422, detail="A non-empty forwarding message is required (min 10 characters).")

    # --- 5. Record forwarding ---
    response = fwd_svc.forward_alert(
        event_id=event_id,
        risk_tier=risk_tier,
        risk_score=risk_score,
        request=payload,
    )

    return response


# ---------------------------------------------------------------------------
# GET /api/alerts/{event_id}/forward-history
# ---------------------------------------------------------------------------
@router.get(
    "/alerts/{event_id}/forward-history",
    response_model=ForwardHistoryResponse,
    tags=["Alert Forwarding"],
)
async def get_forward_history(
    event_id: str,
    request: Request,
) -> ForwardHistoryResponse:
    """
    Return the forwarding history for a thermal event.
    Returns an empty list if the event has never been forwarded.
    """
    event_svc = request.app.state.event_service
    try:
        event_svc.get_event_row(event_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")

    return fwd_svc.get_forward_history(event_id)
