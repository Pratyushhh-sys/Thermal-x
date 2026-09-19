"""
backend/services/persistence_service.py
==========================================
Per-event 7-day persistence feature service.

For /api/events/{id} we use the pre-computed values from the feature CSV
(fast path — no re-computation needed, the values were already computed
during Day 1 feature engineering with the full 26-day window).

The `trend_label` field classifies persistence qualitatively:
  - "persistent"   : active_days >= 5 (seen on 5+ of last 7 days)
  - "frequent"     : active_days >= 3
  - "intermittent" : active_days >= 1
  - "new"          : active_days == 0 (first detection or isolated)
  - "declining"    : frp_trend < -2 MW/day  (overrides above if strong decline)
"""

import logging
from typing import Any, Dict

import numpy as np

logger = logging.getLogger(__name__)


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if (isinstance(f, float) and np.isnan(f)) else f
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _trend_label(active_days: int, frp_trend: float) -> str:
    """Classify persistence qualitatively."""
    if frp_trend < -2.0 and active_days >= 2:
        return "declining"
    if active_days >= 5:
        return "persistent"
    if active_days >= 3:
        return "frequent"
    if active_days >= 1:
        return "intermittent"
    return "new"


def extract_persistence_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract pre-computed 7-day persistence features from a feature CSV row.

    Uses pre-computed values — no re-computation. These were calculated
    during Day 1 with Haversine spatial matching at 1.0 km radius.

    Parameters
    ----------
    row : dict from EventService.get_event_row()

    Returns
    -------
    dict compatible with PersistenceSchema
    """
    active_days  = _safe_int(row.get("active_days_last_7"), 0)
    pers_ratio   = _safe_float(row.get("persistence_ratio"), 0.0)
    obs_count    = _safe_int(row.get("observation_count_last_7"), 0)
    avg_frp      = _safe_float(row.get("avg_frp"), None)   # type: ignore[arg-type]
    max_frp      = _safe_float(row.get("max_frp"), None)   # type: ignore[arg-type]
    min_frp      = _safe_float(row.get("min_frp"), None)   # type: ignore[arg-type]
    frp_trend    = _safe_float(row.get("frp_trend"), 0.0)
    frp_std      = _safe_float(row.get("frp_std"), 0.0)
    night_count  = _safe_int(row.get("night_count"), 0)
    day_count    = _safe_int(row.get("day_count"), 0)

    # Handle sentinel NaN for avg/max/min when obs_count == 0
    if obs_count == 0:
        avg_frp = None
        max_frp = None
        min_frp = None

    trend = _trend_label(active_days, frp_trend)

    return {
        "active_days_last_7": active_days,
        "persistence_ratio": round(pers_ratio, 4),
        "observation_count_last_7": obs_count,
        "avg_frp": round(avg_frp, 2) if avg_frp is not None else None,
        "max_frp": round(max_frp, 2) if max_frp is not None else None,
        "min_frp": round(min_frp, 2) if min_frp is not None else None,
        "frp_trend": round(frp_trend, 4),
        "frp_std": round(frp_std, 4),
        "night_count": night_count,
        "day_count": day_count,
        "trend_label": trend,
    }
