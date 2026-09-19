"""
ml/feature_engineering/build_features.py
==========================================
Full Feature Table Builder + Data Quality Checks

Orchestrates:
  1. Load cleaned FIRMS data
  2. Run OSM geospatial enrichment (with caching)
  3. Apply weak geographic labels
  4. Compute 7-day temporal persistence features
  5. (Optional) Add weather context features
  6. Assemble final feature table
  7. Run automated data quality checks
  8. Save:
       data/features/source_classification_features.csv
       data/features/dataset_summary.json

Run as:
  python ml/feature_engineering/build_features.py
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Allow running as a script from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.feature_engineering.osm_enrichment import enrich_with_osm
from ml.feature_engineering.label_events import assign_source_labels
from ml.feature_engineering.temporal_features import (
    compute_temporal_features,
    compute_temporal_features_fast,
)

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROCESSED_CSV = Path("data/processed/firms_viirs_clean.csv")
FEATURES_CSV = Path("data/features/source_classification_features.csv")
SUMMARY_JSON = Path("data/features/dataset_summary.json")

FIRMS_BBOX = os.getenv("FIRMS_BBOX", "67,6,98,37")
PERSISTENCE_RADIUS_KM = float(os.getenv("PERSISTENCE_RADIUS_KM", "1.0"))

# Threshold above which we use the fast chunked temporal algorithm
FAST_TEMPORAL_THRESHOLD = 30_000

# ---------------------------------------------------------------------------
# Final feature columns (canonical order)
# ---------------------------------------------------------------------------
EVENT_COLS = ["latitude", "longitude", "acq_date", "hour", "month", "day_night"]

THERMAL_COLS = ["frp", "brightness", "brightness_ti5", "brightness_diff",
                "confidence_numeric", "scan", "track"]

TEMPORAL_COLS = [
    "active_days_last_7", "persistence_ratio", "observation_count_last_7",
    "avg_frp", "max_frp", "min_frp", "frp_trend", "frp_std",
    "night_count", "day_count",
]

GEOSPATIAL_COLS = [
    "distance_to_industrial", "distance_to_factory", "distance_to_chemical",
    "distance_to_refinery", "distance_to_gas",
    "distance_to_mine", "distance_to_quarry", "distance_to_pipeline",
    "distance_to_forest", "distance_to_cropland",
]

LANDCOVER_COLS = [
    "near_industrial", "near_factory", "near_mine", "near_quarry",
    "near_forest", "near_cropland", "dominant_context",
]

WEATHER_COLS = ["wind_speed", "wind_direction", "temperature", "humidity"]

TARGET_COL = ["source_label"]

# ---------------------------------------------------------------------------
# Optional weather enrichment (modular — skipped if unavailable)
# ---------------------------------------------------------------------------
def enrich_with_weather(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optionally enrich events with historical weather context via Open-Meteo.
    Open-Meteo is free, requires no API key, and provides historical ERA5 data.

    This is a best-effort enrichment: if the API is unavailable or times out,
    weather columns are set to NaN and the pipeline continues.

    Reference: https://open-meteo.com/en/docs/historical-weather-api
    """
    try:
        import requests
        logger.info("Attempting weather enrichment via Open-Meteo…")

        # Batch by unique date to minimize API calls
        weather_records = {}
        unique_combos = df[["latitude", "longitude", "acq_date"]].drop_duplicates()
        logger.info("Fetching weather for %d unique (lat, lon, date) combinations…",
                    len(unique_combos))

        for _, row in unique_combos.head(200).iterrows():  # cap at 200 to avoid timeout
            key = (round(row["latitude"], 2), round(row["longitude"], 2), str(row["acq_date"]))
            if key in weather_records:
                continue

            date_str = str(row["acq_date"])[:10]
            url = (
                f"https://archive-api.open-meteo.com/v1/archive"
                f"?latitude={row['latitude']:.4f}&longitude={row['longitude']:.4f}"
                f"&start_date={date_str}&end_date={date_str}"
                f"&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,winddirection_10m"
                f"&timezone=UTC"
            )
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    hourly = data.get("hourly", {})
                    idx = 12  # use noon UTC as representative
                    weather_records[key] = {
                        "temperature": _safe_idx(hourly.get("temperature_2m"), idx),
                        "humidity": _safe_idx(hourly.get("relativehumidity_2m"), idx),
                        "wind_speed": _safe_idx(hourly.get("windspeed_10m"), idx),
                        "wind_direction": _safe_idx(hourly.get("winddirection_10m"), idx),
                    }
            except Exception:
                pass

        if weather_records:
            def _lookup(row):
                k = (round(row["latitude"], 2), round(row["longitude"], 2), str(row["acq_date"]))
                return pd.Series(weather_records.get(k, {
                    "temperature": np.nan, "humidity": np.nan,
                    "wind_speed": np.nan, "wind_direction": np.nan,
                }))

            weather_df = df.apply(_lookup, axis=1)
            df = pd.concat([df, weather_df], axis=1)
            n_filled = weather_df["temperature"].notna().sum()
            logger.info("Weather enrichment: filled %d / %d rows", n_filled, len(df))
        else:
            logger.warning("No weather data retrieved.")
            for col in WEATHER_COLS:
                df[col] = np.nan

    except Exception as exc:
        logger.warning("Weather enrichment skipped (non-blocking): %s", exc)
        for col in WEATHER_COLS:
            df[col] = np.nan

    return df


