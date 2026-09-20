"""
backend/main.py
================
FastAPI application factory for the Thermal Source Attribution backend.

Startup sequence (lifespan):
  1. Load ModelService (Exp C + Exp A models, encoders, feature columns)
  2. Load EventService (20,828-row feature CSV → memory)
  3. Load OSMService  (Day 1 BallTree cache → memory)
  4. Register API routers

Shutdown: no cleanup required (no DB connections, no file handles).

Run with:
  uvicorn backend.main:app --reload --port 8000

Or from project root:
  python -m uvicorn backend.main:app --reload --port 8000
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Allow importing project root modules (ml/, backend/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.api import events, health, summary, notifications, imagery, system
from backend.services.model_service import model_service
from backend.services.event_service import event_service
from backend.services.osm_service import osm_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

FIRMS_BBOX = os.getenv("FIRMS_BBOX", "67,6,98,37")

# BUG-B12: Allow origin list from env (never use wildcard + credentials)
_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://localhost:4173",
    ).split(",")
    if o.strip()
]

# BUG-B12: Limit concurrent expensive requests (each GET /api/events runs ML inference)
_CONCURRENCY_LIMIT = int(os.getenv("API_CONCURRENCY", "4"))
_request_semaphore: asyncio.Semaphore  # initialised in lifespan


# ---------------------------------------------------------------------------
# Startup / shutdown lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    All services are loaded synchronously at startup.
    Failure to load any service will prevent the API from starting.
    """
    logger.info("=" * 60)
    logger.info("  Thermal Source Attribution API — Starting up")
    logger.info("  SIH 2026 PS 26162")
    logger.info("=" * 60)

    # --- Load model service ---
    logger.info("Loading model artifacts...")
    model_service.load()   # Raises RuntimeError/FileNotFoundError on failure

    # --- Load event dataset ---
    logger.info("Loading feature dataset...")
    event_service.load()   # Raises FileNotFoundError on failure

    # --- Load OSM cache ---
    logger.info("Loading OSM feature cache...")
    osm_service.load(bbox_firms=FIRMS_BBOX)

    # --- Expose as app state ---
    app.state.model_service = model_service
    app.state.event_service = event_service
    app.state.osm_service   = osm_service

    # BUG-B12: initialise the concurrency semaphore
    global _request_semaphore
    _request_semaphore = asyncio.Semaphore(_CONCURRENCY_LIMIT)

    logger.info("-" * 60)
    logger.info("  Model:   Exp C (%d features) + Exp A (%d features)",
                model_service.exp_c_feature_count,
                model_service.exp_a_feature_count)
    logger.info("  Events:  %d thermal events", event_service.get_total_count())
    logger.info("  OSM:     %d / 10 feature types cached", osm_service.loaded_type_count)
    logger.info("  Classes: %s", model_service.class_names)
    logger.info("-" * 60)
    logger.info("  LABEL DISCLAIMER: source_label = WEAK GEOGRAPHIC LABEL")
    logger.info("  NOT verified fire-cause ground truth.")
    logger.info("=" * 60)
    logger.info("  API ready at http://localhost:8000")
    logger.info("  Docs at   http://localhost:8000/docs")
    logger.info("=" * 60)

    yield

    logger.info("Thermal Source Attribution API — Shutdown complete.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Thermal Source Attribution API",
    description=(
        "Satellite-Based Industrial Fire & Thermal Source Attribution\n\n"
        "**SIH 2026 PS 26162**\n\n"
        "Provides thermal event intelligence: source classification, "
        "GIS context, 7-day persistence, risk scoring, and explainability.\n\n"
        "> **Label disclaimer**: `source_label` is a **weak geographic label** "
        "derived from OSM proximity. It is **NOT** verified fire-cause ground truth. "
        "Classification results are labeled 'Probable Source', not 'Confirmed Fire Cause'."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# BUG-B03: Do NOT combine allow_credentials=True with allow_origins=["*"].
# That violates the CORS spec and browsers will block such responses.
# Use explicit origin list from environment instead.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS", "POST"],
    allow_headers=["*"],
)


# BUG-B12: Middleware to reject requests when the server is already at capacity
@app.middleware("http")
async def concurrency_limit_middleware(request: Request, call_next):
    if not await _request_semaphore.acquire.__func__(_request_semaphore):
        return JSONResponse(status_code=503, content={"detail": "Server busy, retry shortly"})
    try:
        return await call_next(request)
    finally:
        _request_semaphore.release()

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(imagery.router, prefix="/api")
app.include_router(system.router, prefix="/api")

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Thermal Source Attribution API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "events": "/api/events",
        "summary": "/api/summary",
        "label_disclaimer": (
            "source_label is a weak geographic label from OSM proximity. "
            "NOT verified fire-cause ground truth."
        ),
    }
