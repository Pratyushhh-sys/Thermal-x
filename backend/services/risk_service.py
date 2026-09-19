"""
backend/services/risk_service.py
==================================
Explainable 4-factor risk engine.

Formula (SIH specification — weights fixed, do not modify without documentation):

  thermal_score    = min(100, FRP / 150 * 100)
  persistence_score = active_days_last_7 / 7 * 100
  osm_score        = distance_band(nearest_hazard_distance_m)
  ai_score         = classification_confidence * 100

  risk = 0.30 * thermal + 0.30 * persistence + 0.20 * osm + 0.20 * ai

Risk tiers:
  HIGH   >= 70
  MEDIUM  45-69.99
  LOW    < 45

OSM distance bands:
  <= 100 m   → 100
  100-500 m  → 85
  500-1000 m → 60
  1-2 km     → 35
  > 2 km     → 15
  No data    → 15 (most conservative)

Industrial/mining hazard proximity bonus:
  If nearest hazard type is in {industrial, factory, chemical, refinery, gas, mine, quarry}
  AND source classification is Industrial or Mining:
  apply +5 bonus to osm_score (capped at 100).
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# --- Weights (spec-fixed) ---
WEIGHT_THERMAL     = 0.30
WEIGHT_PERSISTENCE = 0.30
WEIGHT_OSM         = 0.20
WEIGHT_AI          = 0.20

# --- Thresholds ---
TIER_HIGH   = 70.0
TIER_MEDIUM = 45.0

HAZARD_TYPES = frozenset({
    "industrial", "factory", "chemical", "refinery", "gas", "mine", "quarry"
})


def _osm_score_from_distance(distance_m: Optional[float]) -> float:
    """Map hazard distance (metres) to an OSM proximity score (0-100)."""
    if distance_m is None:
        return 15.0
    if distance_m <= 100:
        return 100.0
    if distance_m <= 500:
        return 85.0
    if distance_m <= 1000:
        return 60.0
    if distance_m <= 2000:
        return 35.0
    return 15.0


def _tier(score: float) -> str:
    if score >= TIER_HIGH:
        return "HIGH"
    if score >= TIER_MEDIUM:
        return "MEDIUM"
    return "LOW"


def compute_risk(
    frp: float,
    active_days_last_7: int,
    nearest_hazard_distance_m: Optional[float],
    classification_confidence: float,
    predicted_source: str = "Other",
    nearest_hazard_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute the 4-factor risk score.

    Parameters
    ----------
    frp                       : Fire Radiative Power (MW)
    active_days_last_7        : Days with detection in past 7 days
    nearest_hazard_distance_m : Haversine distance to nearest industrial/mining feature (m)
    classification_confidence : Exp C prediction confidence (0-1)
    predicted_source          : Predicted class label
    nearest_hazard_type       : OSM feature type of the nearest hazard

    Returns
    -------
    dict with score, tier, components{thermal, persistence, osm, ai}, weights
    """
    # --- Component scores ---
    thermal_score = min(100.0, (frp / 150.0) * 100.0)
    persistence_score = (active_days_last_7 / 7.0) * 100.0
    osm_score = _osm_score_from_distance(nearest_hazard_distance_m)
    ai_score = classification_confidence * 100.0

    # --- Industrial/mining hazard proximity bonus ---
    if (
        nearest_hazard_type in HAZARD_TYPES
        and predicted_source in {"Industrial", "Mining"}
        and nearest_hazard_distance_m is not None
        and nearest_hazard_distance_m <= 2000
    ):
        osm_score = min(100.0, osm_score + 5.0)

    # --- Weighted composite ---
    risk_score = (
        WEIGHT_THERMAL     * thermal_score
        + WEIGHT_PERSISTENCE * persistence_score
        + WEIGHT_OSM         * osm_score
        + WEIGHT_AI          * ai_score
    )
    risk_score = round(risk_score, 2)

    return {
        "score": risk_score,
        "tier": _tier(risk_score),
        "components": {
            "thermal":     round(thermal_score, 2),
            "persistence": round(persistence_score, 2),
            "osm":         round(osm_score, 2),
            "ai":          round(ai_score, 2),
        },
        "weights": {
            "thermal":     WEIGHT_THERMAL,
            "persistence": WEIGHT_PERSISTENCE,
            "osm":         WEIGHT_OSM,
            "ai":          WEIGHT_AI,
        },
    }
