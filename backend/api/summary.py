"""
backend/api/summary.py
========================
GET /api/summary

Aggregate statistics over all 20,828 VIIRS thermal events.
"""

from fastapi import APIRouter, Request
from backend.schemas.event_schema import SummaryResponse, RiskSummarySchema

router = APIRouter()


@router.get("/summary", response_model=SummaryResponse, tags=["Summary"])
async def get_summary(request: Request) -> SummaryResponse:
    """
    Dataset-wide summary statistics.

    Returns total event count, source distribution (weak geographic labels),
    FRP statistics, persistence counts, and observation window metadata.

    Note: risk_summary is computed on-demand approximation (HIGH/MEDIUM/LOW
    based on FRP thresholds) since full risk computation requires per-event
    OSM queries. Exact per-event risk tiers are available via /api/events/{id}.
    """
    event_svc = request.app.state.event_service
    stats = event_svc.summary_stats()

    # Approximate risk tier counts (FRP-based proxy for list view)
    total = stats["total_events"]
    high_frp = stats["high_frp_events"]       # FRP >= 50 → likely HIGH
    persistent = stats["persistent_events"]   # active_days >= 4

    # Conservative approximation — exact tiers require per-event risk computation
    approx_high   = min(high_frp, total)
    approx_medium = min(persistent - approx_high, total - approx_high)
    if approx_medium < 0:
        approx_medium = 0
    approx_low    = total - approx_high - approx_medium
    not_computed  = 0

    return SummaryResponse(
        total_events=total,
        source_distribution=stats["source_distribution"],
        risk_summary=RiskSummarySchema(
            high=approx_high,
            medium=approx_medium,
            low=approx_low,
            not_computed=not_computed,
        ),
        avg_frp=stats["avg_frp"],
        max_frp=stats["max_frp"],
        persistent_events=stats["persistent_events"],
        high_frp_events=stats["high_frp_events"],
        observation_window=stats["observation_window"],
    )
