"""
backend/api/health.py
=======================
GET /api/health

Returns the status of:
  - API server
  - Model (loaded, experiment, feature count)
  - Dataset (event count)
  - OSM cache (number of feature types loaded)
"""

from fastapi import APIRouter, Request
from backend.schemas.event_schema import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(request: Request) -> HealthResponse:
    """
    Backend health check.

    Returns model load status, dataset size, and OSM cache status.
    """
    model_svc  = request.app.state.model_service
    event_svc  = request.app.state.event_service
    osm_svc    = request.app.state.osm_service

    model_loaded = model_svc.is_loaded
    events_available = 0
    try:
        events_available = event_svc.get_total_count()
    except Exception:
        pass

    obs_window = {}
    try:
        obs_window = event_svc.obs_window()
    except Exception:
        pass

    return HealthResponse(
        status="ok" if model_loaded else "degraded",
        model_loaded=model_loaded,
        model_experiment="Experiment C (primary) + Experiment A (contextual)",
        model_feature_count=model_svc.exp_c_feature_count if model_loaded else 0,
        events_available=events_available,
        osm_cache_types=osm_svc.loaded_type_count,
        details={
            "exp_c_features": model_svc.exp_c_feature_count if model_loaded else None,
            "exp_a_features": model_svc.exp_a_feature_count if model_loaded else None,
            "classes": model_svc.class_names if model_loaded else [],
            "osm_types_loaded": osm_svc.loaded_types,
            "obs_window": obs_window,
        },
    )
