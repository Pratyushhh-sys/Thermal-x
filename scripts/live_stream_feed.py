"""
scripts/live_stream_feed.py
===========================
Continuous live stream simulator for SIH 2026 Thermal Source Attribution.
Periodically posts realistic satellite thermal detections through the
Experiment C ML classification & risk assessment pipeline via
POST /api/events/stream/simulate, broadcasting live updates to all connected
SSE clients (browser dashboards).
"""

import itertools
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LiveStreamFeed")

BACKEND_URL = "http://127.0.0.1:8000"
ADMIN_EMAIL = "official@thermalx.gov.in"
ADMIN_PASSWORD = "ThermalX@123"

# Realistic Indian hotspot detection locations
HOTSPOT_REGIONS = [
    {
        "name": "Hazira Industrial Corridor, Gujarat",
        "lat": 21.115,
        "lon": 72.652,
        "base_frp": 110.0,
        "brightness": 362.4,
        "satellite": "VIIRS-SNPP",
    },
    {
        "name": "Jamnagar Refining Hub, Gujarat",
        "lat": 22.470,
        "lon": 70.060,
        "base_frp": 85.5,
        "brightness": 348.1,
        "satellite": "VIIRS-NOAA20",
    },
    {
        "name": "Korba Power & Coal Cluster, Chhattisgarh",
        "lat": 22.359,
        "lon": 82.688,
        "base_frp": 135.0,
        "brightness": 378.0,
        "satellite": "VIIRS-SNPP",
    },
    {
        "name": "Angul Metallurgical Belt, Odisha",
        "lat": 20.840,
        "lon": 85.150,
        "base_frp": 92.0,
        "brightness": 352.3,
        "satellite": "VIIRS-NOAA20",
    },
    {
        "name": "Singrauli Energy Hub, MP/UP Border",
        "lat": 24.200,
        "lon": 82.660,
        "base_frp": 120.0,
        "brightness": 366.5,
        "satellite": "VIIRS-SNPP",
    },
    {
        "name": "Rourkela Steel Sector, Odisha",
        "lat": 22.225,
        "lon": 84.867,
        "base_frp": 78.0,
        "brightness": 344.0,
        "satellite": "VIIRS-NOAA20",
    },
    {
        "name": "Ludhiana Agricultural Zone, Punjab",
        "lat": 30.900,
        "lon": 75.850,
        "base_frp": 45.0,
        "brightness": 328.0,
        "satellite": "VIIRS-SNPP",
    },
    {
        "name": "Kanha Forest Perimeter, MP",
        "lat": 22.200,
        "lon": 80.500,
        "base_frp": 38.0,
        "brightness": 322.0,
        "satellite": "VIIRS-NOAA20",
    },
]


def create_authenticated_session() -> requests.Session:
    """Login and establish cookie-authenticated admin session."""
    session = requests.Session()
    resp = session.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Admin authentication failed: {resp.status_code} {resp.text}")
    logger.info("Authenticated as ADMIN (%s). Live feed active.", ADMIN_EMAIL)
    return session


def run_live_feed():
    logger.info("Starting live thermal stream feed to %s...", BACKEND_URL)
    session = None
    region_cycle = itertools.cycle(HOTSPOT_REGIONS)

    while True:
        try:
            if session is None:
                session = create_authenticated_session()

            region = next(region_cycle)
            # Add slight jitter to coordinates & thermal intensity for realism
            lat_jitter = random.uniform(-0.015, 0.015)
            lon_jitter = random.uniform(-0.015, 0.015)
            frp_jitter = random.uniform(-10.0, 20.0)

            event_id = f"LIVE-{uuid.uuid4().hex[:6].upper()}"
            now = datetime.now(timezone.utc)
            obs = {
                "id": event_id,
                "latitude": round(region["lat"] + lat_jitter, 5),
                "longitude": round(region["lon"] + lon_jitter, 5),
                "frp": round(max(15.0, region["base_frp"] + frp_jitter), 1),
                "brightness": round(region["brightness"] + random.uniform(-5.0, 10.0), 1),
                "brightness_ti5": round(296.0 + random.uniform(-2.0, 5.0), 1),
                "scan": 0.4,
                "track": 0.38,
                "acq_date": now.strftime("%Y-%m-%d"),
                "acq_time": now.strftime("%H%M"),
                "satellite": region["satellite"],
                "day_night": "D",
                "active_days_last_7": random.randint(3, 7),
            }

            resp = session.post(
                f"{BACKEND_URL}/api/events/stream/simulate",
                json=obs,
                timeout=10,
            )

            if resp.status_code == 401:
                logger.warning("Session expired. Re-authenticating...")
                session = None
                continue
            elif resp.status_code == 200:
                data = resp.json()
                evt = data.get("event", {})
                risk = evt.get("risk_tier") or evt.get("risk_level") or "UNKNOWN"
                source = evt.get("source") or evt.get("source_label") or "Unknown"
                clients = data.get("active_clients", 0)
                logger.info(
                    "Broadcasted event %s [%s | Risk: %s | FRP: %.1f MW] to %d client(s)",
                    event_id, source, risk, obs["frp"], clients
                )
            else:
                logger.warning("Simulate returned status %d: %s", resp.status_code, resp.text)

        except requests.exceptions.RequestException as e:
            logger.warning("Connection error: %s. Retrying in 5s...", e)
            session = None
            time.sleep(5)
            continue
        except Exception as e:
            logger.error("Unexpected error in feed loop: %s", e)

        # Broadcast interval (12-15 seconds)
        sleep_sec = random.uniform(10.0, 15.0)
        time.sleep(sleep_sec)


if __name__ == "__main__":
    run_live_feed()

