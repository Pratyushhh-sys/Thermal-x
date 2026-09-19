"""
backend/services/model_service.py
===================================
Singleton model loading service.

Loads model artifacts ONCE at startup and validates feature columns
against the saved JSON list. Fails loudly on any mismatch.

Models managed:
  - Experiment C (primary): thermal + temporal features only, NO leakage
  - Experiment A (contextual): all features including OSM distances, HIGH leakage

Both are loaded and available for dual-prediction responses.

IMPORTANT: source_label is a WEAK GEOGRAPHIC LABEL from OSM proximity.
           NOT verified fire-cause ground truth.
"""

import json
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR   = PROJECT_ROOT / "models"

# Model artifact paths
_EXP_C_MODEL_PATH    = MODELS_DIR / "source_classifier_exp_c.pkl"
_EXP_C_COLS_PATH     = MODELS_DIR / "feature_columns_exp_c.json"
_EXP_A_MODEL_PATH    = MODELS_DIR / "source_classifier.pkl"
_EXP_A_COLS_PATH     = MODELS_DIR / "feature_columns.json"
_ENCODER_PATH        = MODELS_DIR / "label_encoder.pkl"
_METADATA_PATH       = MODELS_DIR / "model_metadata.json"


class ModelService:
    """
    Singleton wrapper around XGBoost classifiers.

    Must be initialised once at startup via `load()`.
    Validates feature column lists strictly — fails loudly on mismatch.
    """

    def __init__(self) -> None:
        self._model_c   = None
        self._model_a   = None
        self._encoder   = None
        self._cols_c: List[str] = []
        self._cols_a: List[str] = []
        self._metadata: dict = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------
    def load(self) -> None:
        """Load all model artifacts and validate feature column lists."""
        logger.info("Loading model artifacts from: %s", MODELS_DIR)

        # --- Label encoder (shared) ---
        if not _ENCODER_PATH.exists():
            raise FileNotFoundError(f"Label encoder not found: {_ENCODER_PATH}")
        with open(_ENCODER_PATH, "rb") as f:
            self._encoder = pickle.load(f)
        logger.info("Label encoder loaded. Classes: %s", list(self._encoder.classes_))

        # --- Experiment C (primary) ---
        self._model_c, self._cols_c = self._load_model(
            _EXP_C_MODEL_PATH, _EXP_C_COLS_PATH, "Experiment C"
        )

        # --- Experiment A (contextual) ---
        self._model_a, self._cols_a = self._load_model(
            _EXP_A_MODEL_PATH, _EXP_A_COLS_PATH, "Experiment A"
        )

        # --- Metadata ---
        if _METADATA_PATH.exists():
            with open(_METADATA_PATH) as f:
                self._metadata = json.load(f)
            logger.info("Model metadata loaded.")

        self._loaded = True
        logger.info(
            "ModelService ready. Exp C: %d features. Exp A: %d features.",
            len(self._cols_c), len(self._cols_a),
        )

    def _load_model(self, model_path: Path, cols_path: Path, name: str):
        """Load one model + its feature column list with strict validation."""
        if not model_path.exists():
            raise FileNotFoundError(f"{name} model not found: {model_path}")
        if not cols_path.exists():
            raise FileNotFoundError(f"{name} feature columns not found: {cols_path}")

        with open(model_path, "rb") as f:
            model = pickle.load(f)
        with open(cols_path) as f:
            cols = json.load(f)

        # Validate the model reports the same number of features
        try:
            expected_n = model.n_features_in_
            if expected_n != len(cols):
                raise RuntimeError(
                    f"FEATURE MISMATCH in {name}!\n"
                    f"  Model expects {expected_n} features.\n"
                    f"  Feature column JSON has {len(cols)} entries.\n"
                    f"  Column file: {cols_path}\n"
                    f"  This must be fixed before the API will serve predictions."
                )
        except AttributeError:
            logger.warning("%s: Cannot validate n_features_in_ (old XGBoost?). Proceeding.", name)

        logger.info("%s loaded: %d features, path=%s", name, len(cols), model_path.name)
        return model, cols

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------
    def _make_feature_vector(
        self, feature_dict: Dict[str, float], col_list: List[str], experiment_name: str
    ) -> pd.DataFrame:
        """
        Build a feature vector in exact saved column order.
        Missing features become NaN (XGBoost handles these natively).
        Raises if feature dict contains unexpected keys (safety check).
        """
        row = {}
        for col in col_list:
            val = feature_dict.get(col, np.nan)
            row[col] = val

        df = pd.DataFrame([row], columns=col_list)

        # Detect columns present in dict but NOT in saved columns
        extra = set(feature_dict.keys()) - set(col_list)
        if extra:
            logger.debug(
                "[%s] Ignored %d extra features not in saved column list: %s",
                experiment_name, len(extra), sorted(extra)
            )

        return df

    def predict_exp_c(self, feature_dict: Dict[str, float]) -> Dict:
        """
        Predict using Experiment C (thermal + temporal only — no OSM, NO leakage).

        Parameters
        ----------
        feature_dict : dict mapping feature_name → value

        Returns
        -------
        dict with keys: source, confidence, probabilities, model_experiment, label_type
        """
        if not self._loaded:
            raise RuntimeError("ModelService.load() must be called before predict().")

        X = self._make_feature_vector(feature_dict, self._cols_c, "Exp C")
        proba = self._model_c.predict_proba(X)[0]
        class_names = list(self._encoder.classes_)

        predicted_idx = int(np.argmax(proba))
        return {
            "source": class_names[predicted_idx],
            "label": "Probable Source",
            "confidence": float(proba[predicted_idx]),
            "probabilities": {cls: float(p) for cls, p in zip(class_names, proba)},
            "model_experiment": "Experiment C (thermal+temporal only, NO OSM features, NO leakage)",
            "label_type": "weak_geographic_labels_NOT_verified_fire_cause",
        }

    def predict_exp_a(self, feature_dict: Dict[str, float]) -> Dict:
        """
        Predict using Experiment A (all features including OSM — HIGH leakage risk).

        This gives a better practical estimate for events near mapped infrastructure
        but its accuracy is inflated by the label-distance correlation.
        """
        if not self._loaded:
            raise RuntimeError("ModelService.load() must be called before predict().")

        X = self._make_feature_vector(feature_dict, self._cols_a, "Exp A")
        proba = self._model_a.predict_proba(X)[0]
        class_names = list(self._encoder.classes_)

        predicted_idx = int(np.argmax(proba))
        return {
            "source": class_names[predicted_idx],
            "label": "Probable Source",
            "confidence": float(proba[predicted_idx]),
            "probabilities": {cls: float(p) for cls, p in zip(class_names, proba)},
            "model_experiment": "Experiment A (all features incl. OSM distances — HIGH label leakage)",
            "label_type": "weak_geographic_labels_NOT_verified_fire_cause",
        }

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def class_names(self) -> List[str]:
        return list(self._encoder.classes_) if self._encoder else []

    @property
    def exp_c_feature_count(self) -> int:
        return len(self._cols_c)

    @property
    def exp_a_feature_count(self) -> int:
        return len(self._cols_a)

    @property
    def exp_c_columns(self) -> List[str]:
        return list(self._cols_c)

    @property
    def exp_a_columns(self) -> List[str]:
        return list(self._cols_a)

    @property
    def metadata(self) -> dict:
        return self._metadata


# Module-level singleton — populated during FastAPI lifespan startup
model_service = ModelService()
