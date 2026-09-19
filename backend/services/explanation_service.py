"""
backend/services/explanation_service.py
==========================================
Human-readable explanation generator for risk results.

Rules:
  - Only generates reasons from facts present in the data.
  - Does not claim facts not in the data (no fabrication).
  - Does not say "Confirmed Fire Cause" — uses "probable source".
  - Does not generate reasons for missing/null fields.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def generate_reasons(
    frp: float,
    active_days_last_7: int,
    persistence_ratio: float,
    gis_context: Dict[str, Any],
    classification: Dict[str, Any],
    risk_components: Dict[str, float],
) -> List[str]:
    """
    Generate human-readable explanations for a risk assessment.

    Parameters
    ----------
    frp                  : Fire Radiative Power (MW)
    active_days_last_7   : Days with a detection in the past 7 days
    persistence_ratio    : active_days / 7
    gis_context          : Output of OSMService.get_osm_context()
    classification       : thermal_only_estimate dict from classify_event()
    risk_components      : {thermal, persistence, osm, ai} scores

    Returns
    -------
    List of reason strings (3-6 typically)
    """
    reasons: List[str] = []

    # --- Thermal intensity ---
    thermal_score = risk_components.get("thermal", 0)
    if frp >= 100:
        reasons.append(f"Very high thermal intensity: FRP {frp:.1f} MW (score {thermal_score:.0f}/100)")
    elif frp >= 50:
        reasons.append(f"High thermal intensity: FRP {frp:.1f} MW (score {thermal_score:.0f}/100)")
    elif frp >= 15:
        reasons.append(f"Moderate thermal intensity: FRP {frp:.1f} MW (score {thermal_score:.0f}/100)")
    else:
        reasons.append(f"Low thermal intensity: FRP {frp:.1f} MW (score {thermal_score:.0f}/100)")

    # --- Persistence ---
    persistence_score = risk_components.get("persistence", 0)
    if active_days_last_7 >= 5:
        reasons.append(
            f"Persistent detection: active on {active_days_last_7} of the last 7 days "
            f"(ratio {persistence_ratio:.2f})"
        )
    elif active_days_last_7 >= 3:
        reasons.append(
            f"Frequent detection: active on {active_days_last_7} of the last 7 days"
        )
    elif active_days_last_7 >= 1:
        reasons.append(
            f"Intermittent detection: {active_days_last_7} day(s) in the last 7 days"
        )
    else:
        reasons.append("First or isolated detection in the last 7 days — no prior history in window")

    # --- GIS / OSM proximity ---
    hazard_distance = gis_context.get("nearest_hazard_distance_m")
    osm_score = risk_components.get("osm", 0)

    # Find nearest hazard facility with a distance
    nearest_hazard_type = None
    nearest_hazard_dist = None
    for htype in ["industrial", "factory", "chemical", "refinery", "gas", "mine", "quarry", "pipeline"]:
        entry = gis_context.get(f"nearest_{htype}")
        if entry:
            d = entry.get("distance_m")
            if d is not None and (nearest_hazard_dist is None or d < nearest_hazard_dist):
                nearest_hazard_dist = d
                nearest_hazard_type = htype

    if nearest_hazard_type and nearest_hazard_dist is not None:
        dist_label = _distance_label(nearest_hazard_dist)
        reasons.append(
            f"{nearest_hazard_type.title()} infrastructure detected {dist_label} "
            f"(OSM proximity score {osm_score:.0f}/100)"
        )
    else:
        reasons.append(
            f"No nearby industrial/mining infrastructure found in OSM cache "
            f"(OSM proximity score {osm_score:.0f}/100)"
        )

    # --- Forest / cropland context ---
    forest_entry = gis_context.get("nearest_forest")
    crop_entry   = gis_context.get("nearest_cropland")
    if forest_entry and forest_entry.get("distance_m", 9999) < 2000:
        reasons.append(
            f"Forest area within {forest_entry['distance_m']:.0f} m — "
            "potential vegetation fire"
        )
    if crop_entry and crop_entry.get("distance_m", 9999) < 1000:
        reasons.append(
            f"Agricultural land within {crop_entry['distance_m']:.0f} m — "
            "potential crop residue burning"
        )

    # --- AI classification ---
    ai_score = risk_components.get("ai", 0)
    pred_source = classification.get("source", "Unknown")
    confidence = classification.get("confidence", 0.0)
    exp_name = classification.get("model_experiment", "")

    reasons.append(
        f"Probable source (thermal signal only): {pred_source} "
        f"— confidence {confidence * 100:.0f}% (AI score {ai_score:.0f}/100)"
    )

    if "Experiment C" in exp_name or "thermal" in exp_name.lower():
        reasons.append(
            "NOTE: Classification uses thermal/temporal features only — "
            "source_label is a weak geographic label, NOT verified fire cause"
        )

    return reasons


def _distance_label(distance_m: float) -> str:
    """Convert distance in metres to a human-readable range label."""
    if distance_m <= 100:
        return f"within {distance_m:.0f} m (< 100 m)"
    if distance_m <= 500:
        return f"within {distance_m:.0f} m (100-500 m)"
    if distance_m <= 1000:
        return f"within {distance_m:.0f} m (500-1000 m)"
    if distance_m <= 2000:
        return f"within {distance_m:.0f} m (1-2 km)"
    return f"at {distance_m/1000:.1f} km (> 2 km)"
