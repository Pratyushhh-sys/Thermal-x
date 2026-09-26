"""
backend/services/thermal_imagery_service.py
============================================
Service for fetching Sentinel-3 SLSTR thermal infrared imagery
from the Copernicus Data Space Ecosystem (CDSE) Process API.

Sentinel-3 SLSTR (Sea and Land Surface Temperature Radiometer):
  - Bands: S7 (3.7 um), S8 (10.85 um), S9 (12.0 um)  <- true thermal infrared
  - Resolution: ~1 km at nadir
  - Repeat cycle: ~1-2 days (two satellites: S3A + S3B)
  - Product: SL_2_LST___ (Land Surface Temperature, L2)
  - These are genuine TIR measurements, NOT the same as Sentinel-2 SWIR.

IMPORTANT SCIENTIFIC NOTE:
  Sentinel-2 L2A does NOT provide thermal infrared imagery.
  It provides visible + SWIR (up to 2.19 um). True thermal IR (>3 um)
  requires a dedicated TIR instrument such as SLSTR.

This service:
  1. Authenticates with CDSE (same OAuth as optical imagery service).
  2. Requests an SLSTR S8 (10.85 um) single-band image for the event location.
  3. Applies a scientific thermal color ramp (IRON palette).
  4. Returns image bytes + metadata (acquisition time, temperature range if available).
  5. Returns available=False with structured reason when no valid scene exists.

The +-6 hour temporal search window is configurable.
"""

import os
import time
import math
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache configuration
# ---------------------------------------------------------------------------
THERMAL_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "thermal"
THERMAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# CDSE endpoints (same auth as optical imagery service)
# ---------------------------------------------------------------------------
CDSE_TOKEN_URL    = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_PROCESS_URL  = "https://sh.dataspace.copernicus.eu/api/v1/process"

LEGACY_TOKEN_URL  = "https://services.sentinel-hub.com/oauth/token"
LEGACY_PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"

# Temporal search window around the event acquisition time (hours)
TEMPORAL_WINDOW_HOURS = 24

# Minimum image size to accept as a valid scene (bytes)
MIN_IMAGE_SIZE_BYTES = 2000


