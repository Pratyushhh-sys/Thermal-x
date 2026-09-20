"""
backend/services/imagery_service.py
====================================
Service for interacting with Sentinel Hub / Copernicus Data Space Ecosystem (CDSE)
APIs to retrieve real-time true-color satellite imagery for thermal events.
Uses OAuth2 client credentials authentication and the Process API.
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Cache directory for retrieved imagery
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "imagery"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Copernicus Data Space Ecosystem (CDSE) endpoints (Current Sentinel Hub API)
CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# Legacy Sentinel Hub endpoints (fallback)
LEGACY_SH_TOKEN_URL = "https://services.sentinel-hub.com/oauth/token"
LEGACY_SH_PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"


class SentinelImageryService:
    def __init__(self):
        self.token: Optional[str] = None
        self.token_expiry: float = 0
        self.active_process_url: str = CDSE_PROCESS_URL

    def _get_credentials(self) -> Tuple[str, str]:
        # Always reload / check environment dynamically
        client_id = os.getenv("SENTINEL_CLIENT_ID", "").strip()
        client_secret = os.getenv("SENTINEL_CLIENT_SECRET", "").strip()

        if not client_id or not client_secret:
            # Try reloading from .env explicitly
            env_path = Path(__file__).resolve().parents[2] / ".env"
            if env_path.exists():
                load_dotenv(env_path, override=True)
                client_id = os.getenv("SENTINEL_CLIENT_ID", "").strip()
                client_secret = os.getenv("SENTINEL_CLIENT_SECRET", "").strip()

        if not client_id or not client_secret:
            raise ValueError("Sentinel Hub / CDSE credentials not configured in environment or .env.")

        return client_id, client_secret

    def _get_token(self) -> str:
        client_id, client_secret = self._get_credentials()

        # Check if current token is still valid (60-second safety margin)
        if self.token and time.time() < self.token_expiry - 60:
            return self.token

        logger.info("Requesting new Copernicus CDSE / Sentinel Hub OAuth token...")

        # 1. Try Copernicus Data Space Ecosystem (Primary for all new sh-* keys)
        try:
            response = requests.post(
                CDSE_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=12,
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.token_expiry = time.time() + data.get("expires_in", 1800)
                self.active_process_url = CDSE_PROCESS_URL
                logger.info("Copernicus CDSE OAuth token acquired successfully.")
                return self.token
            else:
                logger.warning("CDSE OAuth failed (Status %s): %s", response.status_code, response.text[:200])
        except Exception as err:
            logger.warning("Error connecting to CDSE token endpoint: %s", err)

        # 2. Fallback to Legacy Sentinel Hub endpoint
        try:
            logger.info("Attempting legacy Sentinel Hub token endpoint...")
            response = requests.post(
                LEGACY_SH_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                timeout=12,
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.token_expiry = time.time() + data.get("expires_in", 3600)
                self.active_process_url = LEGACY_SH_PROCESS_URL
                logger.info("Legacy Sentinel Hub OAuth token acquired successfully.")
                return self.token
            else:
                response.raise_for_status()
        except Exception as err:
            logger.error("All Sentinel authentication endpoints failed: %s", err)
            raise

        raise RuntimeError("Failed to obtain satellite imagery OAuth token.")

    def get_bbox_for_point(self, lat: float, lng: float, radius_km: float = 2.0) -> Tuple[float, float, float, float]:
        """
        Convert a point and a radius into a bounding box [min_lng, min_lat, max_lng, max_lat].
        Rough approximation: 1 degree latitude is ~111 km.
        """
        import math
        lat_offset = radius_km / 111.0
        lng_offset = radius_km / (111.0 * math.cos(math.radians(lat))) if lat != 0 else radius_km / 111.0

        min_lng = lng - lng_offset
        max_lng = lng + lng_offset
        min_lat = lat - lat_offset
        max_lat = lat + lat_offset
        return (min_lng, min_lat, max_lng, max_lat)

    def fetch_true_color_image(
        self,
        lat: float,
        lng: float,
        radius_km: float = 2.0,
        acq_date: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Calls Sentinel Hub / CDSE Process API to fetch a true-color Sentinel-2 L2A image.
        Uses a dynamic 60-day window leading up to the acquisition date.
        Caches results locally to avoid redundant API calls.
        """
        # Parse acquisition date
        if acq_date:
            clean_date_str = str(acq_date).strip().split("T")[0].split(" ")[0]
            try:
                end_date = datetime.strptime(clean_date_str, "%Y-%m-%d")
            except ValueError:
                logger.warning("Could not parse acq_date '%s', defaulting to UTC now", acq_date)
                end_date = datetime.utcnow()
        else:
            end_date = datetime.utcnow()

        start_date = end_date - timedelta(days=60)
        date_str = end_date.strftime("%Y-%m-%d")

        # Check local disk cache
        cache_filename = f"{event_id}.jpg" if event_id else f"{lat:.4f}_{lng:.4f}_{date_str}.jpg"
        cache_file = CACHE_DIR / cache_filename
        if cache_file.exists() and cache_file.stat().st_size > 1000:
            logger.info("Serving satellite image from local cache: %s", cache_filename)
            try:
                return cache_file.read_bytes()
            except Exception as e:
                logger.warning("Error reading cache file %s: %e", cache_file, e)

        try:
            token = self._get_token()

            min_lng, min_lat, max_lng, max_lat = self.get_bbox_for_point(lat, lng, radius_km)
            bbox = [min_lng, min_lat, max_lng, max_lat]

            # True-color RGB evalscript with 2.5x gain enhancement for crystal-clear industrial clarity
            evalscript = """
            //VERSION=3
            function setup() {
              return {
                input: ["B02", "B03", "B04"],
                output: { bands: 3 }
              };
            }
            function evaluatePixel(sample) {
              return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
            }
            """

            # Try cloud coverage levels (starts at 20% as requested, falls back if overcast monsoon period)
            cloud_cover_levels = [20, 50, 80]
            for cloud_max in cloud_cover_levels:
                payload = {
                    "input": {
                        "bounds": {
                            "bbox": bbox,
                            "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                        },
                        "data": [
                            {
                                "type": "sentinel-2-l2a",
                                "dataFilter": {
                                    "timeRange": {
                                        "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                                        "to": end_date.strftime("%Y-%m-%dT23:59:59Z"),
                                    },
                                    "maxCloudCoverage": cloud_max,
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
                    "evalscript": evalscript,
                }

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }

                resp = requests.post(
                    self.active_process_url,
                    headers=headers,
                    json=payload,
                    timeout=20,
                )

                if resp.status_code == 200:
                    img_bytes = resp.content
                    # If returned image is greater than 6KB (non-blank), cache and return
                    if len(img_bytes) > 6000:
                        try:
                            cache_file.write_bytes(img_bytes)
                        except Exception as write_err:
                            logger.warning("Could not write cache file: %s", write_err)
                        return img_bytes
                    elif cloud_max == cloud_cover_levels[-1]:
                        # Even if smaller, return last valid response
                        return img_bytes
                else:
                    logger.warning(
                        "Sentinel Process API returned %s with cloudMax=%s: %s",
                        resp.status_code,
                        cloud_max,
                        resp.text[:200],
                    )

            logger.warning("No clear satellite imagery found in window %s to %s", start_date, end_date)
            return None

        except Exception as e:
            logger.error("Error fetching Sentinel imagery: %s", e)
            return None


# Singleton instance
imagery_service = SentinelImageryService()
