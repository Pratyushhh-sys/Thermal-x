"""
ml/data_collection/firms_client.py
====================================
NASA FIRMS VIIRS Data Client

Data acquisition strategy (in order of priority):
  1. NASA FIRMS MAP_KEY API (NRT or archive)
  2. Locally supplied, officially downloaded FIRMS CSV file

NEVER fabricates satellite observations.
If neither source is available, raises a clear RuntimeError with instructions.

FIRMS API documentation:
  https://firms.modaps.eosdis.nasa.gov/api/
"""

import datetime
import os
import logging
import time
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FIRMS_API_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Supported VIIRS datasets (in preference order)
VIIRS_DATASETS = [
    "VIIRS_NOAA21_NRT",   # newest satellite, most data
    "VIIRS_NOAA20_NRT",
    "VIIRS_SNPP_NRT",
    "MODIS_NRT",
]

# Canonical VIIRS column names expected from the FIRMS API
VIIRS_REQUIRED_COLS = {"latitude", "longitude", "acq_date", "frp"}

# India bounding box (West, South, East, North) — default target region
INDIA_BBOX = "67,6,98,37"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class FIRMSClient:
    """
    Client for retrieving NASA FIRMS VIIRS active-fire hotspot data.

    Parameters
    ----------
    map_key : str, optional
        FIRMS MAP_KEY. If not provided, reads from FIRMS_MAP_KEY env var.
    local_file_path : str or Path, optional
        Path to a locally downloaded FIRMS CSV file. If not provided, reads
        from FIRMS_LOCAL_FILE env var.
    """

    def __init__(
        self,
        map_key: Optional[str] = None,
        local_file_path: Optional[str] = None,
    ):
        self.map_key = map_key or os.getenv("FIRMS_MAP_KEY", "").strip()
        self.local_file_path = local_file_path or os.getenv("FIRMS_LOCAL_FILE", "").strip()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def fetch(
        self,
        area: str = INDIA_BBOX,
        days: int = 5,
        dataset: str = "ALL_VIIRS_NRT",
    ) -> pd.DataFrame:
        """
        Fetch the most recent FIRMS NRT data (up to 5 days).

        For longer historical windows, use fetch_date_range().

        Parameters
        ----------
        area : str
            Bounding box in FIRMS format: 'W,S,E,N'
        days : int
            Number of recent days to request (max 5 for NRT API).
        dataset : str
            FIRMS dataset name, or 'ALL_VIIRS_NRT' to combine all three
            VIIRS satellites (NOAA-21, NOAA-20, Suomi-NPP) for maximum coverage.
        """
        # Clamp days to NRT API limit
        days = min(days, 5)

        # ── Strategy 1: MAP_KEY API ──────────────────────────────────────
        if self.map_key and self.map_key != "your_firms_map_key_here":
            logger.info(
                "FIRMS: Attempting API fetch | dataset=%s | area=%s | days=%d",
                dataset, area, days,
            )
            if dataset == "ALL_VIIRS_NRT":
                # Combine all three VIIRS satellites for maximum data coverage
                return self._fetch_all_viirs(area=area, days=days)

            for ds in [dataset] + [d for d in VIIRS_DATASETS if d != dataset]:
                try:
                    df = self._fetch_from_api(area=area, days=days, dataset=ds)
                    logger.info("FIRMS API success: %d records via %s", len(df), ds)
                    return df
                except Exception as exc:
                    logger.warning("FIRMS API failed for %s: %s", ds, exc)
            logger.warning("All FIRMS API dataset variants failed.")
        else:
            logger.warning(
                "FIRMS_MAP_KEY not set or is placeholder. "
                "Get a free key at https://firms.modaps.eosdis.nasa.gov/api/"
            )

        # ── Strategy 2: Local file ───────────────────────────────────────
        if self.local_file_path:
            logger.info("FIRMS: Loading local file: %s", self.local_file_path)
            try:
                df = self._load_local_file(self.local_file_path)
                logger.info("Local FIRMS file loaded: %d records", len(df))
                return df
            except Exception as exc:
                logger.error("Failed to load local FIRMS file: %s", exc)

        # ── No source available ──────────────────────────────────────────
        raise RuntimeError(
            "\n"
            "═══════════════════════════════════════════════════════════\n"
            " FIRMS DATA UNAVAILABLE — no data will be fabricated.\n"
            "═══════════════════════════════════════════════════════════\n"
            "\n"
            " Option 1 — Use the FIRMS API (recommended):\n"
            "   1. Register for a free MAP_KEY at:\n"
            "      https://firms.modaps.eosdis.nasa.gov/api/\n"
            "   2. Set FIRMS_MAP_KEY=<your_key> in your .env file.\n"
            "\n"
            " Option 2 — Use a locally downloaded FIRMS dataset:\n"
            "   1. Download VIIRS CSV from:\n"
            "      https://firms.modaps.eosdis.nasa.gov/download/\n"
            "   2. Set FIRMS_LOCAL_FILE=/path/to/firms_data.csv in .env\n"
            "\n"
            " Neither source is currently configured.\n"
        )

    def fetch_date_range(
        self,
        area: str = INDIA_BBOX,
        total_days: int = 30,
        dataset: str = "ALL_VIIRS_NRT",
        end_date: Optional[datetime.date] = None,
    ) -> pd.DataFrame:
        """
        Fetch FIRMS data over a longer historical window by stitching
        multiple 5-day API calls.

        Uses the confirmed FIRMS date-range URL format:
          /api/area/csv/{key}/{dataset}/{area}/{days}/{YYYY-MM-DD}
        where the date is the LAST day of that 5-day window.

        Parameters
        ----------
        area : str
            Bounding box 'W,S,E,N'
        total_days : int
            Total historical window to fetch (e.g. 30).
            Will be stitched from multiple 5-day windows.
        dataset : str
            'ALL_VIIRS_NRT' to combine all three satellites, or a specific dataset.
        end_date : datetime.date, optional
            Last date of the window. Defaults to today.

        Returns
        -------
        pd.DataFrame
            All records across the full window, deduplicated.
        """
        if not (self.map_key and self.map_key != "your_firms_map_key_here"):
            raise RuntimeError("FIRMS_MAP_KEY required for historical fetch.")

        if end_date is None:
            end_date = datetime.date.today()

        # Build list of window end-dates (step back 5 days at a time)
        window_size = 5
        windows = []
        current_end = end_date
        days_covered = 0
        while days_covered < total_days:
            windows.append(current_end)
            current_end = current_end - datetime.timedelta(days=window_size)
            days_covered += window_size

        logger.info(
            "Fetching %d days of FIRMS history: %d windows ending %s → %s",
            total_days, len(windows),
            windows[-1] - datetime.timedelta(days=window_size - 1),
            windows[0],
        )

        satellites = ["VIIRS_NOAA21_NRT", "VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT"] \
            if dataset == "ALL_VIIRS_NRT" else [dataset]

        all_dfs = []
        for win_end in tqdm(windows, desc="Fetching historical windows"):
            date_str = win_end.strftime("%Y-%m-%d")
            for ds in satellites:
                try:
                    df = self._fetch_from_api_dated(
                        area=area, days=window_size, dataset=ds, date_str=date_str
                    )
                    df["_source_dataset"] = ds
                    all_dfs.append(df)
                except Exception as exc:
                    logger.warning("  %s @ %s failed: %s", ds, date_str, exc)
            time.sleep(1.0)  # be polite to FIRMS servers between windows

        if not all_dfs:
            raise RuntimeError("All historical FIRMS windows failed.")

        combined = pd.concat(all_dfs, ignore_index=True)
        before = len(combined)
        dedup_cols = [c for c in ["latitude", "longitude", "acq_date", "acq_time", "satellite"]
                      if c in combined.columns]
        combined.drop_duplicates(subset=dedup_cols, keep="first", inplace=True)
        after = len(combined)
        logger.info(
            "Historical fetch complete: %d records across %d days (dedup removed %d)",
            after, total_days, before - after
        )
        # Document the actual observation window
        if "acq_date" in combined.columns:
            dates = pd.to_datetime(combined["acq_date"], errors="coerce").dropna()
            if not dates.empty:
                actual_start = dates.min().date()
                actual_end = dates.max().date()
                actual_days = (actual_end - actual_start).days + 1
                logger.info(
                    "Actual observation window: %s to %s (%d distinct days)",
                    actual_start, actual_end, actual_days
                )
                combined.attrs["obs_start"] = str(actual_start)
                combined.attrs["obs_end"]   = str(actual_end)
                combined.attrs["obs_days"]  = actual_days
        return combined

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _fetch_from_api(self, area: str, days: int, dataset: str) -> pd.DataFrame:
        """Download recent NRT data (last N days) from FIRMS API."""
        url = f"{FIRMS_API_BASE}/{self.map_key}/{dataset}/{area}/{days}"
        return self._get_csv(url)

    def _fetch_from_api_dated(
        self, area: str, days: int, dataset: str, date_str: str
    ) -> pd.DataFrame:
        """Download FIRMS data ending on a specific date using the date-range URL format.

        Confirmed working format: /{key}/{dataset}/{area}/{days}/{YYYY-MM-DD}
        """
        url = f"{FIRMS_API_BASE}/{self.map_key}/{dataset}/{area}/{days}/{date_str}"
        return self._get_csv(url)

    def _get_csv(self, url: str) -> pd.DataFrame:
        """GET a FIRMS CSV URL, validate, and return as DataFrame."""
        logger.debug("GET %s", url)
        headers = {"User-Agent": "ThermalSourceAttribution/1.0 SIH2026-PS26162"}
        resp = requests.get(url, headers=headers, timeout=180)
        resp.raise_for_status()

        content = resp.text.strip()
        if not content:
            raise ValueError("API returned empty body.")
        if content.startswith("Invalid"):
            raise ValueError(f"API rejected request: {content[:300]}")
        if content.startswith("<"):
            raise ValueError(f"API returned HTML/XML: {content[:300]}")

        df = pd.read_csv(StringIO(content), low_memory=False)
        missing = VIIRS_REQUIRED_COLS - set(df.columns)
        if missing:
            raise ValueError(
                f"Missing VIIRS columns: {missing}. Got: {list(df.columns)}"
            )
        if df.empty:
            raise ValueError("API returned a header-only (empty) CSV.")
        return df

    def _fetch_all_viirs(self, area: str, days: int) -> pd.DataFrame:
        """
        Fetch from all three VIIRS NRT satellites and combine.
        Deduplicates on (latitude, longitude, acq_date, acq_time, satellite).
        """
        all_dfs = []
        viirs_nrt = ["VIIRS_NOAA21_NRT", "VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT"]
        for ds in viirs_nrt:
            try:
                df = self._fetch_from_api(area=area, days=days, dataset=ds)
                df["_source_dataset"] = ds
                all_dfs.append(df)
                logger.info("  %s: %d records", ds, len(df))
            except Exception as exc:
                logger.warning("  %s failed: %s", ds, exc)

        if not all_dfs:
            raise ValueError("All VIIRS NRT datasets failed.")

        combined = pd.concat(all_dfs, ignore_index=True)
        before = len(combined)
        dedup_cols = [c for c in ["latitude", "longitude", "acq_date", "acq_time", "satellite"]
                      if c in combined.columns]
        combined.drop_duplicates(subset=dedup_cols, keep="first", inplace=True)
        logger.info("Combined all VIIRS: %d records (dedup removed %d)", len(combined), before - len(combined))
        return combined

    def _load_local_file(self, path: str) -> pd.DataFrame:
        """Load a locally downloaded FIRMS CSV file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Local FIRMS file not found: {p.resolve()}")

        suffix = p.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(p, low_memory=False)
        elif suffix in (".parquet", ".pq"):
            df = pd.read_parquet(p)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Expected .csv or .parquet")

        missing = VIIRS_REQUIRED_COLS - set(df.columns)
        if missing:
            raise ValueError(
                f"Local file missing expected VIIRS columns: {missing}. "
                f"Got: {list(df.columns)}"
            )

        return df


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------
def load_firms_data(
    area: str = INDIA_BBOX,
    days: int = 10,
    dataset: str = "VIIRS_NOAA20_NRT",
    map_key: Optional[str] = None,
    local_file: Optional[str] = None,
) -> pd.DataFrame:
    """
    Module-level convenience wrapper around FIRMSClient.fetch().

    Reads FIRMS_MAP_KEY / FIRMS_LOCAL_FILE from environment if not supplied.
    """
    client = FIRMSClient(map_key=map_key, local_file_path=local_file)
    return client.fetch(area=area, days=days, dataset=dataset)