class ThermalImageryService:
    """
    Fetches genuine Sentinel-3 SLSTR thermal infrared imagery from CDSE.
    Applies a scientific IRON heatmap color ramp for visualization.
    Caches results to avoid redundant API calls.
    """

    # SLSTR evalscript - S8 band (10.85 um) with IRON heatmap
    # This requests genuine brightness temperature from SLSTR S8 (TIR)
    # and maps it to IRON color palette (black->red->orange->yellow->white).
    # Temperature range ~270-380 K covers ambient to extreme fire hotspot.
    EVALSCRIPT_SLSTR_S8_IRON = """//VERSION=3
function setup() {
  return {
    input: ["S8"],
    output: { bands: 3, sampleType: "UINT8" }
  };
}

function ironColor(t) {
  var r, g, b;
  if (t < 0.25) {
    r = t * 4.0; g = 0.0; b = 0.0;
  } else if (t < 0.50) {
    r = 1.0; g = (t - 0.25) * 4.0; b = 0.0;
  } else if (t < 0.75) {
    r = 1.0; g = 1.0; b = (t - 0.50) * 2.0;
  } else {
    r = 1.0; g = 1.0; b = 0.5 + (t - 0.75) * 2.0;
  }
  return [Math.min(1.0, r), Math.min(1.0, g), Math.min(1.0, b)];
}

function evaluatePixel(sample) {
  var bt = sample.S8;
  if (isNaN(bt) || bt <= 0) {
    return [15, 23, 42];
  }
  var T_MIN = 270.0;
  var T_MAX = 380.0;
  var t = Math.max(0, Math.min(1, (bt - T_MIN) / (T_MAX - T_MIN)));
  var color = ironColor(t);
  return [Math.round(color[0] * 255), Math.round(color[1] * 255), Math.round(color[2] * 255)];
}
"""

    def __init__(self) -> None:
        self.token: Optional[str] = None
        self.token_expiry: float = 0.0
        self.active_process_url: str = CDSE_PROCESS_URL

    def _get_credentials(self) -> Tuple[str, str]:
        client_id = os.getenv("SENTINEL_CLIENT_ID", "").strip()
        client_secret = os.getenv("SENTINEL_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            env_path = Path(__file__).resolve().parents[2] / ".env"
            if env_path.exists():
                load_dotenv(env_path, override=True)
                client_id = os.getenv("SENTINEL_CLIENT_ID", "").strip()
                client_secret = os.getenv("SENTINEL_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            raise ValueError("Sentinel Hub / CDSE credentials not configured.")
        return client_id, client_secret

    def _get_token(self) -> str:
        client_id, client_secret = self._get_credentials()
        if self.token and time.time() < self.token_expiry - 60:
            return self.token

        logger.info("Requesting CDSE OAuth token for Sentinel-3 SLSTR thermal imagery...")

        try:
            resp = requests.post(
                CDSE_TOKEN_URL,
                data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
                timeout=12,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data["access_token"]
                self.token_expiry = time.time() + data.get("expires_in", 1800)
                self.active_process_url = CDSE_PROCESS_URL
                logger.info("CDSE OAuth token acquired for thermal imagery.")
                return self.token
            logger.warning("CDSE auth failed (%s): %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning("CDSE token endpoint error: %s", e)

        try:
            resp = requests.post(
                LEGACY_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                timeout=12,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data["access_token"]
                self.token_expiry = time.time() + data.get("expires_in", 3600)
                self.active_process_url = LEGACY_PROCESS_URL
                logger.info("Legacy Sentinel Hub token acquired for thermal imagery.")
                return self.token
        except Exception as e:
            logger.error("All auth endpoints failed for thermal: %s", e)
            raise

        raise RuntimeError("Failed to obtain CDSE/Sentinel Hub OAuth token.")

    @staticmethod
    def _get_bbox(lat: float, lng: float, radius_km: float = 5.0) -> Tuple[float, float, float, float]:
        lat_offset = radius_km / 111.0
        lng_offset = (radius_km / (111.0 * math.cos(math.radians(lat)))) if lat != 0 else radius_km / 111.0
        return (lng - lng_offset, lat - lat_offset, lng + lng_offset, lat + lat_offset)

    def fetch_thermal_image(
        self,
        lat: float,
        lng: float,
        acq_date: Optional[str] = None,
        acq_time_hhmm: Optional[str] = None,
        event_id: Optional[str] = None,
        radius_km: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Fetch a Sentinel-3 SLSTR thermal image for the given event location.
        Returns a dict: available, image_bytes, source, acquisition_time,
        time_delta_minutes, metadata, reason.
        """
        # Parse event timestamp
        event_dt: datetime = datetime.now(timezone.utc).replace(tzinfo=None)
        if acq_date:
            clean = str(acq_date).strip().split("T")[0].split(" ")[0]
            try:
                event_dt = datetime.strptime(clean, "%Y-%m-%d")
                if acq_time_hhmm:
                    try:
                        t = int(acq_time_hhmm)
                        event_dt = event_dt.replace(hour=t // 100, minute=t % 100)
                    except (ValueError, TypeError):
                        pass
            except ValueError:
                logger.warning("Could not parse acq_date '%s'", acq_date)

        search_start = event_dt - timedelta(hours=TEMPORAL_WINDOW_HOURS)
        search_end   = event_dt + timedelta(hours=TEMPORAL_WINDOW_HOURS)

        # Disk cache check
        cache_key = str(event_id) if event_id else f"{lat:.4f}_{lng:.4f}_{event_dt.strftime('%Y%m%d_%H%M')}"
        cache_img  = THERMAL_CACHE_DIR / f"{cache_key}.jpg"
        cache_meta = THERMAL_CACHE_DIR / f"{cache_key}.txt"

        if cache_img.exists() and cache_img.stat().st_size > MIN_IMAGE_SIZE_BYTES and cache_meta.exists():
            logger.info("Serving thermal image from cache: %s", cache_img.name)
            try:
                meta_lines = cache_meta.read_text().splitlines()
                return {
                    "available": True,
                    "image_bytes": cache_img.read_bytes(),
                    "source": "Sentinel-3 SLSTR",
                    "acquisition_time": meta_lines[0] if meta_lines else None,
                    "time_delta_minutes": int(meta_lines[1]) if len(meta_lines) > 1 and meta_lines[1] else None,
                    "metadata": self._build_metadata(
                        meta_lines[2] if len(meta_lines) > 2 else "270 K",
                        meta_lines[3] if len(meta_lines) > 3 else "380 K",
                    ),
                    "reason": None,
                }
            except Exception as e:
                logger.warning("Error reading thermal cache: %s", e)

        # Authenticate
        try:
            token = self._get_token()
        except Exception as e:
            logger.error("Cannot authenticate for thermal imagery: %s", e)
            return self._unavailable(
                "Sentinel Hub / CDSE authentication failed. Check credentials.", event_dt=event_dt
            )

        min_lng, min_lat, max_lng, max_lat = self._get_bbox(lat, lng, radius_km)

        payload = {
            "input": {
                "bounds": {
                    "bbox": [min_lng, min_lat, max_lng, max_lat],
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "sentinel-3-slstr",
                        "dataFilter": {
                            "timeRange": {
                                "from": search_start.strftime("%Y-%m-%dT00:00:00Z"),
                                "to":   search_end.strftime("%Y-%m-%dT23:59:59Z"),
                            },
                            "mosaickingOrder": "mostRecent",
                        },
                    }
                ],
            },
            "output": {
                "width": 512,
                "height": 512,
                "responses": [{"identifier": "default", "format": {"type": "image/jpeg"}}],
            },
            "evalscript": self.EVALSCRIPT_SLSTR_S8_IRON,
        }

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            resp = requests.post(self.active_process_url, headers=headers, json=payload, timeout=25)

            if resp.status_code == 200:
                img_bytes = resp.content
                if len(img_bytes) > MIN_IMAGE_SIZE_BYTES:
                    # Extract acquisition time from headers if available
                    acq_header = resp.headers.get("X-Sentinel-Hub-Acquisition-Date")
                    scene_dt: Optional[datetime] = None
                    if acq_header:
                        try:
                            scene_dt = datetime.strptime(acq_header[:19], "%Y-%m-%dT%H:%M:%S")
                        except Exception:
                            pass

                    delta_min: Optional[int] = None
                    acq_time_str = event_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if scene_dt:
                        delta_min = int(abs((scene_dt - event_dt).total_seconds()) / 60)
                        acq_time_str = scene_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                    # Cache
                    try:
                        cache_img.write_bytes(img_bytes)
                        cache_meta.write_text(
                            "\n".join([acq_time_str, str(delta_min) if delta_min is not None else "", "270 K", "380 K"])
                        )
                    except Exception as we:
                        logger.warning("Could not write thermal cache: %s", we)

                    return {
                        "available": True,
                        "image_bytes": img_bytes,
                        "source": "Sentinel-3 SLSTR",
                        "acquisition_time": acq_time_str,
                        "time_delta_minutes": delta_min,
                        "metadata": self._build_metadata("270 K", "380 K"),
                        "reason": None,
                    }

                return self._unavailable(
                    f"No compatible Sentinel-3 SLSTR scene found within +-{TEMPORAL_WINDOW_HOURS} hours of the event timestamp.",
                    event_dt=event_dt,
                )

            elif resp.status_code == 400:
                err = resp.text[:300]
                logger.warning("SLSTR Process API 400: %s", err)
                if "no data" in err.lower() or "no scenes" in err.lower():
                    return self._unavailable(
                        f"No Sentinel-3 SLSTR scene in +-{TEMPORAL_WINDOW_HOURS}h window.", event_dt=event_dt
                    )
                return self._unavailable(
                    "Sentinel-3 SLSTR data requires Copernicus Data Space access with Sentinel-3 tier. "
                    "Current credentials may cover Sentinel-2 only. Optical imagery (Sentinel-2 L2A) remains available.",
                    event_dt=event_dt,
                )

            elif resp.status_code == 403:
                return self._unavailable(
                    "Access denied for Sentinel-3 SLSTR. The current subscription may not include this product. "
                    "Enable Sentinel-3 SLSTR access via Copernicus Data Space.",
                    event_dt=event_dt,
                )

            else:
                logger.warning("SLSTR API status %s: %s", resp.status_code, resp.text[:300])
                return self._unavailable(
                    f"Sentinel-3 SLSTR API returned HTTP {resp.status_code}.", event_dt=event_dt
                )

        except requests.Timeout:
            return self._unavailable("Sentinel-3 SLSTR request timed out.", event_dt=event_dt)
        except Exception as e:
            logger.error("Unexpected error fetching SLSTR image: %s", e)
            return self._unavailable(f"Thermal imagery could not be loaded: {str(e)[:120]}", event_dt=event_dt)

    @staticmethod
    def _build_metadata(min_temp: str, max_temp: str) -> Dict[str, Any]:
        return {
            "satellite": "Sentinel-3A / Sentinel-3B",
            "product": "SL_2_LST___",
            "band": "S8 (10.85 um - Thermal Infrared)",
            "resolution": "~1 km at nadir",
            "processing_level": "L2",
            "temperature_units": "Kelvin (K)",
            "min_temp": min_temp,
            "max_temp": max_temp,
            "temporal_window": f"+-{TEMPORAL_WINDOW_HOURS} hours",
            "color_ramp": "IRON (black->red->orange->yellow->white)",
        }

    @staticmethod
    def _unavailable(reason: str, event_dt: Optional[datetime] = None) -> Dict[str, Any]:
        return {
            "available": False,
            "image_bytes": None,
            "source": "Sentinel-3 SLSTR",
            "acquisition_time": None,
            "time_delta_minutes": None,
            "metadata": {
                "satellite": "Sentinel-3A / Sentinel-3B",
                "product": "SL_2_LST___",
                "band": "S8 (10.85 um - Thermal Infrared)",
                "resolution": "~1 km at nadir",
                "processing_level": "L2",
                "temperature_units": "Kelvin (K)",
                "temporal_window": f"+-{TEMPORAL_WINDOW_HOURS} hours",
                "event_time": event_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if event_dt else None,
                "color_ramp": "IRON (black->red->orange->yellow->white)",
            },
            "reason": reason,
        }


# Singleton
thermal_imagery_service = ThermalImageryService()
