import os, sys
os.environ.setdefault("PYTHONUTF8", "1")
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
"""
scripts/run_ml_pipeline.py
============================
Complete ML Pipeline Orchestrator — SIH 2026 PS 26162

Executes the full Day-1 pipeline end-to-end:

  Stage 1 — Data acquisition      (FIRMS API or local file)
  Stage 2 — Data cleaning          (normalize, deduplicate, validate)
  Stage 3 — OSM geospatial enrichment (Overpass, cached)
  Stage 4 — Weak label assignment  (geographic proximity labels)
  Stage 5 — Temporal persistence   (7-day Haversine spatial matching)
  Stage 6 — Feature assembly       (canonical feature table + QC)
  Stage 7 — Model training         (XGBoost, spatial split, 2 experiments)
  Stage 8 — Evaluation             (metrics, confusion matrix, SHAP)
  Stage 9 — Artifact saving        (model, encoder, metadata, leakage report)

Each stage is independent and can also be run separately:
  python scripts/download_firms_data.py
  python ml/feature_engineering/build_features.py
  python ml/training/train_model.py

Usage:
  python scripts/run_ml_pipeline.py
  python scripts/run_ml_pipeline.py --skip-download   (if data already exists)
  python scripts/run_ml_pipeline.py --skip-features   (if features already built)
  python scripts/run_ml_pipeline.py --force-osm-refresh
  python scripts/run_ml_pipeline.py --skip-weather
  python scripts/run_ml_pipeline.py --radius-km 2.0   (change persistence radius)

Environment variables (set in .env):
  FIRMS_MAP_KEY, FIRMS_LOCAL_FILE, FIRMS_BBOX, FIRMS_DAYS
  PERSISTENCE_RADIUS_KM, SPATIAL_SPLIT_LAT, RANDOM_SEED
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Allow import from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------

def stage_banner(n: int, name: str) -> None:
    print(f"\n{'═'*60}")
    print(f"  STAGE {n}: {name}")
    print(f"{'═'*60}")


def run_stage_1_download(args) -> bool:
    """Download FIRMS data and clean it."""
    stage_banner(1, "DATA ACQUISITION (FIRMS)")

    from scripts.download_firms_data import download_and_prepare

    try:
        download_and_prepare(
            bbox=args.bbox or os.getenv("FIRMS_BBOX"),
            days=args.days,
            dataset=args.dataset,
            local_file=args.local_file,
            skip_cleaning=False,
        )
        return True
    except RuntimeError as exc:
        print(f"\n  ❌ STAGE 1 BLOCKED: {exc}")
        print("  Cannot continue pipeline without real data.")
        return False
    except Exception as exc:
        logger.error("Stage 1 failed: %s", exc, exc_info=True)
        return False


def run_stage_2_features(args) -> bool:
    """Build full feature table."""
    stage_banner(2, "FEATURE ENGINEERING (OSM + TEMPORAL + LABELS)")

    from ml.feature_engineering.build_features import build_features

    try:
        build_features(
            radius_km=args.radius_km,
            force_osm_refresh=args.force_osm_refresh,
            skip_weather=args.skip_weather,
        )
        return True
    except FileNotFoundError as exc:
        print(f"\n  ❌ STAGE 2 BLOCKED: {exc}")
        return False
    except Exception as exc:
        logger.error("Stage 2 failed: %s", exc, exc_info=True)
        return False


def run_stage_3_training(args) -> bool:
    """Train, evaluate, and save the model."""
    stage_banner(3, "MODEL TRAINING & EVALUATION (XGBoost)")

    from ml.training.train_model import run_training

    try:
        run_training(split_lat=args.split_lat)
        return True
    except FileNotFoundError as exc:
        print(f"\n  ❌ STAGE 3 BLOCKED: {exc}")
        return False
    except ValueError as exc:
        print(f"\n  ❌ STAGE 3 DATA ERROR: {exc}")
        return False
    except Exception as exc:
        logger.error("Stage 3 failed: %s", exc, exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
def run_pipeline(args) -> None:
    start_time = time.time()

    print("\n" + "╔" + "═"*58 + "╗")
    print("║   SATELLITE THERMAL SOURCE ATTRIBUTION — ML PIPELINE    ║")
    print("║   SIH 2026 PS 26162  |  Day 1 Pipeline                  ║")
    print("╚" + "═"*58 + "╝")
    print(f"\n  Persistence radius : {args.radius_km:.1f} km (Haversine)")
    print(f"  Spatial split lat  : {args.split_lat}° N")
    print(f"  Skip download      : {args.skip_download}")
    print(f"  Skip features      : {args.skip_features}")
    print(f"  Skip weather       : {args.skip_weather}")
    print(f"  Force OSM refresh  : {args.force_osm_refresh}")

    results = {}

    # ── Stage 1: Data ─────────────────────────────────────────────────────
    if args.skip_download:
        print("\n  [SKIP] Stage 1 — using existing data files")
        clean_path = Path("data/processed/firms_viirs_clean.csv")
        if not clean_path.exists():
            print("  ❌ Cleaned data not found. Remove --skip-download and re-run.")
            sys.exit(1)
        results["stage_1"] = "skipped"
    else:
        ok = run_stage_1_download(args)
        results["stage_1"] = "success" if ok else "failed"
        if not ok:
            print("\n  Pipeline stopped at Stage 1. Fix data source and re-run.")
            sys.exit(1)

    # ── Stage 2: Features ─────────────────────────────────────────────────
    if args.skip_features:
        print("\n  [SKIP] Stage 2 — using existing feature file")
        feat_path = Path("data/features/source_classification_features.csv")
        if not feat_path.exists():
            print("  ❌ Feature file not found. Remove --skip-features and re-run.")
            sys.exit(1)
        results["stage_2"] = "skipped"
    else:
        ok = run_stage_2_features(args)
        results["stage_2"] = "success" if ok else "failed"
        if not ok:
            print("\n  Pipeline stopped at Stage 2.")
            sys.exit(1)

    # ── Stage 3: Training ─────────────────────────────────────────────────
    ok = run_stage_3_training(args)
    results["stage_3"] = "success" if ok else "failed"
    if not ok:
        print("\n  Pipeline stopped at Stage 3.")
        sys.exit(1)

    # ── Final summary ─────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    minutes, seconds = divmod(int(elapsed), 60)

    print("\n" + "╔" + "═"*58 + "╗")
    print("║   PIPELINE COMPLETE                                      ║")
    print("╚" + "═"*58 + "╝")
    print(f"\n  Stage results:")
    for stage, status in results.items():
        icon = "✓" if status in ("success", "skipped") else "❌"
        print(f"    {icon} {stage}: {status}")
    print(f"\n  Total time: {minutes}m {seconds}s")
    print(f"\n  Output artifacts:")
    print(f"    data/raw/firms_viirs_raw.csv")
    print(f"    data/processed/firms_viirs_clean.csv")
    print(f"    data/features/source_classification_features.csv")
    print(f"    data/features/dataset_summary.json")
    print(f"    models/source_classifier.pkl")
    print(f"    models/source_classifier_no_distances.pkl")
    print(f"    models/label_encoder.pkl")
    print(f"    models/feature_columns.json")
    print(f"    models/feature_columns_no_distances.json")
    print(f"    models/model_metadata.json")
    print(f"    models/leakage_report.json")
    print(f"    models/plots/")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Run the complete thermal source attribution ML pipeline."
    )

    # Data options
    parser.add_argument("--bbox", default=None, help="FIRMS bbox W,S,E,N")
    parser.add_argument("--days", type=int, default=None, help="FIRMS NRT days")
    parser.add_argument("--dataset", default=None, help="FIRMS dataset name")
    parser.add_argument("--local-file", default=None, help="Local FIRMS CSV path")

    # Skip flags
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip Stage 1 (use existing raw/clean data)")
    parser.add_argument("--skip-features", action="store_true",
                        help="Skip Stage 2 (use existing feature table)")

    # Feature engineering options
    parser.add_argument("--radius-km", type=float,
                        default=float(os.getenv("PERSISTENCE_RADIUS_KM", "1.0")),
                        help="Spatial matching radius for temporal features (km). Default: 1.0")
    parser.add_argument("--force-osm-refresh", action="store_true",
                        help="Re-query Overpass API even if OSM cache exists")
    parser.add_argument("--skip-weather", action="store_true",
                        help="Skip weather enrichment")

    # Training options
    parser.add_argument("--split-lat", type=float,
                        default=float(os.getenv("SPATIAL_SPLIT_LAT", "15.0")),
                        help="Latitude boundary for spatial train/test split (default: 15.0)")

    args = parser.parse_args()
    run_pipeline(args)
