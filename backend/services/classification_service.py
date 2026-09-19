"""
backend/services/classification_service.py
============================================
Thin wrapper around ModelService that assembles the feature vector
in the exact saved column order for each experiment.

Handles:
  - NaN weather columns (always NaN in current dataset — XGBoost-safe)
  - Day 1 column name conventions
  - Returns dual prediction (Exp C + Exp A) for API responses
"""

import logging
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


def _safe_float(val: Any, default: float = np.nan) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return f
    except (ValueError, TypeError):
        return default


def build_feature_dict(row: Dict[str, Any]) -> Dict[str, float]:
    """
    Convert a raw feature CSV row into a flat float dict for model prediction.

    Uses pre-computed features from the Day 1 pipeline.
    Missing values → NaN (XGBoost handles natively).

    Parameters
    ----------
    row : dict from EventService.get_event_row()

    Returns
    -------
    dict{feature_name: float}  — all numeric, NaN for missing
    """
    feature_map = {}

    # Location
    feature_map["latitude"]  = _safe_float(row.get("latitude"))
    feature_map["longitude"] = _safe_float(row.get("longitude"))

    # Temporal (date)
    feature_map["hour"]  = _safe_float(row.get("hour"))
    feature_map["month"] = _safe_float(row.get("month"))

    # Thermal
    feature_map["frp"]                = _safe_float(row.get("frp"))
    feature_map["brightness"]         = _safe_float(row.get("brightness"))
    feature_map["brightness_ti5"]     = _safe_float(row.get("brightness_ti5"))
    feature_map["brightness_diff"]    = _safe_float(row.get("brightness_diff"))
    feature_map["confidence_numeric"] = _safe_float(row.get("confidence_numeric"))
    feature_map["scan"]               = _safe_float(row.get("scan"))
    feature_map["track"]              = _safe_float(row.get("track"))

    # 7-day persistence
    feature_map["active_days_last_7"]       = _safe_float(row.get("active_days_last_7"), 0.0)
    feature_map["persistence_ratio"]        = _safe_float(row.get("persistence_ratio"), 0.0)
    feature_map["observation_count_last_7"] = _safe_float(row.get("observation_count_last_7"), 0.0)
    feature_map["avg_frp"]                  = _safe_float(row.get("avg_frp"))
    feature_map["max_frp"]                  = _safe_float(row.get("max_frp"))
    feature_map["min_frp"]                  = _safe_float(row.get("min_frp"))
    feature_map["frp_trend"]                = _safe_float(row.get("frp_trend"), 0.0)
    feature_map["frp_std"]                  = _safe_float(row.get("frp_std"), 0.0)
    feature_map["night_count"]              = _safe_float(row.get("night_count"), 0.0)
    feature_map["day_count"]               = _safe_float(row.get("day_count"), 0.0)

    # Weather (all NaN in current dataset — XGBoost-safe)
    feature_map["wind_speed"]      = _safe_float(row.get("wind_speed"))
    feature_map["wind_direction"]  = _safe_float(row.get("wind_direction"))
    feature_map["temperature"]     = _safe_float(row.get("temperature"))
    feature_map["humidity"]        = _safe_float(row.get("humidity"))

    # OSM distance features (only used by Exp A — Exp C ignores them)
    for col in [
        "distance_to_industrial", "distance_to_factory", "distance_to_chemical",
        "distance_to_refinery", "distance_to_gas", "distance_to_mine",
        "distance_to_quarry", "distance_to_pipeline", "distance_to_forest",
        "distance_to_cropland",
    ]:
        feature_map[col] = _safe_float(row.get(col))

    # OSM context flags (Exp A)
    for col in [
        "ctx_agricultural_context", "ctx_forest_context",
        "ctx_industrial_context", "ctx_mining_context",
    ]:
        feature_map[col] = _safe_float(row.get(col), 0.0)

    return feature_map


def classify_event(row: Dict[str, Any], model_service) -> Dict[str, Any]:
    """
    Run both Exp C (thermal-only) and Exp A (contextual) predictions.

    Parameters
    ----------
    row          : raw feature dict from EventService
    model_service: loaded ModelService singleton

    Returns
    -------
    dict with:
      thermal_only_estimate  : Exp C prediction
      contextual_estimate    : Exp A prediction
      recommended            : "thermal_only_estimate"
    """
    feature_dict = build_feature_dict(row)

    # Exp C — primary honest prediction
    pred_c = model_service.predict_exp_c(feature_dict)

    # Exp A — contextual (labeled as HIGH leakage)
    pred_a = None
    try:
        pred_a = model_service.predict_exp_a(feature_dict)
    except Exception as exc:
        logger.warning("Exp A prediction failed (non-blocking): %s", exc)

    return {
        "thermal_only_estimate": pred_c,
        "contextual_estimate": pred_a,
        "recommended": "thermal_only_estimate",
    }
