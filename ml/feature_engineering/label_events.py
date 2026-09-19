"""
ml/feature_engineering/label_events.py
========================================
Weak Geographic Label Assignment for FIRMS Thermal Events

╔══════════════════════════════════════════════════════════════════════════╗
║  IMPORTANT DISCLAIMER                                                    ║
║                                                                          ║
║  Labels produced by this module are WEAK / NOISY geographic labels.     ║
║  They are derived from the spatial proximity of each FIRMS thermal       ║
║  event to mapped OpenStreetMap infrastructure categories.                ║
║                                                                          ║
║  These labels are NOT:                                                   ║
║    - Verified fire cause determinations                                  ║
║    - Official fire investigation records                                 ║
║    - Ground-truth from field surveys                                     ║
║                                                                          ║
║  Known limitations:                                                      ║
║    1. OSM coverage in rural India is incomplete.                         ║
║    2. A thermal event near an industrial facility may still be caused     ║
║       by vegetation burning or another unrelated source.                 ║
║    3. The same proximity distance used to assign a label is also used    ║
║       as a distance feature in the ML model — this creates a direct      ║
║       label-feature correlation (leakage). This is explicitly            ║
║       investigated and reported in the training pipeline.                ║
║                                                                          ║
║  This labeling methodology is documented in README.md and               ║
║  models/model_metadata.json.                                             ║
╚══════════════════════════════════════════════════════════════════════════╝

Label priority order (first match wins):
  1. Industrial  — distance_to_industrial OR factory/refinery/chemical/gas < LABEL_INDUSTRIAL_KM
  2. Mining      — distance_to_mine OR quarry < LABEL_MINING_KM
  3. Forest      — distance_to_forest < LABEL_FOREST_KM
  4. Agricultural — distance_to_cropland < LABEL_AGRICULTURAL_KM
  5. Other       — none of the above criteria satisfied

Thresholds are configurable via environment variables.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Label definitions
# ---------------------------------------------------------------------------
SOURCE_LABELS = {
    0: "Industrial",
    1: "Mining",
    2: "Agricultural",
    3: "Forest",
    4: "Other",
}

LABEL_TO_INT = {v: k for k, v in SOURCE_LABELS.items()}

# Labeling proximity thresholds (km) — configurable via env
LABEL_INDUSTRIAL_KM = float(os.getenv("LABEL_INDUSTRIAL_KM", "2.0"))
LABEL_MINING_KM = float(os.getenv("LABEL_MINING_KM", "2.0"))
LABEL_FOREST_KM = float(os.getenv("LABEL_FOREST_KM", "1.0"))
LABEL_AGRICULTURAL_KM = float(os.getenv("LABEL_AGRICULTURAL_KM", "2.0"))


# ---------------------------------------------------------------------------
# Labeling logic
# ---------------------------------------------------------------------------
def assign_source_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign weak geographic source labels to each thermal event.

    Requires OSM distance columns to be present (output of osm_enrichment.py):
      distance_to_industrial, distance_to_factory, distance_to_chemical,
      distance_to_refinery, distance_to_gas, distance_to_mine,
      distance_to_quarry, distance_to_forest, distance_to_cropland

    Parameters
    ----------
    df : pd.DataFrame
        OSM-enriched FIRMS data.

    Returns
    -------
    pd.DataFrame
        Input DataFrame with 'source_label' (str) and 'source_label_int' (int) columns.
    """
    df = df.copy()

    _check_required_columns(df)

    # Compute composite distances (min over related OSM types)
    df["_d_industrial_min"] = df[_present_cols(df, [
        "distance_to_industrial", "distance_to_factory",
        "distance_to_refinery", "distance_to_chemical", "distance_to_gas"
    ])].min(axis=1)

    df["_d_mining_min"] = df[_present_cols(df, [
        "distance_to_mine", "distance_to_quarry"
    ])].min(axis=1)

    df["_d_forest"] = df.get("distance_to_forest", pd.Series(np.full(len(df), 999.0), index=df.index))
    df["_d_cropland"] = df.get("distance_to_cropland", pd.Series(np.full(len(df), 999.0), index=df.index))

    labels = []
    label_rationale = []

    for _, row in df.iterrows():
        d_ind = row["_d_industrial_min"]
        d_min = row["_d_mining_min"]
        d_for = row["_d_forest"]
        d_agr = row["_d_cropland"]

        if d_ind < LABEL_INDUSTRIAL_KM:
            labels.append("Industrial")
            label_rationale.append(f"industrial_proximity_{d_ind:.2f}km")
        elif d_min < LABEL_MINING_KM:
            labels.append("Mining")
            label_rationale.append(f"mining_proximity_{d_min:.2f}km")
        elif d_for < LABEL_FOREST_KM:
            labels.append("Forest")
            label_rationale.append(f"forest_proximity_{d_for:.2f}km")
        elif d_agr < LABEL_AGRICULTURAL_KM:
            labels.append("Agricultural")
            label_rationale.append(f"agricultural_proximity_{d_agr:.2f}km")
        else:
            labels.append("Other")
            label_rationale.append("no_proximity_match")

    df["source_label"] = labels
    df["source_label_int"] = df["source_label"].map(LABEL_TO_INT)
    df["label_rationale"] = label_rationale  # diagnostic column

    # Drop internal columns
    df.drop(
        columns=["_d_industrial_min", "_d_mining_min", "_d_forest", "_d_cropland"],
        inplace=True, errors="ignore",
    )

    # ── Label distribution report ─────────────────────────────────────────
    dist = df["source_label"].value_counts()
    logger.info("Label distribution:\n%s", dist.to_string())

    print("\n── Weak Label Distribution (geographic proximity labels) ────────")
    print("  ⚠  These are NOT verified fire-cause ground truth.")
    print("  ⚠  Label-distance feature correlation exists — see leakage report.")
    for label, count in dist.items():
        pct = 100.0 * count / len(df)
        print(f"  {label:20s}: {count:6d} ({pct:.1f}%)")
    print("────────────────────────────────────────────────────────────────\n")

    return df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _check_required_columns(df: pd.DataFrame) -> None:
    """Warn if expected OSM distance columns are missing."""
    expected = [
        "distance_to_industrial", "distance_to_factory",
        "distance_to_mine", "distance_to_quarry",
        "distance_to_forest", "distance_to_cropland",
    ]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        logger.warning(
            "Missing OSM distance columns (using 999 km sentinel): %s", missing
        )


def _present_cols(df: pd.DataFrame, candidates: list) -> list:
    """Return only those column names that exist in df."""
    present = [c for c in candidates if c in df.columns]
    if not present:
        # Return a dummy column of 999 km
        df["_dummy_999"] = 999.0
        return ["_dummy_999"]
    return present
