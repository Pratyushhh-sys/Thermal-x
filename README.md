# Satellite-Based Industrial Fire & Thermal Source Attribution
## SIH 2026 — PS 26162 | Day 1: ML Pipeline + Day 2: Backend API

> **Label disclaimer**: `source_label` is a **weak geographic label** derived from OSM proximity.
> It is **NOT** verified fire-cause ground truth. All classification results are labeled
> "Probable Source", not "Confirmed Fire Cause".

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Project Structure](#2-project-structure)
3. [Quick Start](#3-quick-start)
4. [Day 2 Backend API](#4-day-2-backend-api)
5. [Data Sources](#5-data-sources)
6. [Label Methodology & Weak Labels](#6-label-methodology--weak-labels)
7. [Feature Engineering](#7-feature-engineering)
8. [Temporal Persistence Features](#8-temporal-persistence-features)
9. [Train/Test Methodology](#9-traintest-methodology)
10. [Data Leakage Investigation](#10-data-leakage-investigation)
11. [Model & Evaluation](#11-model--evaluation)
12. [Saved Artifacts](#12-saved-artifacts)
13. [Known Limitations](#13-known-limitations)
14. [Reproduction Commands](#14-reproduction-commands)
15. [Configuration Reference](#15-configuration-reference)

---

## 4. Day 2 Backend API

### Architecture

```
backend/
├── main.py                         FastAPI app factory, lifespan loader
├── api/
│   ├── events.py                   GET /api/events, GET /api/events/{id}
│   ├── health.py                   GET /api/health
│   └── summary.py                  GET /api/summary
├── services/
│   ├── model_service.py            Singleton model loader (Exp C + Exp A)
│   ├── event_service.py            Pre-computed feature CSV loader
│   ├── classification_service.py   Dual-prediction wrapper
│   ├── osm_service.py              OSM cache BallTree query service
│   ├── persistence_service.py      7-day temporal feature extraction
│   ├── risk_service.py             4-factor risk engine (SIH spec)
│   └── explanation_service.py      Human-readable reason generator
├── schemas/
│   └── event_schema.py             Pydantic v2 response models
└── tests/
    └── test_api.py                 12 acceptance tests
```

### Starting the backend

```bash
# From project root:
python -m uvicorn backend.main:app --reload --port 8000

# Interactive API docs:
http://localhost:8000/docs
```

### Startup sequence (automatic)
1. Loads `source_classifier_exp_c.pkl` (Exp C — 25 features, NO leakage)
2. Loads `source_classifier.pkl` (Exp A — 39 features, HIGH leakage, contextual)
3. Loads `label_encoder.pkl` and `feature_columns_exp_c.json`
4. **Validates feature column count** — fails loudly if mismatch
5. Loads 20,828-event feature CSV into memory (~20 MB)
6. Loads OSM feature cache BallTrees (9/10 types)
7. API ready in ~15 seconds

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Model, dataset, OSM cache status |
| `GET` | `/api/summary` | Dataset-wide statistics |
| `GET` | `/api/events` | Paginated event list (`?limit=`, `?offset=`, `?source=`, `?min_frp=`) |
| `GET` | `/api/events/{id}` | Full intelligence pipeline for one event |
| `GET` | `/docs` | Interactive Swagger UI |

### Full event intelligence pipeline (`/api/events/{id}`)

```
Event ID → Feature row → Persistence → OSM context → Classify (Exp C + A)
         → Risk score → Explanation → Final JSON
```

Response includes:
- **`firms`**: FRP, brightness, satellite, acquisition date
- **`persistence`**: 7-day active days, ratio, FRP stats, trend label
- **`gis_context`**: nearest infrastructure per type (10 OSM categories), 100/500/1000 m buffers
- **`classification`**: dual prediction — `thermal_only_estimate` (Exp C, no leakage) + `contextual_estimate` (Exp A)
- **`risk`**: composite score (0-100), tier (HIGH/MEDIUM/LOW), 4-factor components, human-readable reasons
- **`metadata`**: model used, label type disclaimer, observation window

### Risk formula (SIH specification — weights fixed)

```
thermal_score     = min(100, FRP / 150 * 100)
persistence_score = active_days_last_7 / 7 * 100
osm_score         = 100 / 85 / 60 / 35 / 15  (≤100m / 100-500m / 500-1000m / 1-2km / >2km)
ai_score          = classification_confidence * 100

risk = 0.30 × thermal + 0.30 × persistence + 0.20 × osm + 0.20 × ai

HIGH ≥ 70  |  MEDIUM 45-69.99  |  LOW < 45
```

### Running tests

```bash
pytest backend/tests/test_api.py -v --asyncio-mode=auto
# Expected: 12 passed
```

### Verified smoke test result (TH00100)

```
lat/lon:   8.616, 80.644  (southern India)
frp:       2.21 MW
trend:     intermittent (1 of 7 days)
[Exp C]:   Other  conf=0.918
[Exp A]:   Other  conf=0.854
risk:      26.09  LOW
  thermal: 1.47  persistence: 14.29  osm: 15.0  ai: 91.83
```

---

## 1. Project Overview

This pipeline processes **NASA FIRMS VIIRS** active-fire satellite observations for the Indian subcontinent and attempts to classify each thermal hotspot as one of five source types:

| Class | Description |
|---|---|
| **Industrial** | Factory, refinery, chemical plant, gas works |
| **Mining** | Coal mine, open-cast mine, quarry |
| **Agricultural** | Crop residue burning, agricultural land |
| **Forest** | Forest or woodland fire |
| **Other** | Unclassified or mixed context |

### What this is NOT
- This is NOT a real-time detection system (no live inference today)
- Labels are **weak geographic labels**, not verified fire-cause ground truth
- This is a research/proof-of-concept pipeline for SIH 2026

---

## 2. Project Structure

```
thermal-source-attribution/
│
├── data/
│   ├── raw/
│   │   ├── firms_viirs_raw.csv          # Unmodified FIRMS download
│   │   └── osm_cache/                   # Cached Overpass API results
│   ├── processed/
│   │   └── firms_viirs_clean.csv        # Cleaned, normalized FIRMS data
│   └── features/
│       ├── source_classification_features.csv  # Final ML feature table
│       └── dataset_summary.json         # Data quality report
│
├── ml/
│   ├── data_collection/
│   │   └── firms_client.py              # FIRMS API + local file client
│   ├── preprocessing/
│   │   └── clean_data.py                # VIIRS data cleaning
│   ├── feature_engineering/
│   │   ├── osm_enrichment.py            # Overpass/OSM geospatial features
│   │   ├── label_events.py              # Weak label assignment
│   │   ├── temporal_features.py         # 7-day persistence features
│   │   └── build_features.py            # Full pipeline assembler
│   ├── training/
│   │   └── train_model.py               # XGBoost training (2 experiments)
│   └── evaluation/
│       └── evaluate_model.py            # Metrics, confusion matrix, SHAP
│
├── models/
│   ├── source_classifier.pkl            # XGBoost model (all features)
│   ├── source_classifier_no_distances.pkl  # Model without distance features
│   ├── label_encoder.pkl                # Sklearn LabelEncoder
│   ├── feature_columns.json             # Ordered feature names (Exp A)
│   ├── feature_columns_no_distances.json   # Feature names (Exp B)
│   ├── model_metadata.json              # Full training metadata + metrics
│   ├── leakage_report.json              # Data leakage diagnostic
│   └── plots/                           # Confusion matrices, feature importance
│
├── scripts/
│   ├── download_firms_data.py           # Stage 1 entry point
│   └── run_ml_pipeline.py              # Full pipeline orchestrator
│
├── notebooks/                           # (reserved for future EDA)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Quick Start

### Install dependencies
```bash
pip install -r requirements.txt
```

### Configure environment
```bash
cp .env.example .env
# Edit .env and set FIRMS_MAP_KEY or FIRMS_LOCAL_FILE
```

### Run complete pipeline
```bash
python scripts/run_ml_pipeline.py
```

### Run stages individually
```bash
# Stage 1: Download FIRMS data
python scripts/download_firms_data.py

# Stage 2: Build features (OSM + temporal + labels)
python ml/feature_engineering/build_features.py

# Stage 3: Train and evaluate model
python ml/training/train_model.py
```

### Options
```bash
# Use a custom persistence radius (default: 1.0 km)
python scripts/run_ml_pipeline.py --radius-km 2.0

# Skip already-completed stages
python scripts/run_ml_pipeline.py --skip-download
python scripts/run_ml_pipeline.py --skip-download --skip-features

# Force re-query of Overpass OSM cache
python scripts/run_ml_pipeline.py --force-osm-refresh

# Skip weather enrichment (faster)
python scripts/run_ml_pipeline.py --skip-weather
```

---

## 4. Data Sources

### Primary: NASA FIRMS VIIRS

| Property | Value |
|---|---|
| **Source** | NASA Fire Information for Resource Management System |
| **Instrument** | VIIRS (Visible Infrared Imaging Radiometer Suite) |
| **Satellites** | NOAA-20 (primary), Suomi-NPP |
| **Dataset** | VIIRS_NOAA20_NRT, VIIRS_SNPP_NRT |
| **API** | https://firms.modaps.eosdis.nasa.gov/api/ |
| **Key required** | Yes — free registration at the link above |
| **Target region** | India (bbox: 67°E, 6°N, 98°E, 37°N) |

**VIIRS fields used:**

| Field | Description |
|---|---|
| `latitude`, `longitude` | Hotspot centroid (degrees) |
| `bright_ti4` | Brightness temperature Band I4 (~3.7 µm, Kelvin) |
| `bright_ti5` | Brightness temperature Band I5 (~11 µm, Kelvin) |
| `frp` | Fire Radiative Power (MW) |
| `scan`, `track` | Along-scan and along-track pixel size (km) |
| `acq_date`, `acq_time` | Acquisition UTC date and time (HHMM) |
| `satellite` | Sensor platform |
| `confidence` | Detection confidence: l/n/h (low/nominal/high) |
| `daynight` | D (day) or N (night) |

### Fallback: Locally downloaded FIRMS archive
If no MAP_KEY is available:
1. Visit https://firms.modaps.eosdis.nasa.gov/download/
2. Download VIIRS CSV for your region and date range
3. Set `FIRMS_LOCAL_FILE=/path/to/downloaded.csv` in `.env`

**Data is never fabricated under any code path.**

### Geospatial Context: OpenStreetMap (Overpass API)
- Free public API: https://overpass-api.de/
- No key required
- Results cached to `data/raw/osm_cache/` — re-used on subsequent runs

---

## 5. Label Methodology & Weak Labels

> ⚠️ **IMPORTANT**: Labels in this dataset are **weak geographic labels**.
> They are derived from spatial proximity to mapped infrastructure.
> They are NOT verified fire-cause determinations.

### How labels are assigned

Each FIRMS event is checked against OpenStreetMap features in priority order:

```
Priority 1 → Industrial
  Condition: distance to nearest industrial/factory/refinery/chemical/gas < 2 km

Priority 2 → Mining
  Condition: distance to nearest mine/quarry < 2 km

Priority 3 → Forest
  Condition: distance to nearest forest/woodland < 1 km

Priority 4 → Agricultural
  Condition: distance to nearest farmland/cropland < 2 km

Priority 5 → Other
  Condition: none of the above met
```

Thresholds are configurable via `.env` (`LABEL_INDUSTRIAL_KM`, etc.).

### Why these are weak labels

1. **Proximity ≠ cause**: A thermal event 1.5 km from a refinery might be a grass fire.
2. **OSM completeness**: OSM coverage varies. Rural and tribal mining areas in India may be unmapped.
3. **Temporal mismatch**: OSM reflects current mapped state, not necessarily what existed at the time of the fire.
4. **Overlap**: An area can be near both cropland and forest — the priority ordering is a heuristic.

### The label rationale column
The feature table includes a `label_rationale` column (e.g., `industrial_proximity_1.23km`) that records exactly why each label was assigned. This supports auditing and debugging.

---

## 6. Feature Engineering

### Event Information
| Feature | Source | Notes |
|---|---|---|
| `latitude`, `longitude` | FIRMS | Hotspot centroid |
| `acq_date` | FIRMS | Acquisition date |
| `hour` | FIRMS | UTC acquisition hour |
| `month` | FIRMS | Calendar month |
| `day_night` | FIRMS | 1=day, 0=night |

### Thermal Features
| Feature | Source | Notes |
|---|---|---|
| `frp` | FIRMS | Fire Radiative Power (MW) |
| `brightness` | FIRMS | Band I4 brightness temp (K) |
| `brightness_ti5` | FIRMS | Band I5 brightness temp (K) |
| `brightness_diff` | Derived | I4 − I5 (fire characterization) |
| `confidence_numeric` | FIRMS | Encoded: l=0, n=1, h=2 |
| `scan`, `track` | FIRMS | Pixel geometry |

### Temporal Persistence Features
*(See Section 7 for full methodology)*

| Feature | Description |
|---|---|
| `active_days_last_7` | Distinct days with nearby detections in last 7 days |
| `persistence_ratio` | `active_days_last_7 / 7` |
| `observation_count_last_7` | Total nearby detections in window |
| `avg_frp` | Mean FRP of nearby events |
| `max_frp` | Maximum FRP in window |
| `min_frp` | Minimum FRP in window |
| `frp_trend` | Linear slope of FRP over time (MW/day) |
| `frp_std` | Standard deviation of FRP |
| `night_count`, `day_count` | Day/night detection breakdown |

### Geospatial Features (OSM-derived)
| Feature | Description |
|---|---|
| `distance_to_industrial` | Haversine km to nearest industrial OSM feature |
| `distance_to_factory` | Haversine km to nearest factory |
| `distance_to_chemical` | Haversine km to nearest chemical facility |
| `distance_to_refinery` | Haversine km to nearest refinery |
| `distance_to_gas` | Haversine km to nearest gas works |
| `distance_to_mine` | Haversine km to nearest mine |
| `distance_to_quarry` | Haversine km to nearest quarry |
| `distance_to_pipeline` | Haversine km to nearest pipeline |
| `distance_to_forest` | Haversine km to nearest forest |
| `distance_to_cropland` | Haversine km to nearest cropland |
| `near_*` | Binary: within 2 km (True/False) |
| `dominant_context` | Categorical: dominant land-cover type |

> ⚠️ **Leakage note**: `distance_to_*` features directly encode the labeling logic. See Section 9.

### Weather Features (Optional)
Source: Open-Meteo Historical ERA5 (free, no key)

| Feature | Description |
|---|---|
| `temperature` | 2m temperature (°C) at noon UTC |
| `humidity` | Relative humidity (%) |
| `wind_speed` | 10m wind speed (km/h) |
| `wind_direction` | 10m wind direction (degrees) |

Weather features may be largely NaN if Open-Meteo was unreachable. The pipeline continues without them.

---

## 7. Temporal Persistence Features

### Why persistence matters
Industrial and mining sources tend to produce **persistent** thermal anomalies over days or weeks. Agricultural burns are shorter. Forest fires may last several days. This temporal pattern is a strong discriminator.

### Spatial matching strategy

**Key design decision**: We do NOT require exact (lat, lon) match between observations. Satellite repeat-pass geometry slightly shifts the observed centroid even for the same physical source.

Instead, we use **configurable Haversine spatial matching**:

```
For each event E at time T:
  Find all events within radius R of E's location
  in the time window [T - 7 days, T)

  R = PERSISTENCE_RADIUS_KM (default: 1.0 km)
```

The default 1.0 km radius captures the same physical site across satellite overpasses. This is configurable:

```bash
# Default: 1 km radius
python scripts/run_ml_pipeline.py --radius-km 1.0

# Sensitivity test: broader radius
python scripts/run_ml_pipeline.py --radius-km 3.0
```

### Algorithm
- **Small datasets** (<30,000 events): event-by-event BallTree query
- **Large datasets** (≥30,000 events): chunked daily-window algorithm (faster)
- Uses `sklearn.neighbors.BallTree` with Haversine metric
- FRP trend calculated via `scipy.stats.linregress` on matched events

---

## 8. Train/Test Methodology

### Spatial train/test split

We use **geographic region holdout** instead of random split.

```
Training set : Events where latitude ≥ 15.0° N
Test set     : Events where latitude < 15.0° N (southern India)
```

**Why not random split?**
Random splitting of spatially autocorrelated data causes leakage: events from the same fire cluster appear in both train and test sets. A model can "remember" spatial neighbours rather than learning generalizable patterns.

Geographic holdout gives a more honest estimate of how the model performs on an entirely unseen region.

### Class balancing
Class imbalance is handled via `sklearn.utils.class_weight.compute_sample_weight("balanced")`, applied during XGBoost training. This avoids the majority-class bias problem without oversampling (which can introduce its own artefacts).

---

## 9. Data Leakage Investigation

> This is a deliberately transparent investigation. Results are not hidden.

### The leakage risk

Because `source_label` is derived from `distance_to_*` features, and those same distance features are also used as model inputs:

```
source_label = f(distance_to_industrial, distance_to_mine, ...)
model_input  = [distance_to_industrial, distance_to_mine, ..., frp, ...]
```

A model trained on all features may simply learn "Industrial = small distance_to_industrial" — this is not meaningful generalisation.

### Two-experiment design

| | Experiment A | Experiment B |
|---|---|---|
| **Features** | All features including `distance_to_*` | Thermal + temporal only (no distance/proximity) |
| **Purpose** | Upper-bound, shows full-feature performance | Honest benchmark — tests genuine thermal/temporal learning |
| **Leakage risk** | High (distance features ≈ labels) | Low |
| **Use case** | Reference; production if distances are trusted | Conservative deployment; new geographies |

Both results are reported in `models/model_metadata.json` and `models/leakage_report.json`.

### Interpretation rules
- If `Acc(A) - Acc(B) > 10 pp` → significant leakage confirmed; use B as benchmark
- If `Acc(A) - Acc(B) < 10 pp` → distance features provide legitimate context beyond labeling
- We **never optimize model hyperparameters** by peeking at test results

---

## 10. Model & Evaluation

### Model: XGBoost (`multi:softprob`)

| Hyperparameter | Value | Rationale |
|---|---|---|
| `n_estimators` | 300 | Sufficient for most datasets; not over-large |
| `max_depth` | 6 | Moderate — prevents overfitting on small data |
| `learning_rate` | 0.05 | Conservative — better generalisation |
| `subsample` | 0.8 | Stochastic gradient — reduces variance |
| `colsample_bytree` | 0.8 | Feature subsampling |
| `min_child_weight` | 5 | Prevents splits on very small leaf nodes |
| `reg_alpha` | 0.1 | L1 regularisation |
| `reg_lambda` | 1.0 | L2 regularisation |

### Evaluation metrics reported
- Accuracy
- Macro F1 (primary benchmark — treats all classes equally)
- Weighted F1
- Per-class: Precision, Recall, F1, Support
- Confusion matrix (raw counts + row-normalized)
- Feature importance (XGBoost gain-based)
- SHAP mean |SHAP| per feature (if SHAP installed)

### Performance honesty
- If macro F1 > 0.90 in Experiment A but < 0.70 in Experiment B → flag leakage
- If macro F1 is poor in both → reported honestly; likely causes: insufficient data, OSM coverage gaps, inherent ambiguity in geographic labeling

---

## 11. Saved Artifacts

| File | Description |
|---|---|
| `models/source_classifier.pkl` | Trained XGBoost (Experiment A, all features) |
| `models/source_classifier_no_distances.pkl` | XGBoost (Experiment B, no distance features) |
| `models/label_encoder.pkl` | Sklearn LabelEncoder for decoding predictions |
| `models/feature_columns.json` | Ordered feature list for Exp A inference |
| `models/feature_columns_no_distances.json` | Ordered feature list for Exp B inference |
| `models/model_metadata.json` | Training date, metrics, feature count, limitations |
| `models/leakage_report.json` | Side-by-side leakage experiment results |
| `models/plots/` | Confusion matrices, feature importance, SHAP |
| `data/features/source_classification_features.csv` | Full feature table |
| `data/features/dataset_summary.json` | Data quality report |

### Loading for inference
```python
import pickle, json
import pandas as pd

with open("models/source_classifier.pkl", "rb") as f:
    model = pickle.load(f)
with open("models/label_encoder.pkl", "rb") as f:
    le = pickle.load(f)
with open("models/feature_columns.json") as f:
    feature_cols = json.load(f)

# Prepare input DataFrame with same columns in same order
X_new = df[feature_cols]
preds_int = model.predict(X_new)
preds_labels = le.inverse_transform(preds_int)
```

---

## 12. Known Limitations

1. **Weak labels** — Labels are geographic heuristics, not verified fire-cause records. No ground-truth dataset exists for Indian fire cause attribution at scale.

2. **OSM completeness** — Industrial and mining infrastructure in rural/tribal areas of India is significantly under-mapped in OpenStreetMap. Missing features produce large sentinel distances (999 km), which may push events incorrectly to "Other".

3. **Temporal window** — Temporal persistence is computed from the available FIRMS data window (NRT: 10 days). Longer-term patterns (seasonal variation, multi-week persistence) are not captured.

4. **Label-distance leakage** — The same proximity logic used to assign labels is present in model input features. Experiment B quantifies this. Both results are reported transparently.

5. **Spatial split limitation** — Geographic holdout reduces spatial leakage but does not eliminate it if the test region has similar infrastructure density to the training region.

6. **Weather features** — May be largely NaN if Open-Meteo was unavailable or rate-limited. Weather enrichment is modular and non-blocking.

7. **Single-satellite time window** — VIIRS NRT gives ~10 days. Archive download from FIRMS can provide multi-year data for more robust persistence features.

8. **No Sentinel-2 integration** — Optical/SWIR contextual features from Sentinel-2 are out of scope for Day 1. This is a planned future enhancement.

---

## 13. Reproduction Commands

```bash
# 0. Install dependencies
pip install -r requirements.txt

# 1. Configure (set FIRMS_MAP_KEY or FIRMS_LOCAL_FILE)
cp .env.example .env
nano .env

# 2. Full pipeline (all stages)
python scripts/run_ml_pipeline.py

# — OR — run stages individually:

# 2a. Download FIRMS data
python scripts/download_firms_data.py

# 2b. Build feature table
python ml/feature_engineering/build_features.py

# 2c. Train and evaluate model
python ml/training/train_model.py

# Sensitivity testing: wider persistence radius
python scripts/run_ml_pipeline.py --skip-download --radius-km 3.0

# Skip weather enrichment for speed
python scripts/run_ml_pipeline.py --skip-weather

# Use southern India test boundary at 12° instead of 15°
python ml/training/train_model.py --split-lat 12.0

# Force re-query of all OSM data (bypasses cache)
python ml/feature_engineering/build_features.py --force-osm-refresh
```

---

## 14. Configuration Reference

Set these in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `FIRMS_MAP_KEY` | — | NASA FIRMS API key (free) |
| `FIRMS_LOCAL_FILE` | — | Path to local FIRMS CSV (fallback) |
| `FIRMS_BBOX` | `67,6,98,37` | Bounding box W,S,E,N (India) |
| `FIRMS_DAYS` | `10` | NRT lookback days |
| `FIRMS_DATASET` | `VIIRS_NOAA20_NRT` | FIRMS dataset name |
| `PERSISTENCE_RADIUS_KM` | `1.0` | Haversine radius for temporal features |
| `OSM_CACHE_DIR` | `data/raw/osm_cache` | Overpass cache directory |
| `LABEL_INDUSTRIAL_KM` | `2.0` | Industrial label proximity threshold |
| `LABEL_MINING_KM` | `2.0` | Mining label proximity threshold |
| `LABEL_FOREST_KM` | `1.0` | Forest label proximity threshold |
| `LABEL_AGRICULTURAL_KM` | `2.0` | Agricultural label proximity threshold |
| `SPATIAL_SPLIT_LAT` | `15.0` | Latitude boundary for test set |
| `RANDOM_SEED` | `42` | Reproducibility seed |

---

*SIH 2026 | PS 26162 | Day 1 ML Pipeline | Data → Features → Model*
