import os, sys
os.environ.setdefault("PYTHONUTF8", "1")
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
"""
ml/training/train_model.py
============================
XGBoost Source Classification Training Script

Label disclaimer:
  source_label is a WEAK GEOGRAPHIC LABEL generated from OSM proximity.
  It is NOT verified fire-cause ground truth. The model classifies based
  on spatial and thermal patterns that approximate — but do not confirm —
  the actual cause of each thermal event.

Experiments:
  A — All features (distance_to_*, ctx_*, near_*, thermal, temporal)
      Leakage risk: HIGH (label-generating features used as inputs)
  B — Distance_to_* and near_* removed; ctx_* kept
      Leakage risk: MEDIUM (ctx_* still derived from OSM labeling logic)
  C — ALL OSM-derived features removed (distance_to_*, near_*, ctx_*, dominant_context)
      Leakage risk: NONE — pure thermal + temporal satellite signal
      This is the only fully honest benchmark.

Spatial split:
  Events where latitude < SPATIAL_SPLIT_LAT are held out as test set.
  Default: 15.0 deg N (southern India) — geographically separated from training.
"""

import json
import logging
import os
import pickle
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

warnings.filterwarnings("ignore", category=UserWarning)

# Allow import from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.evaluation.evaluate_model import (
    evaluate_model,
    get_feature_importance,
    plot_feature_importance,
    compute_shap_values,
    run_leakage_diagnostic,
)

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FEATURES_CSV    = Path("data/processed/firms_weather_enriched.csv")
MODEL_DIR       = Path("models")
MODEL_PATH      = MODEL_DIR / "experiment_d_model.pkl"
ENCODER_PATH    = MODEL_DIR / "experiment_d_label_encoder.pkl"
FEATURE_COLS_PATH = MODEL_DIR / "experiment_d_feature_columns.json"
METADATA_PATH   = MODEL_DIR / "experiment_d_metadata.json"
LEAKAGE_REPORT_PATH = MODEL_DIR / "experiment_d_leakage_report.json"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SPATIAL_SPLIT_LAT = float(os.getenv("SPATIAL_SPLIT_LAT", "15.0"))
RANDOM_SEED       = int(os.getenv("RANDOM_SEED", "42"))

# Features used to generate source_label — excluded in Experiment B
LABEL_GENERATING_DISTANCE_COLS = [
    "distance_to_industrial",
    "distance_to_factory",
    "distance_to_chemical",
    "distance_to_refinery",
    "distance_to_gas",
    "distance_to_mine",
    "distance_to_quarry",
    "distance_to_pipeline",
    "distance_to_forest",
    "distance_to_cropland",
    "near_industrial",
    "near_factory",
    "near_mine",
    "near_quarry",
    "near_forest",
    "near_cropland",
]

# ALL OSM-derived features (distance_to_*, near_*, ctx_*, dominant_context)
# Removed in Experiment C — the fully leakage-free benchmark.
OSM_ALL_DERIVED_COLS = LABEL_GENERATING_DISTANCE_COLS + [
    "ctx_industrial_context",
    "ctx_mining_context",
    "ctx_forest_context",
    "ctx_agricultural_context",
    "dominant_context",
]

# Minimum test-set support below which class estimates are flagged as unreliable
MIN_RELIABLE_SUPPORT = 30

# Columns that are NOT features (meta / target / audit)
NON_FEATURE_COLS = {
    "source_label",
    "source_label_int",
    "label_rationale",
    "dominant_context",
    "acq_date",
    "datetime_utc",
    "satellite",
    "confidence_raw",
    "day_night",
}

# Categorical columns to one-hot encode
CATEGORICAL_COLS = ["satellite", "dominant_context"]


