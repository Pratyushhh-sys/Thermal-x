"""
ml/preprocessing/clean_data.py
================================
FIRMS VIIRS Raw Data Cleaning & Normalization

Steps performed:
  1. Standardize column names to lowercase
  2. Drop rows with missing latitude, longitude, or FRP
  3. Filter out physically impossible values (coords, FRP, brightness)
  4. Decode and validate VIIRS confidence flag
  5. Parse and normalize timestamps to UTC
  6. Extract temporal fields: hour, month, day_of_week
  7. Deduplicate on (lat, lon, acq_date, acq_time, satellite)
  8. Report cleaning summary statistics

Output: data/processed/firms_viirs_clean.csv
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Physical validity bounds
# ---------------------------------------------------------------------------
LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0

# VIIRS FRP valid range (MW). Values ≥10,000 MW are almost certainly artefacts.
FRP_MIN = 0.0          # strictly positive fire radiative power
FRP_MAX = 10_000.0     # upper physical plausibility limit

# VIIRS brightness temperature (Kelvin)
# Band I4 (~3.7 µm) valid range
BRIGHT_MIN = 200.0
BRIGHT_MAX = 500.0

# VIIRS confidence values (text-coded in NRT products)
VALID_CONFIDENCE_TEXT = {"l", "n", "h"}           # low, nominal, high
CONFIDENCE_ENCODE = {"l": 0, "n": 1, "h": 2}      # ordinal encoding

# Some archive products use numeric confidence (0–100)
CONFIDENCE_NUMERIC_MIN = 0
CONFIDENCE_NUMERIC_MAX = 100


# ---------------------------------------------------------------------------
# Main cleaning function
# ---------------------------------------------------------------------------
def clean_firms_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Clean and normalize raw FIRMS VIIRS data.

    Parameters
    ----------
    df : pd.DataFrame
        Raw data from FIRMSClient (any VIIRS variant).

    Returns
    -------
    clean_df : pd.DataFrame
        Cleaned, normalized DataFrame.
    report : dict
        Summary statistics documenting how many rows were dropped and why.
    """
    report: dict = {"initial_rows": len(df)}

    # ── 1. Standardize column names ──────────────────────────────────────
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # Map alternative column names that appear in some FIRMS products
    column_aliases = {
        "bright_ti4": "brightness",      # VIIRS I4 band
        "bright_t31": "brightness",      # MODIS (if mixed input)
        "brightness": "brightness",
        "bright_ti5": "brightness_ti5",
    }
    for old, new in column_aliases.items():
        if old in df.columns and new not in df.columns:
            df.rename(columns={old: new}, inplace=True)

    # ── 2. Drop rows with missing critical fields ─────────────────────────
    critical = ["latitude", "longitude", "frp", "acq_date"]
    before = len(df)
    df.dropna(subset=critical, inplace=True)
    report["dropped_missing_critical"] = before - len(df)

    # ── 3. Filter invalid coordinates ────────────────────────────────────
    before = len(df)
    valid_coords = (
        df["latitude"].between(LAT_MIN, LAT_MAX, inclusive="both")
        & df["longitude"].between(LON_MIN, LON_MAX, inclusive="both")
    )
    df = df[valid_coords].copy()
    report["dropped_invalid_coords"] = before - len(df)

    # ── 4. Filter invalid FRP ─────────────────────────────────────────────
    before = len(df)
    df["frp"] = pd.to_numeric(df["frp"], errors="coerce")
    valid_frp = df["frp"].between(FRP_MIN, FRP_MAX, inclusive="neither")
    df = df[valid_frp].copy()
    report["dropped_invalid_frp"] = before - len(df)

    # ── 5. Handle confidence ──────────────────────────────────────────────
    if "confidence" in df.columns:
        conf = df["confidence"].astype(str).str.strip().str.lower()

        # Text confidence (NRT products: l/n/h)
        if conf.isin(VALID_CONFIDENCE_TEXT | {str(v) for v in CONFIDENCE_ENCODE.values()}).any():
            df["confidence_raw"] = conf
            df["confidence_numeric"] = conf.map(CONFIDENCE_ENCODE)
            # If already numeric strings, try direct coercion
            mask_na = df["confidence_numeric"].isna()
            if mask_na.any():
                df.loc[mask_na, "confidence_numeric"] = pd.to_numeric(
                    conf[mask_na], errors="coerce"
                ).clip(0, 100) / 33.0  # scale 0-100 → 0-3

        else:
            # Numeric confidence (archive: 0-100)
            df["confidence_numeric"] = pd.to_numeric(conf, errors="coerce").clip(0, 100)
            df["confidence_raw"] = conf
    else:
        logger.warning("'confidence' column not found; setting confidence_numeric = NaN")
        df["confidence_numeric"] = np.nan
        df["confidence_raw"] = "unknown"

    # ── 6. Brightness temperature ─────────────────────────────────────────
    if "brightness" in df.columns:
        df["brightness"] = pd.to_numeric(df["brightness"], errors="coerce")
        # Clip to plausible range; do not drop — some sensors vary
        df["brightness"] = df["brightness"].clip(BRIGHT_MIN, BRIGHT_MAX)
    else:
        df["brightness"] = np.nan
        logger.warning("Brightness temperature column not found.")

    if "brightness_ti5" in df.columns:
        df["brightness_ti5"] = pd.to_numeric(df["brightness_ti5"], errors="coerce")
        df["brightness_ti5"] = df["brightness_ti5"].clip(BRIGHT_MIN, BRIGHT_MAX)
        df["brightness_diff"] = df["brightness"] - df["brightness_ti5"]
    else:
        df["brightness_ti5"] = np.nan
        df["brightness_diff"] = np.nan

    # ── 7. Scan and track ─────────────────────────────────────────────────
    for col in ["scan", "track"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    # ── 8. Day/Night ──────────────────────────────────────────────────────
    if "daynight" in df.columns:
        df["day_night"] = df["daynight"].astype(str).str.strip().str.upper().map(
            {"D": 1, "N": 0}
        )
    else:
        df["day_night"] = np.nan

    # ── 9. Satellite ──────────────────────────────────────────────────────
    if "satellite" in df.columns:
        df["satellite"] = df["satellite"].astype(str).str.strip()
    else:
        df["satellite"] = "Unknown"

    # ── 10. Timestamp parsing ─────────────────────────────────────────────
    df = _parse_timestamps(df)

    # ── 11. Deduplicate ───────────────────────────────────────────────────
    before = len(df)
    dedup_cols = [c for c in ["latitude", "longitude", "acq_date", "acq_time", "satellite"] if c in df.columns]
    df.drop_duplicates(subset=dedup_cols, keep="first", inplace=True)
    report["dropped_duplicates"] = before - len(df)

    # ── 12. Reset index ───────────────────────────────────────────────────
    df.reset_index(drop=True, inplace=True)
    report["final_rows"] = len(df)
    report["total_dropped"] = report["initial_rows"] - report["final_rows"]

    logger.info(
        "Cleaning complete: %d → %d rows (dropped %d, %.1f%%)",
        report["initial_rows"],
        report["final_rows"],
        report["total_dropped"],
        100.0 * report["total_dropped"] / max(report["initial_rows"], 1),
    )

    return df, report


# ---------------------------------------------------------------------------
# Timestamp utilities
# ---------------------------------------------------------------------------
def _parse_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse acq_date + acq_time into a UTC datetime and extract temporal features.

    FIRMS acq_time format: HHMM (integer or zero-padded string).
    """
    df = df.copy()

    if "acq_time" in df.columns:
        # Zero-pad to 4 digits
        acq_time_str = df["acq_time"].astype(str).str.zfill(4)
        time_str = acq_time_str.str[:2] + ":" + acq_time_str.str[2:]
    else:
        time_str = "00:00"

    combined = df["acq_date"].astype(str).str.strip() + " " + time_str

    df["datetime_utc"] = pd.to_datetime(combined, format="%Y-%m-%d %H:%M", errors="coerce")

    # Drop rows where timestamp could not be parsed (indicates corrupt data)
    n_bad = df["datetime_utc"].isna().sum()
    if n_bad > 0:
        logger.warning("Dropped %d rows with unparseable timestamps.", n_bad)
        df = df.dropna(subset=["datetime_utc"]).copy()

    # Extract temporal features
    df["hour"] = df["datetime_utc"].dt.hour
    df["month"] = df["datetime_utc"].dt.month
    df["day_of_week"] = df["datetime_utc"].dt.dayofweek  # 0=Mon

    return df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_cleaning(
    raw_path: str = "data/raw/firms_viirs_raw.csv",
    output_path: str = "data/processed/firms_viirs_clean.csv",
) -> pd.DataFrame:
    """
    Load raw FIRMS data, clean it, and save to output_path.

    Parameters
    ----------
    raw_path : str
        Path to raw FIRMS CSV.
    output_path : str
        Destination path for cleaned CSV.

    Returns
    -------
    pd.DataFrame
        Cleaned dataset.
    """
    raw_path = Path(raw_path)
    output_path = Path(output_path)

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {raw_path.resolve()}")

    logger.info("Loading raw data from %s", raw_path)
    df_raw = pd.read_csv(raw_path, low_memory=False)

    df_clean, report = clean_firms_data(df_raw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(output_path, index=False)
    logger.info("Clean data saved to %s (%d rows)", output_path, len(df_clean))

    # Print cleaning summary
    print("\n── Cleaning Report ──────────────────────────────────────")
    for key, val in report.items():
        print(f"  {key:35s}: {val}")
    print("─────────────────────────────────────────────────────────\n")

    return df_clean


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_cleaning()
