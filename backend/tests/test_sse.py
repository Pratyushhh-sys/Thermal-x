"""
backend/tests/test_sse.py
=========================
Unit and integration tests for Server-Sent Events (SSE) functionality.
Tests are completely additive and validate:
  - Stream endpoint headers and status
  - SSEConnectionManager lifecycle and broadcasting
  - Event formatting and Last-Event-ID replay
  - Simulated observation processing through the existing ML/risk pipeline
"""

import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.sse_service import (
    sse_manager,
    _format_sse,
    publish_thermal_event,
    publish_dashboard_update,
    publish_notification,
    publish_system_status,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post(
            "/api/auth/login",
            data={"username": "official@thermalx.gov.in", "password": "ThermalX@123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        yield c


def test_sse_status_endpoint(client):
    """Test GET /api/events/stream/status."""
    response = client.get("/api/events/stream/status")
    assert response.status_code == 200
    data = response.json()
    assert "active_clients" in data
    assert data["status"] == "online"
    assert data["heartbeat_interval_seconds"] == 20


def test_sse_formatting():
    """Test RFC 8895 formatting."""
    frame = _format_sse("thermal_event", {"id": "TH001", "frp": 50.0}, event_id="123")
    assert frame == "id: 123\nevent: thermal_event\ndata: {\"id\": \"TH001\", \"frp\": 50.0}\n\n"


def test_sse_manager_connect_and_broadcast():
    """Test SSEConnectionManager connection and message broadcasting."""
    sse_client = sse_manager.connect()
    initial_count = sse_manager.client_count
    assert initial_count >= 1

    # Broadcast an event
    sse_manager.broadcast("test_event", {"msg": "hello"}, event_id="evt_01")
    assert not sse_client.queue.empty()
    item = sse_client.queue.get_nowait()
    assert "event: test_event" in item
    assert "evt_01" in item

    # Disconnect
    sse_manager.disconnect(sse_client)
    assert sse_manager.client_count == initial_count - 1


def test_sse_last_event_id_replay():
    """Test Last-Event-ID replay from the ring buffer."""
    # Broadcast two events
    sse_manager.broadcast("thermal_event", {"id": "E1"}, event_id="id_1")
    sse_manager.broadcast("thermal_event", {"id": "E2"}, event_id="id_2")

    # Connect client with last_event_id="id_1"
    replaying_client = sse_manager.connect(last_event_id="id_1")
    try:
        assert not replaying_client.queue.empty()
        replayed = replaying_client.queue.get_nowait()
        assert "id: id_2" in replayed
    finally:
        sse_manager.disconnect(replaying_client)


def test_sse_simulate_pipeline_integration(client):
    """
    Test POST /api/events/stream/simulate.
    Validates that observation is processed through the existing pipeline,
    classified via Experiment C, evaluated by risk engine, and broadcast.
    """
    test_client_sse = sse_manager.connect()
    try:
        payload = {
            "id": "SIM-TEST-001",
            "latitude": 21.115,
            "longitude": 72.652,
            "frp": 85.0,  # High FRP -> should trigger HIGH risk
            "source": "Industrial",
        }
        res = client.post("/api/events/stream/simulate", json=payload)
        assert res.status_code == 200
        result_data = res.json()
        assert result_data["status"] == "processed_and_broadcast"
        event = result_data["event"]
        assert event["id"] == "SIM-TEST-001"
        assert event["risk_level"] in {"HIGH", "CRITICAL"}
        assert event["simulated"] is True

        # Check that events were enqueued to the connected SSE client
        frames = []
        while not test_client_sse.queue.empty():
            frames.append(test_client_sse.queue.get_nowait())

        # Should contain thermal_event, high_risk_alert, notification, dashboard_update
        all_frames_text = "".join(frames)
        assert "event: thermal_event" in all_frames_text
        assert "event: high_risk_alert" in all_frames_text
        assert "event: notification" in all_frames_text
        assert "event: dashboard_update" in all_frames_text
    finally:
        sse_manager.disconnect(test_client_sse)


def test_sse_broadcast_endpoint(client):
    """Test POST /api/events/stream/broadcast."""
    test_client_sse = sse_manager.connect()
    try:
        res = client.post(
            "/api/events/stream/broadcast",
            json={
                "event": "system_status",
                "data": {"status": "maintenance_scheduled"},
                "id": "custom_001",
            },
        )
        assert res.status_code == 200
        assert not test_client_sse.queue.empty()
        frame = test_client_sse.queue.get_nowait()
        assert "event: system_status" in frame
        assert "maintenance_scheduled" in frame
    finally:
        sse_manager.disconnect(test_client_sse)

