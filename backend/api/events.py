"""
backend/api/events.py
=======================
GET /api/events                 — paginated event list
GET /api/events/{event_id}      — full intelligence for one event

The full intelligence pipeline for a single event:
  1. Load pre-computed feature row from dataset
  2. Extract persistence features (pre-computed, fast)
  3. Fetch OSM context (cached BallTrees, no Overpass queries)
  4. Run dual classification: Exp C (thermal-only) + Exp A (contextual)
  5. Compute 4-factor risk score
  6. Generate human-readable explanations
  7. Return final structured JSON
"""

import logging
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from backend.schemas.event_schema import (
    EventListItem,
    EventResponse,
    LocationSchema,
    FIRMSSchema,
    PersistenceSchema,
    GISContextSchema,
    NearbyFacilitySchema,
    BufferItemSchema,
    ClassificationPairSchema,
    ClassificationResultSchema,
    RiskSchema,
    RiskComponentsSchema,
    EventMetadataSchema,
    EnvironmentSchema,
)
from backend.services.classification_service import classify_event
from backend.services.persistence_service import extract_persistence_from_row
from backend.services.risk_service import compute_risk
from backend.services.explanation_service import generate_reasons

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /api/events  — paginated event list
# ---------------------------------------------------------------------------
@router.get("/events", response_model=List[EventListItem], tags=["Events"])
async def list_events(
    request: Request,
    limit:  int            = Query(100, ge=1, le=1000, description="Max events to return"),
    offset: int            = Query(0, ge=0, description="Pagination offset"),
    source: Optional[str]  = Query(None, description="Filter by source_label (e.g. Industrial)"),
    satellite: Optional[str] = Query(None, description="Filter by satellite (e.g. N20)"),
    min_frp: Optional[float] = Query(None, description="Minimum FRP (MW)"),
    max_frp: Optional[float] = Query(None, description="Maximum FRP (MW)"),
) -> List[EventListItem]:
    """
    Return a paginated list of thermal events from the pre-computed dataset.

    Fields marked `source_label` are WEAK GEOGRAPHIC LABELS from OSM proximity,
    NOT verified fire-cause ground truth.
    """
    event_svc = request.app.state.event_service
    model_svc = request.app.state.model_service
    osm_svc   = request.app.state.osm_service

    rows = event_svc.get_events(
        limit=limit,
        offset=offset,
        source_filter=source,
        satellite_filter=satellite,
        min_frp=min_frp,
        max_frp=max_frp,
        raw_rows=True,
    )

    items = []
    for r in rows:
        try:
            # Basic fields
            item_dict = event_svc._row_to_list_item(pd.Series(r))
            
            # Compute ML / Risk on the fly for the page
            lat = float(r.get("latitude", 0))
            lon = float(r.get("longitude", 0))
            frp = float(r.get("frp", 0) or 0)
            
            # Classification
            clf = classify_event(r, model_svc)
            pred_c = clf["thermal_only_estimate"]
            item_dict["source_label"] = pred_c["source"] # Use ML prediction for probable source
            
            # Persistence & OSM for Risk
            pers_dict = extract_persistence_from_row(r)
            try:
                osm_dict = osm_svc.get_osm_context(lat, lon)
            except Exception:
                osm_dict = {}
                
            nearest_htype = _nearest_hazard_type(osm_dict)
            risk_dict = compute_risk(
                frp=frp,
                active_days_last_7=pers_dict["active_days_last_7"],
                nearest_hazard_distance_m=osm_dict.get("nearest_hazard_distance_m"),
                classification_confidence=pred_c["confidence"],
                predicted_source=pred_c["source"],
                nearest_hazard_type=nearest_htype,
            )
            
            item_dict["risk_tier"] = risk_dict["tier"]
            item_dict["risk_score"] = risk_dict["score"]

            items.append(EventListItem(**item_dict))
        except Exception as exc:
            logger.warning("Could not serialize event %s: %s", r.get("event_id"), exc)
    return items


