"""
backend/services/imagery_service.py
====================================
Service for interacting with Sentinel Hub APIs to retrieve satellite imagery.
Uses OAuth2 for authentication and the Process API for downloading raw imagery.
"""

import os
import time
import logging
import requests
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class SentinelImageryService:
    def __init__(self):
        self.client_id = os.getenv("SENTINEL_CLIENT_ID")
        self.client_secret = os.getenv("SENTINEL_CLIENT_SECRET")
        self.token = None
        self.token_expiry = 0

    def _get_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise ValueError("Sentinel Hub credentials not configured.")
        
        # Add 60 seconds buffer before expiry
        if self.token and time.time() < self.token_expiry - 60:
            return self.token
            
        logger.info("Requesting new Sentinel Hub OAuth token...")
        
        response = requests.post(
            "https://services.sentinel-hub.com/oauth/token",
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.token_expiry = time.time() + data.get("expires_in", 3600)
        
        logger.info("Sentinel Hub token acquired successfully.")
        return self.token

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

    def fetch_true_color_image(self, lat: float, lng: float, radius_km: float = 2.0) -> Optional[bytes]:
        """
        Calls Sentinel Hub Process API to fetch a true color image buffer.
        """
        try:
            import math
            token = self._get_token()
            
            # Approximate bounding box
            lat_offset = radius_km / 111.0
            lng_offset = radius_km / (111.0 * math.cos(math.radians(lat))) if lat != 0 else radius_km / 111.0
            
            bbox = [lng - lng_offset, lat - lat_offset, lng + lng_offset, lat + lat_offset]

            evalscript = '''
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
            '''
            
            payload = {
                "input": {
                    "bounds": {
                        "bbox": bbox,
                        "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                    },
                    "data": [
                        {
                            "type": "sentinel-2-l2a",
                            "dataFilter": {
                                "timeRange": {
                                    "from": "2026-07-01T00:00:00Z",
                                    "to": "2026-09-01T23:59:59Z"
                                },
                                "maxCloudCoverage": 20
                            }
                        }
                    ]
                },
                "output": {
                    "width": 512,
                    "height": 512,
                    "responses": [{"identifier": "default", "format": {"type": "image/jpeg"}}]
                },
                "evalscript": evalscript
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://services.sentinel-hub.com/api/v1/process",
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error fetching Sentinel imagery: {e}")
            return None

# Singleton instance
imagery_service = SentinelImageryService()
