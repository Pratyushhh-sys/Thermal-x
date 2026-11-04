"""
backend/services/event_service.py
====================================
Loads the pre-computed feature dataset at startup and serves
thermal event records with stable IDs.

Event IDs are formatted as TH{n:05d} (e.g., TH00000, TH00042, TH20827).

No retraining, no re-fetching. Reads from:
  data/features/source_classification_features.csv  (20,828 rows)
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from backend.services.facility_service import resolve_facility_name

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_CSV_ORIGINAL = PROJECT_ROOT / "data" / "features" / "source_classification_features.csv"
FEATURES_CSV_WEATHER = PROJECT_ROOT / "data" / "processed" / "firms_weather_enriched.csv"
FEATURES_CSV = FEATURES_CSV_WEATHER if FEATURES_CSV_WEATHER.exists() else FEATURES_CSV_ORIGINAL
OBS_WINDOW_JSON = PROJECT_ROOT / "data" / "raw" / "obs_window.json"


class EventService:
    """
    In-memory event store backed by the Day 1 feature CSV.

    Loaded once at startup. Provides:
      - get_events()     → paginated list with optional filters
      - get_event_row()  → single raw row dict by event_id
      - summary_stats()  → aggregate statistics
    """

    def __init__(self) -> None:
        self._df: Optional[pd.DataFrame] = None
        self._obs_window: dict = {}

    def load(self) -> None:
        """Load feature CSV into memory. Called once at startup."""
        if not FEATURES_CSV.exists():
            raise FileNotFoundError(
                f"Feature dataset not found: {FEATURES_CSV}\n"
                "Run: python ml/feature_engineering/build_features.py"
            )

        logger.info("Loading feature dataset: %s", FEATURES_CSV)
        df = pd.read_csv(FEATURES_CSV, low_memory=False)

        # Assign stable event IDs
        df["event_id"] = [f"TH{i:05d}" for i in range(len(df))]
        df["event_idx"] = df.index

        # Normalize NaN → None-friendly types
        df = df.where(pd.notnull(df), other=None)

        self._df = df
        logger.info("EventService loaded: %d events, %d columns", len(df), len(df.columns))

        # BUG-B01: Pre-compute lightweight risk_tier and risk_score using FRP+persistence proxy
        # This avoids running the full ML pipeline on every list request.
        # Vectorized for fast load over 20k rows.
        import numpy as np
        frp_vals = df["frp"].fillna(0.0).astype(float) if "frp" in df.columns else np.zeros(len(df))
        days = df["active_days_last_7"].fillna(0).astype(int) if "active_days_last_7" in df.columns else np.zeros(len(df))
        
        # Exact proxy math aligned with risk_service.py (Base 19.0 points for avg OSM + AI)
        thermal = np.minimum(100.0, (frp_vals / 60.0) * 100.0)
        persistence = np.minimum(100.0, (days / 4.0) * 100.0)
        scores = np.round(0.30 * thermal + 0.30 * persistence + 19.0, 2)
        df["_risk_score"] = scores
        
        conditions = [
            (scores >= 70.0),
            (scores >= 45.0)
        ]
        choices = ["HIGH", "MEDIUM"]
        df["_risk_tier"] = np.select(conditions, choices, default="LOW")
        self._df = df
        logger.info("EventService loaded: %d events (risk tiers pre-computed)", len(df))

        # Load observation window metadata
        import json
        if OBS_WINDOW_JSON.exists():
            with open(OBS_WINDOW_JSON) as f:
                self._obs_window = json.load(f)
        else:
            self._obs_window = {
                "obs_start": "unknown",
                "obs_end": "unknown",
                "obs_days": "unknown",
            }

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------
    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        source_filter: Optional[str] = None,
        satellite_filter: Optional[str] = None,
        min_frp: Optional[float] = None,
        max_frp: Optional[float] = None,
        raw_rows: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return paginated event list with optional filters."""
        self._assert_loaded()

        # BUG-B10: Only copy when we actually need to filter — avoids 15MB alloc on every request
        needs_filter = any([source_filter, satellite_filter, min_frp is not None, max_frp is not None])
        df = self._df.copy() if needs_filter else self._df

        if source_filter:
            df = df[df["source_label"].str.lower() == source_filter.lower()]
        if satellite_filter:
            sat_col = "satellite" if "satellite" in df.columns else None
            if sat_col:
                df = df[df[sat_col].str.upper() == satellite_filter.upper()]
        if min_frp is not None:
            df = df[df["frp"] >= min_frp]
        if max_frp is not None:
            df = df[df["frp"] <= max_frp]

        # Prioritize highest intensity (and thus highest risk) events
        if "frp" in df.columns:
            df = df.sort_values(by="frp", ascending=False)
            
            # Spatial decluttering: Ensure even distribution by picking only the highest 
            # FRP event per ~11km grid cell (1 decimal degree)
            df["lat_grid"] = df["latitude"].round(1)
            df["lon_grid"] = df["longitude"].round(1)
            df = df.drop_duplicates(subset=["lat_grid", "lon_grid"], keep="first")
            df = df.drop(columns=["lat_grid", "lon_grid"])

        df = df.iloc[offset: offset + limit]

        if raw_rows:
            return [row.to_dict() for _, row in df.iterrows()]

        return [self._row_to_list_item(row) for _, row in df.iterrows()]

    def get_top_frp_rows(self, n: int = 10) -> List[Dict[str, Any]]:
        """BUG-B05 fix: Return top-N rows by FRP across the entire dataset."""
        self._assert_loaded()
        top = self._df.nlargest(n, "frp")
        return [row.to_dict() for _, row in top.iterrows()]


    def get_event_row(self, event_id: str) -> Dict[str, Any]:
        """Return the full raw feature row for a given event_id."""
        self._assert_loaded()

        mask = self._df["event_id"] == event_id
        if not mask.any():
            raise KeyError(f"Event not found: {event_id}")

        row = self._df[mask].iloc[0]
        return row.to_dict()

    def get_total_count(self) -> int:
        self._assert_loaded()
        return len(self._df)

    def summary_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics over the full dataset."""
        self._assert_loaded()
        df = self._df

        source_dist: Dict[str, int] = {}
        if "source_label" in df.columns:
            source_dist = df["source_label"].value_counts().to_dict()

        avg_frp = float(df["frp"].mean()) if "frp" in df.columns else 0.0
        max_frp = float(df["frp"].max()) if "frp" in df.columns else 0.0
        persistent = int((df["active_days_last_7"] >= 4).sum()) \
            if "active_days_last_7" in df.columns else 0
        high_frp = int((df["frp"] >= 50).sum()) if "frp" in df.columns else 0
        # BUG-B06: add moderate bucket (15-49 MW) for accurate summary tiers
        moderate_frp = int(((df["frp"] >= 15) & (df["frp"] < 50)).sum()) if "frp" in df.columns else 0

        return {
            "total_events": len(df),
            "source_distribution": source_dist,
            "avg_frp": round(avg_frp, 2),
            "max_frp": round(max_frp, 2),
            "persistent_events": persistent,
            "high_frp_events": high_frp,
            "moderate_frp_events": moderate_frp,  # BUG-B06: new field
            "observation_window": (
                f"{self._obs_window.get('obs_start', '?')} to "
                f"{self._obs_window.get('obs_end', '?')} "
                f"({self._obs_window.get('obs_days', '?')} days)"
            ),
        }

    def obs_window(self) -> dict:
        return self._obs_window

    def add_event(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Additive SSE Support: Register a newly processed event into the in-memory store.
        Allows live/simulated events to be queried via REST APIs and reflected in summaries.
        """
        self._assert_loaded()
        event_id = event_dict.get("event_id") or event_dict.get("id") or f"TH{len(self._df):05d}"
        event_dict["event_id"] = event_id
        event_dict["event_idx"] = len(self._df)

        frp_val = _safe_float(event_dict.get("frp"), 0.0)
        days = int(event_dict.get("active_days_last_7") or 0)
        if "_risk_score" not in event_dict:
            thermal = min(100.0, (frp_val / 60.0) * 100.0)
            persistence = min(100.0, (days / 4.0) * 100.0)
            event_dict["_risk_score"] = round(0.30 * thermal + 0.30 * persistence + 19.0, 2)
        if "_risk_tier" not in event_dict:
            event_dict["_risk_tier"] = "HIGH" if event_dict["_risk_score"] >= 70.0 else ("MEDIUM" if event_dict["_risk_score"] >= 45.0 else "LOW")

        new_row_df = pd.DataFrame([event_dict])
        self._df = pd.concat([self._df, new_row_df], ignore_index=True)
        logger.info("EventService: added new event %s (total events: %d)", event_id, len(self._df))
        return event_dict

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _row_to_list_item(self, row: pd.Series) -> Dict[str, Any]:
        """Convert a dataset row to the lightweight list-item format."""
        sat_raw = row.get("satellite", None)

        day_night_val = row.get("day_night", None)
        if day_night_val is not None:
            try:
                dn_int = int(day_night_val)
                day_night_str = "D" if dn_int == 1 else "N"
            except (ValueError, TypeError):
                day_night_str = str(day_night_val) if day_night_val else None
        else:
            day_night_str = None

        frp_val = _safe_float(row.get("frp"), 0.0)
        # BUG-B01: use pre-computed tier and proxy risk_score
        risk_tier = row.get("_risk_tier", "LOW")
        proxy_score = _safe_float(row.get("_risk_score"), 0.0)
        days = int(row.get("active_days_last_7", 0) or 0)

        lat = _safe_float(row.get("latitude"))
        lon = _safe_float(row.get("longitude"))
        source_label = row.get("source_label")
        fac_info = resolve_facility_name(lat, lon, source_label)

        return {
            "id": row.get("event_id"),
            "location": {
                "lat": lat,
                "lon": lon,
            },
            "frp": frp_val,
            "acq_date": str(row.get("acq_date")) if row.get("acq_date") else None,
            "source_label": source_label,
            "active_days_last_7": days,
            "satellite": str(sat_raw) if sat_raw else None,
            "day_night": day_night_str,
            "risk_tier": risk_tier,    # BUG-B01: pre-computed, no ML needed
            "risk_score": proxy_score, # BUG-B01: proxy score for list view
            "candidate_source": fac_info["name"],
            "candidate_type": fac_info["type"],
        }

    def _assert_loaded(self) -> None:
        if self._df is None:
            raise RuntimeError("EventService.load() must be called at startup.")


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning default for None/NaN."""
    if val is None:
        return default
    try:
        f = float(val)
        return default if np.isnan(f) else f
    except (ValueError, TypeError):
        return default


# Module-level singleton
event_service = EventService()
