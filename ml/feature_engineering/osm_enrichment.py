"""
ml/feature_engineering/osm_enrichment.py
==========================================
OpenStreetMap / Overpass API Geospatial Enrichment

For each FIRMS thermal event this module calculates:
  - Haversine distance (km) to nearest feature of each type:
      industrial, factory, chemical, refinery, gas, mine, quarry,
      pipeline, forest, cropland/agricultural
  - Binary proximity flags (within threshold km)
  - Dominant land-cover context label (for use by labeling module)

Data source: OpenStreetMap via Overpass API (public, no key required).

Rate-limiting strategy:
  - Results are cached per query to data/raw/osm_cache/ as JSON.
  - Cached results are loaded on subsequent runs without re-querying.
  - Queries are batched by feature type over the full bounding box.
  - Exponential back-off on HTTP 429 / 504 responses.

IMPORTANT: OSM data reflects the mapped state of the world and may be
incomplete, especially in rural or unmapped areas. Missing features mean
infinite distance — this is preserved in the feature as a large sentinel
value (DEFAULT_MAX_DIST_KM) rather than silently dropped.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from sklearn.neighbors import BallTree
from tqdm import tqdm

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT = 300            # seconds per Overpass query
OVERPASS_RETRY_DELAYS = [5, 15, 60]  # back-off seconds on failure

OSM_CACHE_DIR = Path(os.getenv("OSM_CACHE_DIR", "data/raw/osm_cache"))

# Sentinel distance for features with NO OSM matches in the area
DEFAULT_MAX_DIST_KM = 999.0

EARTH_RADIUS_KM = 6371.0


# ---------------------------------------------------------------------------
# OSM Feature Type Definitions
# ---------------------------------------------------------------------------
# Each entry is (feature_key, overpass_query_tag_clause, description)
OSM_FEATURE_TYPES: Dict[str, dict] = {
    "industrial": {
        "description": "Industrial areas (factories, plants, facilities)",
        "query_tags": [
            '["landuse"="industrial"]',
            '["industrial"~"factory|manufacturing|plant"]',
        ],
    },
    "factory": {
        "description": "Factories and manufacturing plants",
        "query_tags": [
            '["man_made"="works"]',
            '["building"="industrial"]',
            '["industrial"="factory"]',
        ],
    },
    "chemical": {
        "description": "Chemical plants and facilities",
        "query_tags": [
            '["industrial"="chemical"]',
            '["industrial"~"chemical|petrochemical"]',
        ],
    },
    "refinery": {
        "description": "Oil and gas refineries",
        "query_tags": [
            '["industrial"~"oil|refinery|petroleum"]',
            '["man_made"~"petroleum_well|storage_tank"]',
        ],
    },
    "gas": {
        "description": "Gas works and facilities",
        "query_tags": [
            '["industrial"="gas"]',
            '["man_made"="gas_works"]',
            '["landuse"="gas"]',
        ],
    },
    "mine": {
        "description": "Mines (coal, ore, etc.)",
        "query_tags": [
            '["industrial"="mine"]',
            '["landuse"="quarry"]["quarry"="yes"]',
            '["industrial"~"mine|coal_mine|iron_mine"]',
        ],
    },
    "quarry": {
        "description": "Quarries and open-pit excavations",
        "query_tags": [
            '["landuse"="quarry"]',
            '["industrial"="quarry"]',
        ],
    },
    "pipeline": {
        "description": "Oil and gas pipelines",
        "query_tags": [
            '["man_made"="pipeline"]',
        ],
    },
    "forest": {
        "description": "Forest and woodland areas",
        "query_tags": [
            '["landuse"="forest"]',
            '["natural"="wood"]',
            '["landuse"="nature_reserve"]',
        ],
    },
    "cropland": {
        "description": "Agricultural and crop land",
        "query_tags": [
            '["landuse"="farmland"]',
            '["landuse"~"farmyard|orchard|vineyard|plant_nursery"]',
            '["landuse"="crop"]',
        ],
    },
}


# ---------------------------------------------------------------------------
# Overpass Querying
# ---------------------------------------------------------------------------
def _build_overpass_query(tag_clause: str, bbox: str, timeout: int = OVERPASS_TIMEOUT) -> str:
    """
    Build an Overpass QL query that returns nodes and way centroids.

    bbox format (for Overpass): south,west,north,east
    """
    return f"""
