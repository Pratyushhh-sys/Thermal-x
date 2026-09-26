"""
backend/tests/test_api.py
==========================
Acceptance tests for the Thermal Source Attribution backend API.

Tests:
  1.  Backend health — /api/health returns 200 and model_loaded=True
  2.  Model loading — ModelService has correct feature count
  3.  GET /api/events — returns list of events
  4.  GET /api/events pagination — offset/limit work
  5.  GET /api/events/{id} — full intelligence response for a real event
  6.  Classification output — probabilities sum to ~1.0, all 5 classes present
  7.  Persistence features — active_days_last_7 is an int, ratio in [0,1]
  8.  Risk calculation — score in [0,100], tier in {HIGH,MEDIUM,LOW}
  9.  Missing OSM data handled — 404 events near missing-cache areas return null, not crash
  10. Invalid event ID — returns 404

Run with:
  pytest backend/tests/test_api.py -v
  (from project root)
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app


# ---------------------------------------------------------------------------
# Session-scoped service loading (runs once for all tests)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def load_services():
    """
    Load all backend services once before any tests run.
    Injects them into app.state directly (bypasses ASGI lifespan complexity).
    """
    from backend.services.model_service import model_service
    from backend.services.event_service import event_service
    from backend.services.osm_service import osm_service
    import os

    if not model_service.is_loaded:
        model_service.load()
    try:
        event_service.get_total_count()
    except RuntimeError:
        event_service.load()
    if osm_service.loaded_type_count == 0:
        osm_service.load(bbox_firms=os.getenv("FIRMS_BBOX", "67,6,98,37"))

    app.state.model_service = model_service
    app.state.event_service = event_service
    app.state.osm_service   = osm_service


# ---------------------------------------------------------------------------
# Shared async client fixture
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="module")
async def client():
    """
    Async HTTP client for the FastAPI app.
    Services are already loaded by load_services fixture above.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test 1: Backend health
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health_endpoint(client):
    """GET /api/health should return 200 with model_loaded=True."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200, f"Health returned {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["events_available"] > 0
    assert data["osm_cache_types"] >= 0


# ---------------------------------------------------------------------------
# Test 2: Model loading
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_model_feature_count(client):
    """Model should have 32 features (Exp C)."""
    resp = await client.get("/api/health")
    data = resp.json()
    assert data["model_feature_count"] == 32, (
        f"Expected 32 Exp C features, got {data['model_feature_count']}"
    )
    assert "Experiment C" in data["model_experiment"]


# ---------------------------------------------------------------------------
# Test 3: GET /api/events — list returns results
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_events_list(client):
    """GET /api/events should return a non-empty list."""
    resp = await client.get("/api/events?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "id" in first
    assert first["id"].startswith("TH")
    assert "location" in first
    assert "frp" in first


# ---------------------------------------------------------------------------
# Test 4: Pagination — offset and limit
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_events_pagination(client):
    """Offset pagination should return different events."""
    resp_0 = await client.get("/api/events?limit=5&offset=0")
    resp_5 = await client.get("/api/events?limit=5&offset=5")
    data_0 = resp_0.json()
    data_5 = resp_5.json()
    assert len(data_0) == 5
    assert len(data_5) == 5
    ids_0 = {e["id"] for e in data_0}
    ids_5 = {e["id"] for e in data_5}
    assert ids_0.isdisjoint(ids_5), "Paginated pages should not overlap"


# ---------------------------------------------------------------------------
# Test 5: Full event intelligence — /api/events/{id}
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_event_detail(client):
    """GET /api/events/TH00042 should return complete intelligence structure."""
    resp = await client.get("/api/events/TH00042")
    assert resp.status_code == 200, f"Returned {resp.status_code}: {resp.text[:300]}"
    data = resp.json()

    # Top-level keys
    for key in ["id", "location", "firms", "persistence", "gis_context",
                "classification", "risk", "metadata"]:
        assert key in data, f"Missing key: {key}"

    assert data["id"] == "TH00042"
    assert data["location"]["lat"] != 0
    assert data["firms"]["frp"] > 0


# ---------------------------------------------------------------------------
# Test 6: Classification output — probabilities correct
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_classification_probabilities(client):
    """Probabilities should sum to ~1.0 and cover all 5 classes."""
    resp = await client.get("/api/events/TH00100")
    assert resp.status_code == 200
    data = resp.json()

    clf = data["classification"]
    assert "thermal_only_estimate" in clf
    te = clf["thermal_only_estimate"]

    assert te["label"] == "Probable Source"
    assert "label_type" in te
    assert "verified" not in te["label"].lower()  # Must NOT say "Confirmed"

    probs = te["probabilities"]
    classes = {"Agricultural", "Forest", "Industrial", "Mining", "Other"}
    assert set(probs.keys()) == classes, f"Missing classes: {set(probs.keys())}"

    total = sum(probs.values())
    assert abs(total - 1.0) < 0.01, f"Probabilities sum to {total}, expected ~1.0"


# ---------------------------------------------------------------------------
# Test 7: Persistence features
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_persistence_features(client):
    """Persistence fields should be valid."""
    resp = await client.get("/api/events/TH00200")
    assert resp.status_code == 200
    pers = resp.json()["persistence"]

    assert isinstance(pers["active_days_last_7"], int)
    assert 0 <= pers["active_days_last_7"] <= 7
    assert 0.0 <= pers["persistence_ratio"] <= 1.0
    assert isinstance(pers["observation_count_last_7"], int)
    assert pers["trend_label"] in {"persistent", "frequent", "intermittent", "new", "declining"}


# ---------------------------------------------------------------------------
# Test 8: Risk calculation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_risk_calculation(client):
    """Risk score should be in [0,100] with valid tier and all 4 components."""
    resp = await client.get("/api/events/TH00050")
    assert resp.status_code == 200
    risk = resp.json()["risk"]

    assert 0.0 <= risk["score"] <= 100.0
    assert risk["tier"] in {"HIGH", "MEDIUM", "LOW"}

    components = risk["components"]
    for comp in ["thermal", "persistence", "osm", "ai"]:
        assert comp in components
        assert 0.0 <= components[comp] <= 100.0

    assert len(risk["reasons"]) >= 2


# ---------------------------------------------------------------------------
# Test 9: Missing OSM data — API must not crash
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_missing_osm_handled(client):
    """
    Events far from any cached OSM feature should return null context fields,
    NOT a 500 error.
    """
    # Use an event — we don't know which has empty OSM, but the API must never 500
    for event_id in ["TH00001", "TH01000", "TH05000"]:
        resp = await client.get(f"/api/events/{event_id}")
        assert resp.status_code in {200, 404}, (
            f"{event_id}: expected 200 or 404, got {resp.status_code}: {resp.text[:200]}"
        )
        if resp.status_code == 200:
            gis = resp.json().get("gis_context", {})
            # Any nearest_* field can be null — that's fine
            buffers = gis.get("buffers", {})
            assert "100m" in buffers
            assert "500m" in buffers
            assert "1000m" in buffers


# ---------------------------------------------------------------------------
# Test 10: Invalid event ID → 404
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invalid_event_id(client):
    """Non-existent event ID should return HTTP 404."""
    resp = await client.get("/api/events/TH99999999")
    assert resp.status_code == 404
    assert "not found" in resp.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# Test 11: Summary endpoint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_summary(client):
    """GET /api/summary should return aggregate statistics."""
    resp = await client.get("/api/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_events"] > 0
    assert "source_distribution" in data
    assert data["avg_frp"] > 0
    assert "label_disclaimer" in data


# ---------------------------------------------------------------------------
# Test 12: Filter by source label
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_events_source_filter(client):
    """Source filter should return only matching events."""
    resp = await client.get("/api/events?source=Industrial&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    for item in data:
        assert item.get("source_label", "").lower() == "industrial", (
            f"Non-Industrial event in filtered result: {item['source_label']}"
        )


# ---------------------------------------------------------------------------
# Test 13: Imagery metadata endpoint (Optical + Thermal)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_imagery_metadata(client):
    """GET /api/events/{id}/imagery should return optical and thermal blocks."""
    events_resp = await client.get("/api/events?limit=1")
    event_id = events_resp.json()[0]["id"]

    resp = await client.get(f"/api/events/{event_id}/imagery")
    assert resp.status_code == 200
    data = resp.json()

    assert data["event_id"] == event_id
    assert "optical" in data
    assert "thermal" in data

    # Optical block checks
    assert data["optical"]["source"] == "Sentinel-2 L2A"
    assert "metadata" in data["optical"]

    # Thermal block checks
    assert isinstance(data["thermal"]["available"], bool)
    assert data["thermal"]["source"] == "Sentinel-3 SLSTR"
    if not data["thermal"]["available"]:
        assert data["thermal"]["reason"] is not None


# ---------------------------------------------------------------------------
# Test 14: Thermal imagery binary endpoint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_thermal_imagery_endpoint(client):
    """GET /api/imagery/{id}/thermal should return 200 (if scene exists) or 204 (if unavailable), never 500."""
    events_resp = await client.get("/api/events?limit=1")
    event_id = events_resp.json()[0]["id"]

    resp = await client.get(f"/api/imagery/{event_id}/thermal")
    assert resp.status_code in (200, 204), f"Unexpected status code {resp.status_code}: {resp.text}"