# ---------------------------------------------------------------------------
# 1. Data loading & validation
# ---------------------------------------------------------------------------
def load_and_validate(features_path: Path) -> pd.DataFrame:
    """Load feature CSV and validate minimum requirements."""
    if not features_path.exists():
        raise FileNotFoundError(
            f"Feature dataset not found: {features_path}\n"
            "Run: python ml/feature_engineering/build_features.py"
        )

    logger.info("Loading feature dataset: %s", features_path)
    df = pd.read_csv(features_path, low_memory=False)
    logger.info("Loaded %d rows × %d columns", len(df), len(df.columns))

    # ── Minimum row check ────────────────────────────────────────────────
    if len(df) < 50:
        raise ValueError(
            f"Dataset has only {len(df)} rows — too small to train meaningfully. "
            "Collect more FIRMS data (increase days or area)."
        )

    # ── Required columns ─────────────────────────────────────────────────
    required = {"latitude", "longitude", "frp", "source_label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Feature dataset missing required columns: {missing}")

    # ── Target label check ───────────────────────────────────────────────
    if df["source_label"].isna().all():
        raise ValueError("All source_label values are NaN — labeling step failed.")

    df = df.dropna(subset=["source_label"]).copy()

    # ── Class distribution check ─────────────────────────────────────────
    dist = df["source_label"].value_counts()
    logger.info("Label distribution:\n%s", dist.to_string())

    min_class_count = dist.min()
    if min_class_count < 5:
        rare = dist[dist < 5].index.tolist()
        logger.warning(
            "Classes with < 5 training samples: %s — predictions will be unreliable.", rare
        )

    print("\n" + "=" * 64)
    print("  LABEL DISCLAIMER")
    print("  source_label = WEAK GEOGRAPHIC LABEL from OSM proximity.")
    print("  NOT verified fire-cause ground truth.")
    print("=" * 64)
    print("\n-- Training Dataset Summary ------------------------------------")
    print(f"  Total rows    : {len(df):,}")
    print(f"  Features (raw): {len(df.columns)}")
    print(f"  Label distribution:")
    for label, count in dist.items():
        print(f"    {label:20s}: {count:6d} ({100*count/len(df):.1f}%)")
    print("----------------------------------------------------------------\n")
    return df


