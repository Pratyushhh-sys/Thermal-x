"""
scripts/download_firms_data.py
================================
FIRMS VIIRS Data Download Script

Downloads historical/NRT active-fire data from NASA FIRMS and saves:
  data/raw/firms_viirs_raw.csv       -- original, unmodified FIRMS output
  data/raw/obs_window.json           -- actual observation window metadata
  data/processed/firms_viirs_clean.csv -- cleaned, normalized version

Data acquisition priority:
  1. NASA FIRMS MAP_KEY API (date-range historical or NRT)
  2. Locally supplied officially downloaded FIRMS CSV (set FIRMS_LOCAL_FILE)
  3. RuntimeError -- data is NEVER fabricated

Configuration (set in .env):
  FIRMS_MAP_KEY       -- get free at https://firms.modaps.eosdis.nasa.gov/api/
  FIRMS_LOCAL_FILE    -- path to manually downloaded CSV (fallback)
  FIRMS_BBOX          -- bounding box W,S,E,N (default: India 67,6,98,37)
  FIRMS_DAYS          -- NRT days, max 5 (default: 5)
  FIRMS_HISTORY_DAYS  -- historical window in days (default: 0 = use NRT)
  FIRMS_DATASET       -- dataset name (default: ALL_VIIRS_NRT)

Usage:
  # NRT last 5 days
  python scripts/download_firms_data.py

  # 30-day historical window (recommended for 7-day persistence features)
  python scripts/download_firms_data.py --history-days 30

  # Custom bbox
  python scripts/download_firms_data.py --history-days 30 --bbox 67,6,98,37

  # Use local file
  python scripts/download_firms_data.py --local-file /path/to/firms.csv
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.data_collection.firms_client import FIRMSClient, INDIA_BBOX
from ml.preprocessing.clean_data import run_cleaning

load_dotenv()
logger = logging.getLogger(__name__)

RAW_DIR       = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
RAW_CSV       = RAW_DIR / "firms_viirs_raw.csv"
CLEAN_CSV     = PROCESSED_DIR / "firms_viirs_clean.csv"


def download_and_prepare(
    bbox: str = None,
    days: int = None,
    history_days: int = None,
    dataset: str = None,
    local_file: str = None,
    map_key: str = None,
    skip_cleaning: bool = False,
) -> None:
    """
    Download FIRMS data and run initial cleaning.

    Parameters
    ----------
    bbox : str          FIRMS bbox W,S,E,N.
    days : int          NRT lookback days (max 5). Used when history_days not set.
    history_days : int  Total historical window in days (e.g. 30). Uses date-range API.
                        When set, overrides --days.
    dataset : str       FIRMS dataset name.
    local_file : str    Path to local FIRMS CSV (skips API).
    map_key : str       FIRMS MAP_KEY.
    skip_cleaning : bool  Skip preprocessing step.
    """
    bbox     = bbox    or os.getenv("FIRMS_BBOX", INDIA_BBOX)
    dataset  = dataset or os.getenv("FIRMS_DATASET", "ALL_VIIRS_NRT")
    h_days   = history_days or int(os.getenv("FIRMS_HISTORY_DAYS", "0"))
    nrt_days = days or int(os.getenv("FIRMS_DAYS", "5"))
    use_history = h_days > 5

    print("\n" + "=" * 60)
    print("  FIRMS DATA ACQUISITION")
    print("=" * 60)
    print(f"  Bounding box : {bbox}")
    print(f"  Dataset      : {dataset}")
    if use_history:
        print(f"  Mode         : Historical ({h_days}-day window via date-range API)")
        print(f"  NOTE: Stitching {(h_days // 5) + (1 if h_days % 5 else 0)} x 5-day windows")
    else:
        print(f"  Mode         : NRT last {nrt_days} days (max 5)")
    if local_file:
        print(f"  Local file   : {local_file}")
    print("=" * 60 + "\n")

    client = FIRMSClient(map_key=map_key, local_file_path=local_file)

    if use_history:
        df = client.fetch_date_range(area=bbox, total_days=h_days, dataset=dataset)
    else:
        df = client.fetch(area=bbox, days=nrt_days, dataset=dataset)

    # Save observation window metadata
    obs_meta = {
        "obs_start":  df.attrs.get("obs_start", "unknown"),
        "obs_end":    df.attrs.get("obs_end",   "unknown"),
        "obs_days":   df.attrs.get("obs_days",  h_days if use_history else nrt_days),
        "mode":       "historical" if use_history else "nrt",
        "total_rows": len(df),
        "note": (
            "Actual observation window. Persistence features require >=7 days."
            if not use_history
            else "Historical window fetched via FIRMS date-range API."
        ),
    }

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_CSV, index=False)
    with open(RAW_DIR / "obs_window.json", "w") as f:
        json.dump(obs_meta, f, indent=2)

    logger.info("Raw data saved: %s (%d rows x %d cols)", RAW_CSV, len(df), len(df.columns))

    print(f"Observation window : {obs_meta['obs_start']} to {obs_meta['obs_end']}"
          f"  ({obs_meta['obs_days']} days)")
    print(f"Raw data saved     : {RAW_CSV}  ({len(df):,} rows)")
    print(f"Columns            : {list(df.columns)}\n")

    if not skip_cleaning:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df_clean = run_cleaning(
            raw_path=str(RAW_CSV),
            output_path=str(CLEAN_CSV),
        )
        print(f"Clean data saved   : {CLEAN_CSV}  ({len(df_clean):,} rows)")

    print("\n  Next step:")
    print("    python ml/feature_engineering/build_features.py\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Download NASA FIRMS VIIRS data and run initial cleaning."
    )
    parser.add_argument("--bbox", default=None,
                        help="Bounding box W,S,E,N (default: India 67,6,98,37)")
    parser.add_argument("--days", type=int, default=None,
                        help="NRT lookback days, max 5 (default: 5 or FIRMS_DAYS env)")
    parser.add_argument("--history-days", type=int, default=None,
                        help="Historical window in days (e.g. 30). Overrides --days. "
                             "Uses FIRMS date-range API stitched in 5-day windows.")
    parser.add_argument("--dataset", default=None,
                        help="FIRMS dataset (default: ALL_VIIRS_NRT)")
    parser.add_argument("--local-file", default=None,
                        help="Path to locally downloaded FIRMS CSV (skips API)")
    parser.add_argument("--map-key", default=None,
                        help="FIRMS MAP_KEY (overrides FIRMS_MAP_KEY env)")
    parser.add_argument("--skip-cleaning", action="store_true",
                        help="Only save raw data; skip preprocessing")

    args = parser.parse_args()

    download_and_prepare(
        bbox=args.bbox,
        days=args.days,
        history_days=args.history_days,
        dataset=args.dataset,
        local_file=args.local_file,
        map_key=args.map_key,
        skip_cleaning=args.skip_cleaning,
    )