# ---------------------------------------------------------------------------
# GET /api/events/{event_id}  — full intelligence pipeline
# ---------------------------------------------------------------------------
@router.get("/events/{event_id}", response_model=EventResponse, tags=["Events"])
async def get_event(event_id: str, request: Request) -> EventResponse:
    """
    Full intelligence result for a single thermal event.

    Runs the complete pipeline:
      Feature Extraction → Classification (Exp C + A) → OSM Context →
      Persistence → Risk Engine → Explanation → Final JSON

    Classification is labeled 'Probable Source' (NOT 'Confirmed Fire Cause').
    source_label is a weak geographic label from OSM proximity.
    """
    event_svc  = request.app.state.event_service
    model_svc  = request.app.state.model_service
    osm_svc    = request.app.state.osm_service

    # --- 1. Load event row ---
    try:
        row = event_svc.get_event_row(event_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")

    lat = float(row.get("latitude", 0))
    lon = float(row.get("longitude", 0))
    frp = float(row.get("frp", 0) or 0)

    # --- 2. Persistence (pre-computed) ---
    pers_dict = extract_persistence_from_row(row)

    # --- 3. OSM context (cached BallTrees) ---
    osm_dict = {}
    try:
        osm_dict = osm_svc.get_osm_context(lat, lon)
    except Exception as exc:
        logger.warning("OSM context failed for %s: %s — returning empty", event_id, exc)
        osm_dict = {
            "buffers": {"100m": [], "500m": [], "1000m": []},
            "nearest_hazard_distance_m": None,
        }

    # --- 4. Classification (dual) ---
    clf_result = classify_event(row, model_svc)
    pred_c = clf_result["thermal_only_estimate"]
    pred_a = clf_result.get("contextual_estimate")

    # --- 5. Risk engine ---
    nearest_hazard_type = _nearest_hazard_type(osm_dict)
    risk_dict = compute_risk(
        frp=frp,
        active_days_last_7=pers_dict["active_days_last_7"],
        nearest_hazard_distance_m=osm_dict.get("nearest_hazard_distance_m"),
        classification_confidence=pred_c["confidence"],
        predicted_source=pred_c["source"],
        nearest_hazard_type=nearest_hazard_type,
    )

    # --- 6. Explanations ---
    reasons = generate_reasons(
        frp=frp,
        active_days_last_7=pers_dict["active_days_last_7"],
        persistence_ratio=pers_dict["persistence_ratio"],
        gis_context=osm_dict,
        classification=pred_c,
        risk_components=risk_dict["components"],
    )

    # --- 7. Assemble response ---
    return _build_response(
        event_id=event_id,
        row=row,
        lat=lat, lon=lon, frp=frp,
        pers_dict=pers_dict,
        osm_dict=osm_dict,
        pred_c=pred_c,
        pred_a=pred_a,
        risk_dict=risk_dict,
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
HAZARD_TYPES = frozenset({
    "industrial", "factory", "chemical", "refinery", "gas", "mine", "quarry", "pipeline"
})


def _nearest_hazard_type(osm_dict: dict) -> Optional[str]:
    """Find which hazard type is closest."""
    best_type = None
    best_dist = float("inf")
    for htype in HAZARD_TYPES:
        entry = osm_dict.get(f"nearest_{htype}")
        if entry and entry.get("distance_m") is not None:
            if entry["distance_m"] < best_dist:
                best_dist = entry["distance_m"]
                best_type = htype
    return best_type


def _build_nearby(osm_dict: dict, key: str) -> Optional[NearbyFacilitySchema]:
    entry = osm_dict.get(f"nearest_{key}")
    if not entry:
        return None
    return NearbyFacilitySchema(
        type=entry["type"],
        name=entry.get("name"),
        distance_m=entry["distance_m"],
        lat=entry.get("lat"),
        lon=entry.get("lon"),
    )


def _build_buffers(osm_dict: dict) -> dict:
    raw_buffers = osm_dict.get("buffers", {"100m": [], "500m": [], "1000m": []})
    result = {}
    for key, items in raw_buffers.items():
        result[key] = [
            BufferItemSchema(
                type=it["type"],
                name=it.get("name"),
                distance_m=it["distance_m"],
            )
            for it in items
        ]
    return result


def _to_clf_schema(pred: dict) -> ClassificationResultSchema:
    return ClassificationResultSchema(
        source=pred["source"],
        label=pred.get("label", "Probable Source"),
        confidence=pred["confidence"],
        probabilities=pred["probabilities"],
        model_experiment=pred.get("model_experiment", ""),
        label_type=pred.get("label_type", "weak_geographic_labels_NOT_verified_fire_cause"),
    )


def _day_night_str(row: dict) -> Optional[str]:
    val = row.get("day_night")
    if val is None:
        return None
    try:
        return "D" if int(float(val)) == 1 else "N"
    except (ValueError, TypeError):
        return str(val) if val else None


def _build_response(
    event_id, row, lat, lon, frp,
    pers_dict, osm_dict, pred_c, pred_a,
    risk_dict, reasons,
) -> EventResponse:
    obs_window = "2026-08-24 to 2026-09-18 (26 days)"

    return EventResponse(
        id=event_id,
        location=LocationSchema(lat=lat, lon=lon),
        firms=FIRMSSchema(
            frp=frp,
            brightness=float(row.get("brightness") or 0),
            brightness_ti5=_opt_float(row.get("brightness_ti5")),
            brightness_diff=_opt_float(row.get("brightness_diff")),
            confidence=_opt_float(row.get("confidence_numeric")),
            satellite=str(row.get("satellite")) if row.get("satellite") else None,
            acq_date=str(row.get("acq_date")) if row.get("acq_date") else None,
            acq_time=_acq_time(row),
            scan=_opt_float(row.get("scan")),
            track=_opt_float(row.get("track")),
            day_night=_day_night_str(row),
        ),
        persistence=PersistenceSchema(**pers_dict),
        gis_context=GISContextSchema(
            nearest_industrial=_build_nearby(osm_dict, "industrial"),
            nearest_factory=_build_nearby(osm_dict, "factory"),
            nearest_chemical=_build_nearby(osm_dict, "chemical"),
            nearest_refinery=_build_nearby(osm_dict, "refinery"),
            nearest_gas=_build_nearby(osm_dict, "gas"),
            nearest_mine=_build_nearby(osm_dict, "mine"),
            nearest_quarry=_build_nearby(osm_dict, "quarry"),
            nearest_pipeline=_build_nearby(osm_dict, "pipeline"),
            nearest_forest=_build_nearby(osm_dict, "forest"),
            nearest_cropland=_build_nearby(osm_dict, "cropland"),
            buffers=_build_buffers(osm_dict),
            nearest_hazard_distance_m=osm_dict.get("nearest_hazard_distance_m"),
        ),
        classification=ClassificationPairSchema(
            thermal_only_estimate=_to_clf_schema(pred_c),
            contextual_estimate=_to_clf_schema(pred_a) if pred_a else None,
            recommended="thermal_only_estimate",
        ),
        risk=RiskSchema(
            score=risk_dict["score"],
            tier=risk_dict["tier"],
            components=RiskComponentsSchema(**risk_dict["components"]),
            reasons=reasons,
            weights=risk_dict["weights"],
        ),
        environment=EnvironmentSchema(
            wind_speed=_opt_float(row.get("wind_speed")),
            wind_direction=_opt_float(row.get("wind_direction")),
            temperature=_opt_float(row.get("temperature")),
            humidity=_opt_float(row.get("humidity")),
        ),
        metadata=EventMetadataSchema(
            event_id=event_id,
            model_primary="source_classifier_exp_c.pkl (Experiment C — thermal+temporal only)",
            model_contextual="source_classifier.pkl (Experiment A — all features, HIGH leakage)",
            label_type="weak_geographic_labels_NOT_verified_fire_cause",
            dataset="FIRMS VIIRS (NASA) — India 67,6,98,37",
            obs_window=obs_window,
            persistence_radius_km=1.0,
        ),
    )


def _opt_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        import numpy as np
        f = float(val)
        return None if (isinstance(f, float) and np.isnan(f)) else f
    except (ValueError, TypeError):
        return None


def _acq_time(row: dict) -> Optional[str]:
    t = row.get("acq_time")
    if t is None:
        return None
    try:
        return f"{int(t):04d} UTC"
    except (ValueError, TypeError):
        return str(t)