# ---------------------------------------------------------------------------
# 2. Feature preparation
# ---------------------------------------------------------------------------
def prepare_features(
    df: pd.DataFrame,
    label_encoder: LabelEncoder,
    fit_encoder: bool = True,
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Encode categoricals, drop non-features, encode target label.

    Returns
    -------
    X : pd.DataFrame — numeric feature matrix
    y : pd.Series   — integer-encoded labels
    feature_names : list of str
    """
    df = df.copy()

    # ── Encode target ─────────────────────────────────────────────────────
    if fit_encoder:
        label_encoder.fit(df["source_label"])
    y = pd.Series(label_encoder.transform(df["source_label"]), name="label")

    # ── Encode satellite (categorical) ────────────────────────────────────
    if "satellite" in df.columns:
        sat_dummies = pd.get_dummies(df["satellite"], prefix="satellite", dtype=float)
        df = pd.concat([df.drop(columns=["satellite"]), sat_dummies], axis=1)

    # ── Encode dominant_context (categorical) ─────────────────────────────
    if "dominant_context" in df.columns:
        ctx_dummies = pd.get_dummies(df["dominant_context"], prefix="ctx", dtype=float)
        df = pd.concat([df.drop(columns=["dominant_context"]), ctx_dummies], axis=1)

    # ── Drop non-feature columns ──────────────────────────────────────────
    drop_cols = [c for c in NON_FEATURE_COLS if c in df.columns]
    df.drop(columns=drop_cols, inplace=True, errors="ignore")

    # ── Keep only numeric ─────────────────────────────────────────────────
    X = df.select_dtypes(include=[np.number]).copy()

    # ── Fill remaining NaN with column median (preserve structure) ────────
    X.fillna(X.median(), inplace=True)

    # ── Clip extreme outliers (3 × IQR) ──────────────────────────────────
    for col in X.columns:
        q1, q3 = X[col].quantile([0.01, 0.99])
        iqr = q3 - q1
        X[col] = X[col].clip(q1 - 3 * iqr, q3 + 3 * iqr)

    feature_names = list(X.columns)
    logger.info("Feature matrix: %d rows × %d features", len(X), len(feature_names))

    return X, y, feature_names


# ---------------------------------------------------------------------------
# 3. Spatial train/test split
# ---------------------------------------------------------------------------
def spatial_train_test_split(
    df: pd.DataFrame,
    X: pd.DataFrame,
    y: pd.Series,
    split_lat: float = SPATIAL_SPLIT_LAT,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Split dataset by geographic latitude.

    Events south of split_lat → TEST set (geographically held-out region).
    Events north of split_lat → TRAIN set.

    This prevents spatial autocorrelation leakage: nearby events that would
    otherwise appear in both train and test after a random shuffle.

    Parameters
    ----------
    split_lat : float
        Latitude boundary. Default: 15.0° N (southern India as test region).

    Returns
    -------
    X_train, X_test, y_train, y_test
    """
    if "latitude" not in df.columns:
        raise ValueError("DataFrame must have 'latitude' column for spatial split.")

    test_mask = df["latitude"] < split_lat
    train_mask = ~test_mask

    n_train = train_mask.sum()
    n_test = test_mask.sum()

    if n_test < 10:
        logger.warning(
            "Spatial split (lat < %.1f) yields only %d test samples. "
            "Consider adjusting SPATIAL_SPLIT_LAT.", split_lat, n_test
        )
    if n_train < 30:
        raise ValueError(
            f"Spatial split yields only {n_train} training samples. "
            "Adjust SPATIAL_SPLIT_LAT or collect more data."
        )

    print(f"\n── Spatial Train/Test Split (lat < {split_lat}° → TEST) ────────")
    print(f"  Training set : {n_train:,} events (lat ≥ {split_lat}°)")
    print(f"  Test set     : {n_test:,} events  (lat < {split_lat}°)")
    print(f"  Test ratio   : {100*n_test/(n_train+n_test):.1f}%")
    print("  Rationale: Geographic separation prevents spatial autocorrelation")
    print("  leakage — nearby events appear only in train OR test, not both.")
    print("────────────────────────────────────────────────────────────────\n")

    return (
        X[train_mask].reset_index(drop=True),
        X[test_mask].reset_index(drop=True),
        y[train_mask].reset_index(drop=True),
        y[test_mask].reset_index(drop=True),
    )


# ---------------------------------------------------------------------------
# 4. XGBoost training
# ---------------------------------------------------------------------------
def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_classes: int,
    experiment_name: str = "exp_A",
    min_child_weight: int = 5,
) -> object:
    """
    Train XGBoost multiclass classifier with class weighting.

    Class imbalance is handled via sample_weight computed from training labels.
    We do NOT over-optimise hyperparameters — defaults with conservative settings
    to avoid overfitting to small datasets.

    Parameters
    ----------
    X_train, y_train : training data
    n_classes : number of target classes
    experiment_name : for logging

    Returns
    -------
    Fitted XGBClassifier
    """
    try:
        from xgboost import XGBClassifier
    except ImportError:
        raise ImportError("XGBoost not installed. Run: pip install xgboost")

    logger.info("Training XGBoost [%s]: %d samples, %d features, %d classes",
                experiment_name, len(X_train), X_train.shape[1], n_classes)

    # Compute sample weights for class balancing
    sample_weights = compute_sample_weight("balanced", y_train)

    # Conservative hyperparameters — not tuned to maximise test score
    # Deliberately moderate depth and estimators for interpretability
    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=min_child_weight,  # lowered to 1 for Exp C (minority class support)
        gamma=1.0,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="multi:softprob",
        num_class=n_classes,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=RANDOM_SEED,
        n_jobs=-1,
        tree_method="hist",
        verbosity=0,
    )

    model.fit(
        X_train,
        y_train,
        sample_weight=sample_weights,
        eval_set=[(X_train, y_train)],
        verbose=False,
    )

    logger.info("XGBoost training complete [%s]", experiment_name)
    return model


