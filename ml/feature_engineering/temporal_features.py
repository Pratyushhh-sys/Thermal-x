"""
ml/feature_engineering/temporal_features.py
=============================================
7-Day Temporal Persistence Feature Engineering

For each FIRMS thermal event this module calculates lookback features
over the previous 7 days using spatially-matched observations.

Spatial matching strategy:
  - Uses Haversine distance to find events within a configurable radius.
  - Default radius: 1.0 km (configurable via PERSISTENCE_RADIUS_KM env var
    or the `radius_km` parameter).
  - Uses a BallTree index for efficient spatial queries at scale.
  - Does NOT require exact lat/lon match — captures the same physical
    fire site seen from slightly different satellite positions.

Features generated:
  - active_days_last_7       : distinct dates with a detection within radius
  - persistence_ratio        : active_days_last_7 / 7
  - observation_count_last_7 : total observation count within radius & window
  - avg_frp                  : mean FRP of nearby events in window
  - max_frp                  : maximum FRP
  - min_frp                  : minimum FRP
  - frp_trend                : linear slope of FRP over time (MW/day)
  - night_count              : nighttime detections in window
  - day_count                : daytime detections in window
  - frp_std                  : std dev of FRP (variability indicator)

Performance note:
  - Naive O(N²) is acceptable for <100,000 events.
  - For larger datasets this module uses a chunked date-window approach
    with BallTree per day-group to stay manageable.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.stats import linregress
from sklearn.neighbors import BallTree
from tqdm import tqdm

load_dotenv()
logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0
DEFAULT_RADIUS_KM = float(os.getenv("PERSISTENCE_RADIUS_KM", "1.0"))
LOOKBACK_DAYS = 7


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------
def compute_temporal_features(
    df: pd.DataFrame,
    radius_km: float = DEFAULT_RADIUS_KM,
    lookback_days: int = LOOKBACK_DAYS,
) -> pd.DataFrame:
    """
    Compute 7-day temporal persistence features for every event in `df`.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned FIRMS data. Must have columns:
        'latitude', 'longitude', 'datetime_utc', 'frp', 'day_night'.
    radius_km : float
        Spatial matching radius in km. Default: 1.0 km.
        Change via PERSISTENCE_RADIUS_KM env var or this parameter.
    lookback_days : int
        Window size in days. Default: 7.

    Returns
    -------
    pd.DataFrame
        Input DataFrame with temporal feature columns appended.
    """
    logger.info(
        "Computing temporal features: %d events, radius=%.2f km, window=%d days",
        len(df), radius_km, lookback_days,
    )

    if "datetime_utc" not in df.columns:
        raise ValueError("DataFrame must have a 'datetime_utc' column (UTC datetime).")

    df = df.copy().sort_values("datetime_utc").reset_index(drop=True)

    # Pre-allocate output arrays
    n = len(df)
    active_days = np.zeros(n, dtype=np.int32)
    persistence_ratio = np.zeros(n, dtype=np.float32)
    obs_count = np.zeros(n, dtype=np.int32)
    avg_frp = np.full(n, np.nan, dtype=np.float32)
    max_frp = np.full(n, np.nan, dtype=np.float32)
    min_frp = np.full(n, np.nan, dtype=np.float32)
    frp_trend = np.zeros(n, dtype=np.float32)
    frp_std = np.zeros(n, dtype=np.float32)
    night_count = np.zeros(n, dtype=np.int32)
    day_count = np.zeros(n, dtype=np.int32)

    lats = df["latitude"].values
    lons = df["longitude"].values
    datetimes = df["datetime_utc"].values
    frps = df["frp"].values

    # day_night: 1=day, 0=night, NaN=unknown
    if "day_night" in df.columns:
        day_nights = df["day_night"].values
    else:
        day_nights = np.full(n, np.nan)

    # Convert radius to radians for BallTree
    radius_rad = radius_km / EARTH_RADIUS_KM

    # Group events by calendar date for efficient windowing
    df["_date"] = pd.to_datetime(datetimes).normalize()
    unique_dates = sorted(df["_date"].unique())
    date_to_idx = {d: np.where(df["_date"].values == d)[0] for d in unique_dates}

    logger.info(
        "Date range: %s → %s (%d unique dates)",
        unique_dates[0], unique_dates[-1], len(unique_dates),
    )

    # All event coords in radians (for BallTree queries)
    all_coords_rad = np.radians(np.column_stack([lats, lons]))

    for i in tqdm(range(n), desc=f"Temporal features (r={radius_km:.1f}km)", unit="event"):
        t_event = pd.Timestamp(datetimes[i])
        t_start = t_event - pd.Timedelta(days=lookback_days)

        # Find candidate indices in the lookback window (date-based filter)
        candidate_idxs = []
        for d in unique_dates:
            if t_start <= pd.Timestamp(d) < t_event:
                candidate_idxs.extend(date_to_idx[d].tolist())

        if not candidate_idxs:
            # No historical observations — all features stay at zero/NaN
            active_days[i] = 0
            persistence_ratio[i] = 0.0
            obs_count[i] = 0
            continue

        candidate_idxs = np.array(candidate_idxs)
        cand_coords_rad = all_coords_rad[candidate_idxs]

        # BallTree nearest-neighbor within radius
        query_point = all_coords_rad[i:i+1]
        tree = BallTree(cand_coords_rad, metric="haversine")
        neighbor_idxs_local = tree.query_radius(query_point, r=radius_rad)[0]

        if len(neighbor_idxs_local) == 0:
            active_days[i] = 0
            persistence_ratio[i] = 0.0
            obs_count[i] = 0
            continue

        # Map back to global indices
        matched = candidate_idxs[neighbor_idxs_local]

        # Compute features from matched events
        matched_frp = frps[matched]
        matched_dates = pd.to_datetime(datetimes[matched]).normalize()
        matched_dn = day_nights[matched]

        active_days[i] = matched_dates.nunique()
        persistence_ratio[i] = active_days[i] / lookback_days
        obs_count[i] = len(matched)

        avg_frp[i] = float(np.nanmean(matched_frp))
        max_frp[i] = float(np.nanmax(matched_frp))
        min_frp[i] = float(np.nanmin(matched_frp))
        frp_std[i] = float(np.nanstd(matched_frp)) if len(matched_frp) > 1 else 0.0

        # FRP trend: linear slope over matched timestamps (MW/day)
        if len(matched) >= 3:
            days_ago = np.array([
                (t_event - pd.Timestamp(datetimes[m])).total_seconds() / 86400.0
                for m in matched
            ])
            try:
                slope, _, _, _, _ = linregress(days_ago, matched_frp)
                frp_trend[i] = float(-slope)  # negative days_ago → positive trend = increasing
            except Exception:
                frp_trend[i] = 0.0
        else:
            frp_trend[i] = 0.0

        # Day/night counts
        valid_dn = matched_dn[~np.isnan(matched_dn)]
        night_count[i] = int(np.sum(valid_dn == 0))
        day_count[i] = int(np.sum(valid_dn == 1))

    # Attach to DataFrame
    df["active_days_last_7"] = active_days
    df["persistence_ratio"] = persistence_ratio
    df["observation_count_last_7"] = obs_count
    df["avg_frp"] = avg_frp
    df["max_frp"] = max_frp
    df["min_frp"] = min_frp
    df["frp_trend"] = frp_trend
    df["frp_std"] = frp_std
    df["night_count"] = night_count
    df["day_count"] = day_count

    df.drop(columns=["_date"], inplace=True, errors="ignore")

    logger.info("Temporal feature computation complete.")
    return df


# ---------------------------------------------------------------------------
# Vectorised fast-path for large datasets (>50k events)
# ---------------------------------------------------------------------------
def compute_temporal_features_fast(
    df: pd.DataFrame,
    radius_km: float = DEFAULT_RADIUS_KM,
    lookback_days: int = LOOKBACK_DAYS,
    chunk_size_days: int = 1,
) -> pd.DataFrame:
    """
    Memory-efficient chunked version for datasets > 50,000 events.

    Processes one day at a time, building a rolling spatial index.
    Significantly faster than the event-by-event version for large datasets.

    Parameters
    ----------
    df : pd.DataFrame
        As per compute_temporal_features().
    radius_km : float
        Spatial matching radius in km.
    lookback_days : int
        Window size (days).
    chunk_size_days : int
        Days to process per chunk (default: 1).

    Returns
    -------
    pd.DataFrame with temporal features appended.
    """
    logger.info(
        "Fast temporal features: %d events, radius=%.2f km, window=%d days",
        len(df), radius_km, lookback_days,
    )

    df = df.copy().sort_values("datetime_utc").reset_index(drop=True)
    df["_date"] = pd.to_datetime(df["datetime_utc"]).dt.normalize()

    unique_dates = sorted(df["_date"].unique())

    results = []
    for i, current_date in enumerate(tqdm(unique_dates, desc="Daily chunks")):
        # Events on this day (current targets)
        mask_today = df["_date"] == current_date
        today_df = df[mask_today].copy()

        # Historical window
        window_start = current_date - pd.Timedelta(days=lookback_days)
        mask_hist = (df["_date"] >= window_start) & (df["_date"] < current_date)
        hist_df = df[mask_hist]

        if len(hist_df) == 0:
            today_df = _assign_zero_temporal_features(today_df)
            results.append(today_df)
            continue

        # Build spatial index on historical data
        hist_coords_rad = np.radians(hist_df[["latitude", "longitude"]].values)
        hist_tree = BallTree(hist_coords_rad, metric="haversine")

        radius_rad = radius_km / EARTH_RADIUS_KM
        today_coords_rad = np.radians(today_df[["latitude", "longitude"]].values)

        # Query all today's events at once
        neighbor_lists = hist_tree.query_radius(today_coords_rad, r=radius_rad)

        today_records = []
        for j, neighbors in enumerate(neighbor_lists):
            row_feats = _compute_row_features(
                hist_df.iloc[neighbors] if len(neighbors) > 0 else hist_df.iloc[:0],
                lookback_days=lookback_days,
            )
            today_records.append(row_feats)

        feat_df = pd.DataFrame(today_records, index=today_df.index)
        today_df = pd.concat([today_df, feat_df], axis=1)
        results.append(today_df)

    result = pd.concat(results, ignore_index=True)
    result.drop(columns=["_date"], inplace=True, errors="ignore")
    return result


def _compute_row_features(hist: pd.DataFrame, lookback_days: int) -> dict:
    """Compute temporal features for one event from its matched historical rows."""
    if len(hist) == 0:
        return {
            "active_days_last_7": 0, "persistence_ratio": 0.0,
            "observation_count_last_7": 0, "avg_frp": np.nan,
            "max_frp": np.nan, "min_frp": np.nan, "frp_trend": 0.0,
            "frp_std": 0.0, "night_count": 0, "day_count": 0,
        }

    frps = hist["frp"].values
    feats = {
        "active_days_last_7": int(hist["_date"].nunique()) if "_date" in hist.columns else 0,
        "observation_count_last_7": len(hist),
        "avg_frp": float(np.nanmean(frps)),
        "max_frp": float(np.nanmax(frps)),
        "min_frp": float(np.nanmin(frps)),
        "frp_std": float(np.nanstd(frps)) if len(frps) > 1 else 0.0,
    }
    feats["persistence_ratio"] = feats["active_days_last_7"] / lookback_days

    # FRP trend
    if len(hist) >= 3 and "datetime_utc" in hist.columns:
        try:
            times = pd.to_datetime(hist["datetime_utc"])
            days = (times.max() - times).dt.total_seconds().values / 86400.0
            slope, *_ = linregress(days, frps)
            feats["frp_trend"] = float(-slope)
        except Exception:
            feats["frp_trend"] = 0.0
    else:
        feats["frp_trend"] = 0.0

    if "day_night" in hist.columns:
        dn = hist["day_night"].dropna().values
        feats["night_count"] = int(np.sum(dn == 0))
        feats["day_count"] = int(np.sum(dn == 1))
    else:
        feats["night_count"] = 0
        feats["day_count"] = 0

    return feats


def _assign_zero_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["active_days_last_7"] = 0
    df["persistence_ratio"] = 0.0
    df["observation_count_last_7"] = 0
    df["avg_frp"] = np.nan
    df["max_frp"] = np.nan
    df["min_frp"] = np.nan
    df["frp_trend"] = 0.0
    df["frp_std"] = 0.0
    df["night_count"] = 0
    df["day_count"] = 0
    return df
