"""
ml/evaluation/evaluate_model.py
=================================
Model Evaluation Utilities

Computes and reports:
  - Accuracy, Precision, Recall, F1 (per-class and macro)
  - Confusion matrix (raw counts + normalized)
  - Feature importance (XGBoost native gain-based)
  - SHAP explainability values (best-effort, skipped if SHAP unavailable)
  - Data leakage diagnostic report

All plots are saved to models/plots/.
All metrics are returned as a dict for storage in model_metadata.json.

IMPORTANT: This module reports metrics honestly.
  - If performance is very high, it flags possible label-leakage.
  - If performance is poor, it reports that honestly with possible causes.
  - We do NOT tune the model after seeing test results.
"""

import json
import logging
import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)

PLOTS_DIR = Path("models/plots")


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------
def evaluate_model(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    class_names: List[str],
    experiment_name: str = "experiment",
    save_plots: bool = True,
) -> Dict[str, Any]:
    """
    Run full evaluation of a trained XGBoost classifier on the test set.

    Parameters
    ----------
    model : fitted XGBoost classifier
    X_test : pd.DataFrame
    y_test : pd.Series (integer-encoded)
    class_names : list of str (label names, index-aligned with integer codes)
    experiment_name : str (used for plot filenames)
    save_plots : bool

    Returns
    -------
    dict with all evaluation metrics
    """
    y_pred = model.predict(X_test)
    y_pred_proba = None
    try:
        y_pred_proba = model.predict_proba(X_test)
    except Exception:
        pass

    # ── Core metrics ─────────────────────────────────────────────────────
    accuracy = float(accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

    precision_per_class = precision_score(y_test, y_pred, average=None, zero_division=0)
    recall_per_class = recall_score(y_test, y_pred, average=None, zero_division=0)
    f1_per_class = f1_score(y_test, y_pred, average=None, zero_division=0)

    # Map back to class names (handle classes that might not appear in test)
    present_classes = sorted(y_test.unique())
    per_class = {}
    for i, cls_idx in enumerate(present_classes):
        cls_name = class_names[cls_idx] if cls_idx < len(class_names) else str(cls_idx)
        per_class[cls_name] = {
            "precision": round(float(precision_per_class[i]), 4),
            "recall": round(float(recall_per_class[i]), 4),
            "f1": round(float(f1_per_class[i]), 4),
            "support": int((y_test == cls_idx).sum()),
        }

    # ── Confusion matrix ──────────────────────────────────────────────────
    present_names = [class_names[i] for i in present_classes if i < len(class_names)]
    cm = confusion_matrix(y_test, y_pred, labels=present_classes)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    # ── Print report ──────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  EVALUATION: {experiment_name}")
    print(f"{'═'*60}")
    print(f"  Test set size : {len(y_test):,}")
    print(f"  Accuracy      : {accuracy:.4f}")
    print(f"  Macro F1      : {macro_f1:.4f}")
    print(f"  Weighted F1   : {weighted_f1:.4f}")
    print(f"\n  Per-class metrics:")
    for cls_name, m in per_class.items():
        print(f"    {cls_name:20s}  P={m['precision']:.3f}  R={m['recall']:.3f}  "
              f"F1={m['f1']:.3f}  support={m['support']}")
    print(f"\n  Confusion matrix ({', '.join(present_names)}):")
    print(f"  (rows=actual, cols=predicted)")
    for i, row in enumerate(cm):
        print(f"    {present_names[i]:18s}: {row}")

    # ── Leakage flag ──────────────────────────────────────────────────────
    leakage_flag = _check_leakage_indicators(accuracy, macro_f1)

    # ── Plots ─────────────────────────────────────────────────────────────
    if save_plots:
        _plot_confusion_matrix(cm_norm, present_names, experiment_name)

    result = {
        "experiment": experiment_name,
        "test_size": int(len(y_test)),
        "accuracy": round(accuracy, 6),
        "macro_f1": round(macro_f1, 6),
        "weighted_f1": round(weighted_f1, 6),
        "per_class_metrics": per_class,
        "confusion_matrix_counts": cm.tolist(),
        "confusion_matrix_normalized": np.round(cm_norm, 4).tolist(),
        "confusion_matrix_labels": present_names,
        "possible_leakage_flag": leakage_flag,
    }
    return result


# ---------------------------------------------------------------------------
# Feature importance
# ---------------------------------------------------------------------------
def get_feature_importance(model, feature_names: List[str], top_n: int = 20) -> Dict:
    """Extract and rank XGBoost feature importances (gain-based)."""
    try:
        importance_dict = model.get_booster().get_fscore()  # frequency
        # Prefer 'gain' importance
        scores = model.feature_importances_
        fi = pd.Series(scores, index=feature_names).sort_values(ascending=False)

        top = fi.head(top_n)
        result = {
            "top_features": [
                {"feature": name, "importance": round(float(val), 6)}
                for name, val in top.items()
            ],
            "all_importances": {name: round(float(val), 6) for name, val in fi.items()},
        }

        print(f"\n  Top {top_n} Features by Importance (gain):")
        for i, (name, val) in enumerate(top.items(), 1):
            print(f"    {i:2d}. {name:35s}: {val:.6f}")

        return result

    except Exception as exc:
        logger.warning("Could not extract feature importance: %s", exc)
        return {"error": str(exc)}


def plot_feature_importance(importance_dict: Dict, experiment_name: str) -> None:
    """Save a bar chart of top feature importances."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        top = importance_dict.get("top_features", [])[:20]
        if not top:
            return

        names = [x["feature"] for x in top][::-1]
        vals = [x["importance"] for x in top][::-1]

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(names, vals, color="#2196F3", alpha=0.8)
        ax.set_xlabel("Feature Importance (gain)")
        ax.set_title(f"Feature Importance — {experiment_name}")
        ax.grid(axis="x", alpha=0.3)
        plt.tight_layout()

        PLOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = PLOTS_DIR / f"feature_importance_{experiment_name}.png"
        plt.savefig(path, dpi=150)
        plt.close()
        logger.info("Feature importance plot saved: %s", path)
    except Exception as exc:
        logger.warning("Could not plot feature importance: %s", exc)


# ---------------------------------------------------------------------------
# SHAP (best-effort)
# ---------------------------------------------------------------------------
def compute_shap_values(model, X_test: pd.DataFrame, experiment_name: str) -> Optional[Dict]:
    """
    Compute SHAP values for model explainability.
    Skipped gracefully if SHAP is not installed or fails.
    """
    try:
        import shap
        logger.info("Computing SHAP values…")

        explainer = shap.TreeExplainer(model)
        # Use a sample of up to 500 test rows to keep it fast
        sample = X_test.sample(min(500, len(X_test)), random_state=42)
        shap_values = explainer.shap_values(sample)

        # For multiclass, shap_values is a list of arrays (one per class)
        if isinstance(shap_values, list):
            # Use mean absolute SHAP across all classes
            mean_abs_shap = np.mean([np.abs(sv) for sv in shap_values], axis=0)
        else:
            mean_abs_shap = np.abs(shap_values)

        mean_abs_per_feature = mean_abs_shap.mean(axis=0)
        shap_series = pd.Series(mean_abs_per_feature, index=sample.columns).sort_values(ascending=False)

        print("\n  Top 10 Features by SHAP (mean |SHAP|):")
        for i, (name, val) in enumerate(shap_series.head(10).items(), 1):
            print(f"    {i:2d}. {name:35s}: {val:.6f}")

        # Save SHAP summary plot
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            PLOTS_DIR.mkdir(parents=True, exist_ok=True)
            plt.figure()
            if isinstance(shap_values, list):
                shap.summary_plot(shap_values[0], sample, show=False, max_display=15)
            else:
                shap.summary_plot(shap_values, sample, show=False, max_display=15)
            plt.tight_layout()
            path = PLOTS_DIR / f"shap_summary_{experiment_name}.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close()
            logger.info("SHAP summary plot saved: %s", path)
        except Exception as plot_exc:
            logger.warning("SHAP plot failed: %s", plot_exc)

        return {
            "top_shap_features": [
                {"feature": name, "mean_abs_shap": round(float(val), 6)}
                for name, val in shap_series.head(15).items()
            ]
        }

    except ImportError:
        logger.info("SHAP not installed — skipping SHAP analysis. Install with: pip install shap")
        return None
    except Exception as exc:
        logger.warning("SHAP computation failed (non-blocking): %s", exc)
        return None


# ---------------------------------------------------------------------------
# Leakage diagnostic
# ---------------------------------------------------------------------------
def run_leakage_diagnostic(
    metrics_with_distances: Dict,
    metrics_without_distances: Dict,
    metrics_no_osm: Optional[Dict] = None,
) -> Dict:
    """
    Three-experiment leakage diagnostic.

    Experiment A: all features including distance_to_* and ctx_*    [HIGH leakage risk]
    Experiment B: distance_to_* and near_* removed; ctx_* kept      [MEDIUM leakage risk]
    Experiment C: ALL OSM-derived features removed                   [NO leakage]

    Experiment C is the only fully honest benchmark.
    """
    acc_a = metrics_with_distances.get("accuracy", 0)
    acc_b = metrics_without_distances.get("accuracy", 0)
    f1_a  = metrics_with_distances.get("macro_f1", 0)
    f1_b  = metrics_without_distances.get("macro_f1", 0)

    acc_c = metrics_no_osm.get("accuracy", 0) if metrics_no_osm else None
    f1_c  = metrics_no_osm.get("macro_f1", 0) if metrics_no_osm else None

    acc_drop_ab = acc_a - acc_b
    f1_drop_ab  = f1_a  - f1_b
    acc_drop_ac = (acc_a - acc_c) if acc_c is not None else None
    f1_drop_ac  = (f1_a  - f1_c) if f1_c  is not None else None

    LEAKAGE_THRESHOLD = 0.10

    leakage_detected = (acc_drop_ab > LEAKAGE_THRESHOLD) or (f1_drop_ab > LEAKAGE_THRESHOLD)

    report = {
        "experiment_A_all_features": {
            "accuracy": acc_a, "macro_f1": f1_a,
            "description": "All features (distance_to_*, ctx_*, near_*, thermal, temporal)",
            "leakage_risk": "HIGH",
        },
        "experiment_B_no_distances": {
            "accuracy": acc_b, "macro_f1": f1_b,
            "description": "distance_to_* and near_* removed; ctx_* context features kept",
            "leakage_risk": "MEDIUM — ctx_* are OSM-derived",
        },
        "experiment_C_no_osm": {
            "accuracy": acc_c, "macro_f1": f1_c,
            "description": "ALL OSM-derived features removed — pure thermal + temporal signal",
            "leakage_risk": "NONE — fully honest benchmark",
        } if metrics_no_osm else None,
        "accuracy_drop_A_minus_B": round(acc_drop_ab, 4),
        "macro_f1_drop_A_minus_B": round(f1_drop_ab, 4),
        "accuracy_drop_A_minus_C": round(acc_drop_ac, 4) if acc_drop_ac is not None else None,
        "macro_f1_drop_A_minus_C": round(f1_drop_ac, 4) if f1_drop_ac is not None else None,
        "leakage_detected": leakage_detected,
        "primary_honest_benchmark": "experiment_C" if metrics_no_osm else "experiment_B",
        "label_type": "weak_geographic_labels_NOT_verified_fire_cause",
        "interpretation": (
            "SIGNIFICANT LEAKAGE CONFIRMED. "
            "Experiment C (no OSM features) is the only fully honest performance estimate. "
            "Experiments A and B both contain OSM-derived features that were also used to "
            "generate source_label, producing artificially inflated metrics."
            if leakage_detected else
            "Leakage impact appears moderate. The model learns genuine thermal/temporal signal. "
            "Experiment C remains the recommended conservative estimate."
        ),
        "recommendation": (
            "Report Experiment C Macro F1 as the model's actual capability. "
            "Experiment A is an upper bound only — not a realistic performance estimate."
            if leakage_detected else
            "All three experiments are useful. Experiment C is the conservative reference."
        ),
    }

    print("\n" + "=" * 64)
    print("  DATA LEAKAGE DIAGNOSTIC REPORT")
    print("  Label: WEAK GEOGRAPHIC LABELS (NOT verified fire-cause)")
    print("=" * 64)
    print(f"  Exp A [HIGH leak]   — Acc: {acc_a:.4f}  Macro F1: {f1_a:.4f}")
    print(f"  Exp B [MED  leak]   — Acc: {acc_b:.4f}  Macro F1: {f1_b:.4f}")
    if acc_c is not None:
        print(f"  Exp C [NO   leak]   — Acc: {acc_c:.4f}  Macro F1: {f1_c:.4f}  (*)")
    print(f"  Accuracy drop (A-B) : {acc_drop_ab:+.4f}")
    print(f"  F1 drop (A-B)       : {f1_drop_ab:+.4f}")
    if acc_drop_ac is not None:
        print(f"  Accuracy drop (A-C) : {acc_drop_ac:+.4f}")
        print(f"  F1 drop (A-C)       : {f1_drop_ac:+.4f}")
    print(f"  Leakage detected    : {'YES' if leakage_detected else 'NO'}")
    print(f"  (*) Experiment C = only fully leakage-free result.")
    print("=" * 64 + "\n")

    print(f"  {report['interpretation']}")

    return report




# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _check_leakage_indicators(accuracy: float, macro_f1: float) -> str:
    if accuracy > 0.95 and macro_f1 > 0.90:
        return (
            "WARNING: Very high accuracy/F1 — strong label-distance leakage likely. "
            "Check Experiment B (without distance features) for honest performance."
        )
    elif accuracy > 0.85:
        return "CAUTION: High accuracy — verify with Experiment B (leakage investigation)."
    else:
        return "No obvious leakage flag from accuracy alone."


def _plot_confusion_matrix(cm_norm: np.ndarray, class_names: List[str], title: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(
            cm_norm,
            annot=True,
            fmt=".2f",
            cmap="Blues",
            xticklabels=class_names,
            yticklabels=class_names,
            ax=ax,
        )
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(f"Confusion Matrix (Normalized) — {title}")
        plt.tight_layout()

        PLOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = PLOTS_DIR / f"confusion_matrix_{title}.png"
        plt.savefig(path, dpi=150)
        plt.close()
        logger.info("Confusion matrix plot saved: %s", path)
    except Exception as exc:
        logger.warning("Could not plot confusion matrix: %s", exc)
