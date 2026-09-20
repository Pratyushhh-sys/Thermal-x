"""
backend/services/osm_service.py
=================================
Per-event OSM geospatial context using Day 1 disk cache.

Reuses:
  ml.feature_engineering.osm_enrichment.fetch_osm_features
  ml.feature_engineering.osm_enrichment.build_balltree
  ml.feature_engineering.osm_enrichment.nearest_distance_km
  ml.feature_engineering.osm_enrichment.OSM_FEATURE_TYPES

NO new Overpass queries are made during API operation.
All data is read from the on-disk cache at data/raw/osm_cache/.

If a feature type has no cached data:
  - distance returned as None
  - buffer entries are empty for that type

The distance sentinel value (999 km) from Day 1 is converted to None
so API consumers see a clean null rather than a meaningless large number.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

# Allow importing from project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from ml.feature_engineering.osm_enrichment import (
    fetch_osm_features,
    build_balltree,
    nearest_distance_km,
    OSM_FEATURE_TYPES,
    DEFAULT_MAX_DIST_KM,
    EARTH_RADIUS_KM,
)
from backend.services.facility_service import resolve_facility_name

logger = logging.getLogger(__name__)

# Buffer radii in metres
BUFFER_RADII_M = [100, 500, 1000]
SENTINEL_KM = DEFAULT_MAX_DIST_KM  # 999.0 km — means "not found"

# Industrial/mining types that get hazard proximity bonus in risk engine
HAZARD_TYPES = {"industrial", "factory", "chemical", "refinery", "gas", "mine", "quarry", "pipeline"}


class OSMService:
    """
    Serves per-event OSM geospatial context from disk cache.
    BallTrees are loaded once at startup; no Overpass queries at runtime.
    """

    def __init__(self) -> None:
        self._trees: Dict[str, Any] = {}
        self._coords: Dict[str, np.ndarray] = {}
        self._loaded_types: List[str] = []

    def load(self, bbox_firms: str = "67,6,98,37") -> None:
        """Load cached OSM features and build BallTrees. Called once at startup."""
        # Convert FIRMS bbox W,S,E,N → Overpass S,W,N,E
        parts = [float(x) for x in bbox_firms.split(",")]
        w, s, e, n = parts
        bbox_overpass = f"{s},{w},{n},{e}"

        logger.info("Loading OSM cache for bbox %s", bbox_overpass)

        for ftype in OSM_FEATURE_TYPES:
            try:
                coords = fetch_osm_features(ftype, bbox_overpass, force_refresh=False)
                self._coords[ftype] = coords
                self._trees[ftype] = build_balltree(coords)
                if len(coords) > 0:
                    self._loaded_types.append(ftype)
                    logger.debug("OSM [%s]: %d features loaded from cache", ftype, len(coords))
                else:
                    logger.debug("OSM [%s]: no cached features", ftype)
            except Exception as exc:
                logger.warning("OSM cache load failed for [%s]: %s — will return null for this type", ftype, exc)
                self._coords[ftype] = np.empty((0, 2))
                self._trees[ftype] = None

        logger.info("OSMService ready: %d / %d types loaded from cache",
                    len(self._loaded_types), len(OSM_FEATURE_TYPES))

    def get_osm_context(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Return nearest facility for each OSM type + buffer analysis.

        Returns
        -------
        dict with keys:
          nearest_{type} → {type, name, distance_m, lat, lon} or None
          buffers        → {"100m": [...], "500m": [...], "1000m": [...]}
          nearest_hazard_distance_m → float or None
        """
        context: Dict[str, Any] = {}
        all_near: List[Dict[str, Any]] = []  # for buffer analysis

        for ftype in OSM_FEATURE_TYPES:
            tree = self._trees.get(ftype)
            coords = self._coords.get(ftype, np.empty((0, 2)))

            if tree is None or len(coords) == 0:
                context[f"nearest_{ftype}"] = None
                continue

            dist_arr = nearest_distance_km(tree, [lat], [lon])
            dist_km = float(dist_arr[0])

            if dist_km >= SENTINEL_KM:
                context[f"nearest_{ftype}"] = None
                continue

            dist_m = dist_km * 1000.0

            # Find the actual nearest coordinate for lat/lon
            near_lat, near_lon = self._nearest_coords(tree, coords, lat, lon)
            resolved = resolve_facility_name(near_lat if near_lat is not None else lat, near_lon if near_lon is not None else lon, ftype)

            facility = {
                "type": ftype,
                "name": resolved["name"],
                "distance_m": round(dist_m, 1),
                "lat": round(near_lat, 6) if near_lat is not None else None,
                "lon": round(near_lon, 6) if near_lon is not None else None,
            }
            context[f"nearest_{ftype}"] = facility
            all_near.append(facility)

        # --- Buffer analysis ---
        context["buffers"] = self._buffer_analysis(all_near)

        # --- Nearest hazard distance ---
        hazard_dists = [
            context[f"nearest_{t}"]["distance_m"]
            for t in HAZARD_TYPES
            if context.get(f"nearest_{t}") is not None
        ]
        context["nearest_hazard_distance_m"] = round(min(hazard_dists), 1) if hazard_dists else None

        return context

    def _nearest_coords(
        self, tree, coords: np.ndarray, lat: float, lon: float
    ) -> Tuple[Optional[float], Optional[float]]:
        """Return lat/lon of the nearest OSM feature."""
        try:
            query_rad = np.radians([[lat, lon]])
            dist, idx = tree.query(query_rad, k=1)
            nearest = coords[idx[0][0]]
            return float(nearest[0]), float(nearest[1])
        except Exception:
            return None, None

    def _buffer_analysis(self, facilities: List[Dict]) -> Dict[str, List[Dict]]:
        """BUG-B08: Assign facilities into EXCLUSIVE rings (not cumulative).
        
        Old behaviour: a 50m facility appeared in 100m, 500m, AND 1000m buffers.
        New behaviour: each buffer only contains facilities within THAT ring.
          - 100m  : d <= 100m
          - 500m  : 100m < d <= 500m
          - 1000m : 500m < d <= 1000m
        """
        buffers: Dict[str, List[Dict]] = {
            "100m": [],
            "500m": [],
            "1000m": [],
        }
        for f in facilities:
            d = f["distance_m"]
            item = {"type": f["type"], "name": f["name"], "distance_m": d}
            if d <= 100:
                buffers["100m"].append(item)
            elif d <= 500:
                buffers["500m"].append(item)
            elif d <= 1000:
                buffers["1000m"].append(item)

        # Sort each buffer by distance
        for key in buffers:
            buffers[key].sort(key=lambda x: x["distance_m"])

        return buffers

    @property
    def loaded_type_count(self) -> int:
        return len(self._loaded_types)

    @property
    def loaded_types(self) -> List[str]:
        return list(self._loaded_types)


# Module-level singleton
osm_service = OSMService()