[out:json][timeout:{timeout}];
(
  node{tag_clause}({bbox});
  way{tag_clause}({bbox});
);
out center;
""".strip()


OVERPASS_HEADERS = {
    "User-Agent": "ThermalSourceAttribution/1.0 SIH2026-PS26162 (academic research)",
    "Accept": "application/json",
}


def _query_overpass(query: str, retries: int = 3) -> dict:
    """Submit an Overpass QL query with exponential back-off on failure."""
    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                OVERPASS_URL,
                data={"data": query},
                headers=OVERPASS_HEADERS,
                timeout=OVERPASS_TIMEOUT + 30,
            )
            if resp.status_code == 429 or resp.status_code == 504:
                delay = OVERPASS_RETRY_DELAYS[min(attempt, len(OVERPASS_RETRY_DELAYS) - 1)]
                logger.warning("Overpass rate-limited (%d). Waiting %ds…", resp.status_code, delay)
                time.sleep(delay)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            if attempt < retries:
                delay = OVERPASS_RETRY_DELAYS[min(attempt, len(OVERPASS_RETRY_DELAYS) - 1)]
                logger.warning("Overpass request failed (attempt %d/%d): %s. Retrying in %ds…",
                               attempt + 1, retries, exc, delay)
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Overpass query failed after all retries.")


def _extract_coords_from_overpass(result: dict) -> np.ndarray:
    """
    Extract (lat, lon) from Overpass JSON result.
    Handles both nodes (lat/lon directly) and ways (via 'center').
    Returns ndarray of shape (N, 2).
    """
    coords = []
    for element in result.get("elements", []):
        if element["type"] == "node":
            coords.append((element["lat"], element["lon"]))
        elif element["type"] == "way" and "center" in element:
            coords.append((element["center"]["lat"], element["center"]["lon"]))
    return np.array(coords) if coords else np.empty((0, 2))


def fetch_osm_features(
    feature_type: str,
    bbox_overpass: str,  # format: south,west,north,east
    force_refresh: bool = False,
) -> np.ndarray:
    """
    Fetch OSM feature coordinates for a given feature type.

    Uses disk cache. Returns array of shape (N, 2) with [lat, lon] rows.

    Parameters
    ----------
    feature_type : str
        Key into OSM_FEATURE_TYPES dict.
    bbox_overpass : str
        Overpass bounding box string: 'south,west,north,east'
    force_refresh : bool
        If True, bypass cache and re-query Overpass.

    Returns
    -------
    np.ndarray of shape (N, 2) — latitude, longitude for each feature.
    """
    if feature_type not in OSM_FEATURE_TYPES:
        raise ValueError(f"Unknown feature type: {feature_type}")

    cache_file = OSM_CACHE_DIR / f"{feature_type}_{bbox_overpass.replace(',', '_')}.json"

    # Load from cache
    if cache_file.exists() and not force_refresh:
        logger.debug("OSM cache hit: %s", cache_file)
        with open(cache_file) as f:
            data = json.load(f)
        return np.array(data["coords"]) if data["coords"] else np.empty((0, 2))

    # Query Overpass
    ftype = OSM_FEATURE_TYPES[feature_type]
    all_coords = []

    for tag_clause in ftype["query_tags"]:
        query = _build_overpass_query(tag_clause, bbox_overpass)
        try:
            logger.info("Querying Overpass: %s %s", feature_type, tag_clause)
            result = _query_overpass(query)
            coords = _extract_coords_from_overpass(result)
            if len(coords) > 0:
                all_coords.append(coords)
            # Rate-limit courtesy delay
            time.sleep(2)
        except Exception as exc:
            logger.warning("OSM query failed for %s / %s: %s", feature_type, tag_clause, exc)

    combined = np.vstack(all_coords) if all_coords else np.empty((0, 2))

    # Deduplicate (round to 5 decimal places ≈ 1 m)
    if len(combined) > 0:
        combined = np.unique(np.round(combined, 5), axis=0)

    # Save cache
    OSM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump({"feature_type": feature_type, "bbox": bbox_overpass,
                   "count": len(combined), "coords": combined.tolist()}, f)

    logger.info("OSM %s: %d features found, cached to %s", feature_type, len(combined), cache_file)
    return combined


# ---------------------------------------------------------------------------
# BallTree Nearest-Neighbour Lookup
# ---------------------------------------------------------------------------
def build_balltree(coords_latlon: np.ndarray) -> Optional[BallTree]:
    """Build a BallTree with Haversine metric for fast nearest-neighbor search."""
    if len(coords_latlon) == 0:
        return None
    coords_rad = np.radians(coords_latlon)
    return BallTree(coords_rad, metric="haversine")


def nearest_distance_km(
    tree: Optional[BallTree],
    query_lats: np.ndarray,
    query_lons: np.ndarray,
) -> np.ndarray:
    """
    Return Haversine distance in km from each query point to its nearest
    feature in `tree`.

    If `tree` is None (no OSM features found), returns DEFAULT_MAX_DIST_KM
    for all query points — this preserves the "no features mapped" signal
    without silently introducing zeros.

    Parameters
    ----------
    tree : BallTree or None
    query_lats, query_lons : array-like of shape (N,)

    Returns
    -------
    distances_km : np.ndarray of shape (N,)
    """
    n = len(query_lats)
    if tree is None:
        logger.debug("No OSM features available; returning sentinel distance %.1f km", DEFAULT_MAX_DIST_KM)
        return np.full(n, DEFAULT_MAX_DIST_KM)

    query_rad = np.radians(np.column_stack([query_lats, query_lons]))
    dist_rad, _ = tree.query(query_rad, k=1)
    return dist_rad[:, 0] * EARTH_RADIUS_KM


# ---------------------------------------------------------------------------
# Main Enrichment Function
# ---------------------------------------------------------------------------
def enrich_with_osm(
    df: pd.DataFrame,
    bbox_firms: str = "67,6,98,37",   # FIRMS format: W,S,E,N
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Add geospatial distance features to a cleaned FIRMS DataFrame.

    For each feature type in OSM_FEATURE_TYPES, adds:
      - distance_to_{type}   (float, km)
      - near_{type}          (bool, within 2 km default)

    Also adds a 'dominant_context' column for use by the labeling module.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned FIRMS data with 'latitude' and 'longitude' columns.
    bbox_firms : str
        Bounding box in FIRMS API format: 'W,S,E,N'
    force_refresh : bool
        Bypass OSM cache and re-query Overpass.

    Returns
    -------
    pd.DataFrame
        Input DataFrame with additional distance columns.
    """
    df = df.copy()

    # Convert FIRMS bbox (W,S,E,N) → Overpass bbox (S,W,N,E)
    parts = [float(x) for x in bbox_firms.split(",")]
    w, s, e, n = parts
    bbox_overpass = f"{s},{w},{n},{e}"

    lats = df["latitude"].values
    lons = df["longitude"].values

    logger.info("OSM enrichment: processing %d events over bbox %s", len(df), bbox_overpass)

    trees: Dict[str, Optional[BallTree]] = {}
    feature_coords: Dict[str, np.ndarray] = {}

    # ── Fetch and index all feature types ────────────────────────────────
    for ftype in tqdm(OSM_FEATURE_TYPES.keys(), desc="Fetching OSM features"):
        try:
            coords = fetch_osm_features(ftype, bbox_overpass, force_refresh=force_refresh)
            feature_coords[ftype] = coords
            trees[ftype] = build_balltree(coords)
        except Exception as exc:
            logger.error("Failed to fetch OSM features for %s: %s. Using sentinel distances.", ftype, exc)
            feature_coords[ftype] = np.empty((0, 2))
            trees[ftype] = None

    # ── Calculate distances ───────────────────────────────────────────────
    logger.info("Calculating nearest-neighbor distances for %d events…", len(df))

    for ftype, tree in tqdm(trees.items(), desc="Calculating distances"):
        col_dist = f"distance_to_{ftype}"
        col_near = f"near_{ftype}"
        distances = nearest_distance_km(tree, lats, lons)
        df[col_dist] = distances
        df[col_near] = distances < 2.0   # 2 km proximity flag

    # ── Dominant context (for labeling) ──────────────────────────────────
    df["dominant_context"] = _assign_dominant_context(df)

    logger.info("OSM enrichment complete.")
    return df


def _assign_dominant_context(df: pd.DataFrame) -> pd.Series:
    """
    Determine the dominant land-cover context based on OSM distances.
    Priority: industrial > mining (quarry+mine) > forest > cropland > other.
    """
    contexts = []
    for _, row in df.iterrows():
        dist_ind = min(row.get("distance_to_industrial", 999),
                       row.get("distance_to_factory", 999),
                       row.get("distance_to_refinery", 999),
                       row.get("distance_to_chemical", 999),
                       row.get("distance_to_gas", 999))
        dist_mine = min(row.get("distance_to_mine", 999),
                        row.get("distance_to_quarry", 999))
        dist_forest = row.get("distance_to_forest", 999)
        dist_crop = row.get("distance_to_cropland", 999)

        if dist_ind < dist_mine and dist_ind < dist_forest and dist_ind < dist_crop:
            contexts.append("industrial_context")
        elif dist_mine < dist_forest and dist_mine < dist_crop:
            contexts.append("mining_context")
        elif dist_forest < dist_crop:
            contexts.append("forest_context")
        elif dist_crop < 999:
            contexts.append("agricultural_context")
        else:
            contexts.append("other_context")

    return pd.Series(contexts, index=df.index)