# ---------------------------------------------------------------------------
# 5. Save artifacts
# ---------------------------------------------------------------------------
def save_artifacts(
    model,
    label_encoder: LabelEncoder,
    feature_names: List[str],
    metrics_a: Dict,
    metrics_b: Dict,
    metrics_c: Dict,
    metrics_d: Dict,
    leakage_report: Dict,
    dataset_size: int,
    n_classes: int,
) -> None:
    """Save model, encoder, feature column list, and metadata."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # ── Model (Experiment A — full features, for practical inference) ─────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    logger.info("Model saved: %s", MODEL_PATH)

    # ── Label encoder ─────────────────────────────────────────────────────
    with open(ENCODER_PATH, "wb") as f:
        pickle.dump(label_encoder, f)
    logger.info("Label encoder saved: %s", ENCODER_PATH)

    # ── Feature column order ──────────────────────────────────────────────
    with open(FEATURE_COLS_PATH, "w") as f:
        json.dump(feature_names, f, indent=2)
    logger.info("Feature columns saved: %s", FEATURE_COLS_PATH)

    # ── Model metadata ────────────────────────────────────────────────────
    fi_a = get_feature_importance(model, feature_names, top_n=10)
    top_features = [x["feature"] for x in fi_a.get("top_features", [])[:10]]

    metadata = {
        "model_type": "XGBoostClassifier (multi:softprob)",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "training_dataset_size": dataset_size,
        "feature_count": len(feature_names),
        "class_names": list(label_encoder.classes_),
        "n_classes": n_classes,
        "spatial_split_latitude": SPATIAL_SPLIT_LAT,
        "spatial_split_description": (
            f"Events south of {SPATIAL_SPLIT_LAT}° N used as test set (southern India). "
            "Prevents spatial autocorrelation leakage."
        ),
        "label_type": "weak_geographic_labels_NOT_verified_fire_cause",
        "evaluation_experiment_A": metrics_a,
        "evaluation_experiment_B": metrics_b,
        "evaluation_experiment_C": metrics_c,
        "evaluation_experiment_D": metrics_d,
        "leakage_diagnostic": leakage_report,
        "primary_benchmark": "experiment_C",
        "primary_benchmark_rationale": (
            "Experiment C uses ONLY thermal and temporal satellite features — "
            "zero OSM-derived inputs. It is the only fully leakage-free benchmark. "
            "Experiments A and B are retained for comparison but not used for "
            "conservative performance estimation."
        ),
        "top_10_features_by_importance": top_features,
        "dataset_methodology": {
            "thermal_source": "NASA FIRMS VIIRS NRT / NOAA-20",
            "label_type": "weak_geographic_labels",
            "label_method": "OSM proximity-based — NOT verified fire-cause ground truth",
            "target_region": "India (bounding box 67,6,98,37)",
            "label_classes": list(label_encoder.classes_),
            "labeling_priority": [
                "1. Industrial (nearest OSM industrial/factory/refinery/chemical/gas < 2 km)",
                "2. Mining (nearest OSM mine/quarry < 2 km)",
                "3. Forest (nearest OSM forest < 1 km)",
                "4. Agricultural (nearest OSM farmland/cropland < 2 km)",
                "5. Other (no proximity match)",
            ],
        },
        "known_limitations": [
            "Labels are weak geographic labels — not verified fire-cause ground truth.",
            "OSM coverage in rural India is incomplete; unmapped features produce sentinel distances.",
            "Distance features used for labeling correlate with model input features (label leakage). "
            "See leakage_diagnostic in this file for quantified impact.",
            "Temporal persistence computed on FIRMS NRT data — only covers the acquisition window.",
            "Model trained on a single temporal snapshot — seasonal variation not fully captured.",
            "Class imbalance is handled by sample weighting, not oversampling.",
            "Weather features are optional and may be largely NaN if Open-Meteo was unavailable.",
        ],
        "reproduction_commands": [
            "python scripts/download_firms_data.py",
            "python ml/feature_engineering/build_features.py",
            "python ml/training/train_model.py",
        ],
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info("Model metadata saved: %s", METADATA_PATH)

    # ── Leakage report ────────────────────────────────────────────────────
    with open(LEAKAGE_REPORT_PATH, "w") as f:
        json.dump(leakage_report, f, indent=2, default=str)
    logger.info("Leakage report saved: %s", LEAKAGE_REPORT_PATH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_training(
    features_path: str = str(FEATURES_CSV),
    split_lat: float = SPATIAL_SPLIT_LAT,
) -> None:
    """
    Full training pipeline entry point.

    1. Load + validate data
    2. Prepare features
    3. Spatial split
    4. Train Experiment A (all features)
    5. Train Experiment B (without label-generating distance features)
    6. Evaluate both
    7. Leakage diagnostic
    8. Save all artifacts
    """
    print("\n" + "═" * 60)
    print("  THERMAL SOURCE ATTRIBUTION — TRAINING PIPELINE")
    print("  SIH 2026 PS 26162")
    print("═" * 60 + "\n")

    # ── 1. Load ───────────────────────────────────────────────────────────
    df = load_and_validate(Path(features_path))

    # ── 2. Prepare features ───────────────────────────────────────────────
    le = LabelEncoder()
    X_full, y_full, feature_names = prepare_features(df, label_encoder=le, fit_encoder=True)
    n_classes = len(le.classes_)

    logger.info("Classes: %s", list(le.classes_))
    logger.info("Feature count: %d", len(feature_names))

    # ── 3. Spatial split ──────────────────────────────────────────────────
    X_train_A, X_test_A, y_train, y_test = spatial_train_test_split(
        df, X_full, y_full, split_lat=split_lat
    )

    if len(y_test) == 0:
        raise ValueError(
            f"No test samples below latitude {split_lat}°. "
            "Adjust SPATIAL_SPLIT_LAT or collect data from a broader area."
        )

    # ── 4. Experiment A — All features ────────────────────────────────────
    print("\n" + "─" * 60)
    print("  EXPERIMENT A: All features (includes distance_to_* columns)")
    print("  NOTE: distance_to_* correlates with label — leakage risk")
    print("─" * 60)

    model_A = train_xgboost(X_train_A, y_train, n_classes, "exp_A")
    metrics_A = evaluate_model(
        model_A, X_test_A, y_test, list(le.classes_), "exp_A_with_distances"
    )
    fi_A = get_feature_importance(model_A, feature_names)
    plot_feature_importance(fi_A, "exp_A_with_distances")

    # -- 5. Experiment B — distances + near_* removed (ctx_* still present) ----
    print("\n" + "-" * 60)
    print("  EXPERIMENT B: distance_to_* and near_* removed")
    print("  NOTE: ctx_* features still present — medium leakage risk")
    print("-" * 60)

    B_drop = [c for c in LABEL_GENERATING_DISTANCE_COLS if c in feature_names]
    feature_names_B = [c for c in feature_names if c not in B_drop]
    X_train_B = X_train_A[feature_names_B].copy()
    X_test_B  = X_test_A[feature_names_B].copy()
    logger.info("Experiment B: removed %d features. Remaining: %d", len(B_drop), len(feature_names_B))
    print(f"  Dropped {len(B_drop)} distance/proximity features")

    model_B = train_xgboost(X_train_B, y_train, n_classes, "exp_B")
    metrics_B = evaluate_model(model_B, X_test_B, y_test, list(le.classes_), "exp_B_without_distances")
    fi_B = get_feature_importance(model_B, feature_names_B)
    plot_feature_importance(fi_B, "exp_B_without_distances")

    # -- 6. Experiment C — ALL OSM-derived features removed (fully clean) ------
    print("\n" + "-" * 60)
    print("  EXPERIMENT C: ALL OSM-derived features removed")
    print("  Removed: distance_to_*, near_*, ctx_*, dominant_context")
    print("  Kept: thermal + temporal satellite measurements ONLY")
    print("  Leakage risk: NONE — this is the fully honest benchmark")
    print("-" * 60)

    C_drop = [c for c in OSM_ALL_DERIVED_COLS if c in feature_names]
    # Also drop any one-hot encoded ctx_* / dominant_context columns
    C_drop_prefixes = ("ctx_", "dominant_context")
    
    weather_cols = [
        "temperature_2m_C", "dewpoint_2m_C", "u10", "v10", 
        "wind_speed_10m", "wind_direction_10m_deg", 
        "relative_humidity_2m_percent", "precipitation_mm", 
        "surface_pressure_hPa", "cloud_cover_percent", 
        "surface_solar_radiation"
    ]
    available_weather = [c for c in weather_cols if c in feature_names]
    
    feature_names_C = [
        c for c in feature_names
        if c not in C_drop and c not in available_weather and not any(c.startswith(p) for p in C_drop_prefixes)
    ]
    X_train_C = X_train_A[feature_names_C].copy()
    X_test_C  = X_test_A[feature_names_C].copy()

    # Assert zero intersection with OSM-derived names (correctness check)
    osm_remaining = [c for c in feature_names_C
                     if any(c.startswith(p) for p in ("distance_to_", "near_", "ctx_", "dominant_"))]
    if osm_remaining:
        logger.error("Exp C still contains OSM-derived cols: %s", osm_remaining)
        raise ValueError(f"Experiment C feature leak: {osm_remaining}")

    logger.info(
        "Experiment C: dropped %d OSM-derived features. Remaining: %d (%s)",
        len(C_drop), len(feature_names_C), feature_names_C
    )
    print(f"  Dropped {len(C_drop)} OSM-derived features and {len(available_weather)} weather features")
    print(f"  Remaining {len(feature_names_C)} features: {feature_names_C}")

    # Use min_child_weight=1 for Exp C to allow minority-class splits
    model_C = train_xgboost(
        X_train_C, y_train, n_classes, "exp_C", min_child_weight=1
    )
    metrics_C = evaluate_model(
        model_C, X_test_C, y_test, list(le.classes_), "exp_C_no_osm_features"
    )
    fi_C = get_feature_importance(model_C, feature_names_C)
    plot_feature_importance(fi_C, "exp_C_no_osm_features")

    # -- 7. Experiment D — Experiment C + Atmospheric Features ------
    print("\n" + "-" * 60)
    print("  EXPERIMENT D: Experiment C + Atmospheric/Weather Features")
    print("-" * 60)
    
    feature_names_D = feature_names_C + available_weather
    
    X_train_D = X_train_A[feature_names_D].copy()
    X_test_D  = X_test_A[feature_names_D].copy()
    
    print(f"  Added {len(available_weather)} weather features: {available_weather}")
    print(f"  Total {len(feature_names_D)} features for Experiment D")
    
    model_D = train_xgboost(
        X_train_D, y_train, n_classes, "exp_D", min_child_weight=1
    )
    metrics_D = evaluate_model(
        model_D, X_test_D, y_test, list(le.classes_), "exp_D_with_weather"
    )
    fi_D = get_feature_importance(model_D, feature_names_D)
    plot_feature_importance(fi_D, "exp_D_with_weather")

    # -- 8. Comparison Table ------
    print("\n" + "=" * 60)
    print("  EXPERIMENT C vs EXPERIMENT D COMPARISON")
    print("=" * 60)
    print(f"{'Metric':<20} {'Experiment C':<18} {'Experiment D':<18}")
    print("-" * 60)
    print(f"{'Accuracy':<20} {metrics_C['accuracy']*100:.2f}%{'':<11} {metrics_D['accuracy']*100:.2f}%")
    print(f"{'Macro F1':<20} {metrics_C.get('macro_f1', 0)*100:.2f}%{'':<11} {metrics_D.get('macro_f1', 0)*100:.2f}%")
    print("=" * 60 + "\n")

    # SHAP on Experiment C (most honest)
    logger.info("Computing SHAP values for Experiment C...")
    shap_result = compute_shap_values(model_C, X_test_C, "exp_C_no_osm_features")
    if shap_result:
        metrics_C["shap"] = shap_result

    # -- 7. Min-support analysis -------------------------------------------------
    dist_test = pd.Series(y_test).map(dict(enumerate(le.classes_))).value_counts()
    print("\n-- Test set class support analysis ----------------------------")
    for cls in le.classes_:
        n = dist_test.get(cls, 0)
        flag = "  [UNRELIABLE: < 30 test samples]" if n < MIN_RELIABLE_SUPPORT else ""
        print(f"  {cls:20s}: {n:4d} test samples{flag}")
    print("----------------------------------------------------------------")

    # -- 8. Leakage / 3-way comparison ------------------------------------------
    leakage_report = run_leakage_diagnostic(metrics_A, metrics_B, metrics_C)

    # ── 8. Save artifacts (Saving Experiment D) ───────────────────────────
    print("\nSaving Experiment D artifacts...")
    save_artifacts(
        model=model_D,
        label_encoder=le,
        feature_names=feature_names_D,
        metrics_a=metrics_A,
        metrics_b=metrics_B,
        metrics_c=metrics_C,
        metrics_d=metrics_D,
        leakage_report=leakage_report,
        dataset_size=len(X_full),
        n_classes=n_classes,
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_DIR / "source_classifier_no_distances.pkl", "wb") as f:
        pickle.dump(model_B, f)
    with open(MODEL_DIR / "feature_columns_no_distances.json", "w") as f:
        json.dump(feature_names_B, f, indent=2)
    with open(MODEL_DIR / "source_classifier_exp_c.pkl", "wb") as f:
        pickle.dump(model_C, f)
    with open(MODEL_DIR / "feature_columns_exp_c.json", "w") as f:
        json.dump(feature_names_C, f, indent=2)

    # -- 10. Honest 3-way summary -----------------------------------------------
    print("\n" + "=" * 64)
    print("  THREE-EXPERIMENT COMPARISON (honest leakage analysis)")
    print("  LABEL TYPE: weak geographic OSM proximity labels")
    print("  NOT verified fire-cause ground truth")
    print("=" * 64)
    hdr = f"  {'Experiment':<35} {'Acc':>7}  {'MacroF1':>8}  {'WtdF1':>7}"
    print(hdr)
    print("  " + "-" * 60)
    rows = [
        ("A — All features [HIGH leakage]",        metrics_A),
        ("B — No distances  [MEDIUM leakage]",      metrics_B),
        ("C — No OSM at all [NO leakage] (*)",      metrics_C),
    ]
    for label, m in rows:
        print(f"  {label:<35} {m['accuracy']:>7.4f}  {m['macro_f1']:>8.4f}  {m['weighted_f1']:>7.4f}")
    print("\n  (*) Experiment C is the only fully leakage-free benchmark.")
    print("      Use its Macro F1 as the conservative performance estimate.")
    print("=" * 64)
    print(f"\n  Dataset rows    : {len(df):,}")
    print(f"  Training events : {len(X_train_A):,}")
    print(f"  Test events     : {len(X_test_A):,}")
    print(f"  Classes         : {list(le.classes_)}")
    print(f"  Leakage A->C    : Acc drop {metrics_A['accuracy'] - metrics_C['accuracy']:+.4f}  "
          f"Macro F1 drop {metrics_A['macro_f1'] - metrics_C['macro_f1']:+.4f}")
    print(f"\n  Saved:")
    print(f"    {MODEL_PATH}  (Exp A)")
    print(f"    models/source_classifier_no_distances.pkl  (Exp B)")
    print(f"    models/source_classifier_exp_c.pkl         (Exp C - honest)")
    print(f"    {METADATA_PATH}")
    print(f"    {LEAKAGE_REPORT_PATH}")
    print("=" * 64 + "\n")


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

    parser = argparse.ArgumentParser(description="Train XGBoost source classifier")
    parser.add_argument(
        "--features-path", default=str(FEATURES_CSV),
        help="Path to feature CSV (default: data/features/source_classification_features.csv)"
    )
    parser.add_argument(
        "--split-lat", type=float, default=SPATIAL_SPLIT_LAT,
        help=f"Latitude below which events go to test set (default: {SPATIAL_SPLIT_LAT})"
    )
    args = parser.parse_args()

    run_training(features_path=args.features_path, split_lat=args.split_lat)