def _safe_idx(lst, idx):
    try:
        return lst[idx]
    except Exception:
        return np.nan


# ---------------------------------------------------------------------------
# Data Quality Checks
# ---------------------------------------------------------------------------
def run_quality_checks(df: pd.DataFrame) -> dict:
    """
    Run automated data quality checks and return a summary dict.

    Checks:
      - Row/column counts
      - Missing values per column
      - Duplicate rows
      - Class distribution
      - Invalid coordinate ranges
      - Invalid FRP values
      - Extreme outliers (IQR-based)
      - Feature correlations (top 10 correlated pairs)
    """
    logger.info("Running data quality checks…")

    summary = {}

    # Basic shape
    summary["n_rows"] = int(len(df))
    summary["n_columns"] = int(len(df.columns))

    # Missing values
    missing = df.isnull().sum()
    summary["missing_values"] = {
        col: {"count": int(v), "pct": round(100 * v / len(df), 2)}
        for col, v in missing.items() if v > 0
    }

    # Duplicate rows
    summary["duplicate_rows"] = int(df.duplicated().sum())

    # Class distribution
    if "source_label" in df.columns:
        dist = df["source_label"].value_counts()
        summary["class_distribution"] = {
            str(k): {"count": int(v), "pct": round(100 * v / len(df), 2)}
            for k, v in dist.items()
        }
        summary["n_classes"] = int(dist.nunique())

    # Coordinate validity
    if "latitude" in df.columns and "longitude" in df.columns:
        bad_lat = int(((df["latitude"] < -90) | (df["latitude"] > 90)).sum())
        bad_lon = int(((df["longitude"] < -180) | (df["longitude"] > 180)).sum())
        summary["invalid_coordinates"] = {"bad_lat": bad_lat, "bad_lon": bad_lon}

    # FRP validity
    if "frp" in df.columns:
        bad_frp = int(((df["frp"] <= 0) | (df["frp"] > 10000)).sum())
        summary["invalid_frp_count"] = bad_frp
        summary["frp_stats"] = {
            "min": float(df["frp"].min()),
            "max": float(df["frp"].max()),
            "mean": float(df["frp"].mean()),
            "median": float(df["frp"].median()),
            "p99": float(df["frp"].quantile(0.99)),
        }

    # Outlier detection (IQR-based on numeric features)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    outlier_summary = {}
    for col in numeric_cols[:20]:  # check first 20 numeric columns
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        n_outliers = int(((df[col] < q1 - 3 * iqr) | (df[col] > q3 + 3 * iqr)).sum())
        if n_outliers > 0:
            outlier_summary[col] = n_outliers
    summary["outlier_counts_iqr3"] = outlier_summary

    # Feature correlations
    try:
        numeric_df = df[numeric_cols].dropna(how="all")
        corr = numeric_df.corr().abs()
        # Get upper triangle
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        top_pairs = (
            upper.stack()
            .sort_values(ascending=False)
            .head(15)
        )
        summary["top_feature_correlations"] = [
            {"col_a": str(a), "col_b": str(b), "correlation": round(float(v), 4)}
            for (a, b), v in top_pairs.items()
        ]
    except Exception as exc:
        summary["top_feature_correlations"] = f"Error: {exc}"

    # Print QC report
    print("\n── Data Quality Report ─────────────────────────────────────────")
    print(f"  Rows         : {summary['n_rows']:,}")
    print(f"  Columns      : {summary['n_columns']}")
    print(f"  Duplicates   : {summary['duplicate_rows']}")
    if "class_distribution" in summary:
        print(f"  Classes      : {summary['n_classes']}")
        for cls, info in summary["class_distribution"].items():
            print(f"    {cls:20s}: {info['count']:6d} ({info['pct']:.1f}%)")
    if summary.get("missing_values"):
        print("  Missing values (top cols):")
        for col, info in list(summary["missing_values"].items())[:8]:
            print(f"    {col:30s}: {info['count']:6d} ({info['pct']:.1f}%)")
    print("────────────────────────────────────────────────────────────────\n")

    return summary


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------
def build_features(
    processed_path: str = str(PROCESSED_CSV),
    output_path: str = str(FEATURES_CSV),
    summary_path: str = str(SUMMARY_JSON),
    bbox: str = FIRMS_BBOX,
    radius_km: float = PERSISTENCE_RADIUS_KM,
    force_osm_refresh: bool = False,
    skip_weather: bool = False,
) -> pd.DataFrame:
    """
    Build the complete ML feature table from cleaned FIRMS data.

    Parameters
    ----------
    processed_path : str
        Path to cleaned FIRMS CSV.
    output_path : str
        Destination for feature CSV.
    summary_path : str
        Destination for quality summary JSON.
    bbox : str
        FIRMS-format bounding box: 'W,S,E,N'
    radius_km : float
        Spatial matching radius for temporal features (km).
    force_osm_refresh : bool
        Re-query Overpass even if cache exists.
    skip_weather : bool
        Skip weather enrichment entirely.

    Returns
    -------
    pd.DataFrame
        Final feature table.
    """
    processed_path = Path(processed_path)
    output_path = Path(output_path)
    summary_path = Path(summary_path)

    if not processed_path.exists():
        raise FileNotFoundError(
            f"Cleaned data not found: {processed_path}\n"
            "Run: python scripts/download_firms_data.py first."
        )

    # ── 1. Load cleaned data ──────────────────────────────────────────────
    logger.info("Loading cleaned FIRMS data from %s", processed_path)
    df = pd.read_csv(processed_path, low_memory=False)
    logger.info("Loaded %d rows", len(df))

    if "datetime_utc" in df.columns:
        df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], errors="coerce")

    # ── 2. OSM geospatial enrichment ──────────────────────────────────────
    logger.info("Step 2/5: OSM geospatial enrichment…")
    df = enrich_with_osm(df, bbox_firms=bbox, force_refresh=force_osm_refresh)

    # ── 3. Weak geographic labels ─────────────────────────────────────────
    logger.info("Step 3/5: Assigning weak geographic labels…")
    df = assign_source_labels(df)

    # ── 4. Temporal persistence features ─────────────────────────────────
    logger.info("Step 4/5: Computing temporal persistence features (radius=%.2f km)…", radius_km)
    if len(df) > FAST_TEMPORAL_THRESHOLD:
        logger.info("Large dataset (%d rows) — using fast chunked temporal algorithm.", len(df))
        df = compute_temporal_features_fast(df, radius_km=radius_km)
    else:
        df = compute_temporal_features(df, radius_km=radius_km)

    # ── 5. Optional weather enrichment ────────────────────────────────────
    if not skip_weather:
        logger.info("Step 5/5: Weather enrichment (best-effort, non-blocking)…")
        df = enrich_with_weather(df)
    else:
        logger.info("Step 5/5: Weather enrichment skipped.")
        for col in WEATHER_COLS:
            df[col] = np.nan

    # ── 6. Assemble final feature table ───────────────────────────────────
    logger.info("Assembling final feature table…")
    all_feature_cols = (
        EVENT_COLS + THERMAL_COLS + TEMPORAL_COLS +
        GEOSPATIAL_COLS + LANDCOVER_COLS + WEATHER_COLS + TARGET_COL
    )
    # Keep only columns that exist; fill missing with NaN
    final_cols = []
    for col in all_feature_cols:
        if col not in df.columns:
            df[col] = np.nan
        final_cols.append(col)

    # Also keep label_rationale for audit (but not as a training feature)
    if "label_rationale" in df.columns:
        final_cols.append("label_rationale")
    if "source_label_int" in df.columns:
        final_cols.append("source_label_int")

    feat_df = df[final_cols].copy()

    # ── 7. Save ───────────────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    feat_df.to_csv(output_path, index=False)
    logger.info("Feature table saved: %s (%d rows × %d cols)", output_path, len(feat_df), len(feat_df.columns))

    # ── 8. Quality checks ─────────────────────────────────────────────────
    summary = run_quality_checks(feat_df)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info("Dataset summary saved: %s", summary_path)

    return feat_df


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Build ML feature table from cleaned FIRMS data")
    parser.add_argument("--processed-path", default=str(PROCESSED_CSV))
    parser.add_argument("--output-path", default=str(FEATURES_CSV))
    parser.add_argument("--summary-path", default=str(SUMMARY_JSON))
    parser.add_argument("--bbox", default=FIRMS_BBOX)
    parser.add_argument("--radius-km", type=float, default=PERSISTENCE_RADIUS_KM,
                        help="Spatial matching radius for temporal features (km). Default: 1.0")
    parser.add_argument("--force-osm-refresh", action="store_true",
                        help="Re-query Overpass API even if cache exists")
    parser.add_argument("--skip-weather", action="store_true",
                        help="Skip weather enrichment (saves time)")

    args = parser.parse_args()

    build_features(
        processed_path=args.processed_path,
        output_path=args.output_path,
        summary_path=args.summary_path,
        bbox=args.bbox,
        radius_km=args.radius_km,
        force_osm_refresh=args.force_osm_refresh,
        skip_weather=args.skip_weather,
    )
