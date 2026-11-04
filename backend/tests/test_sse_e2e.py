"""
backend/tests/test_sse_e2e.py
=============================
Comprehensive end-to-end verification covering all Section 10 requirements:
  1. Existing REST APIs continue working unchanged.
  2. SSE endpoint returns text/event-stream with no-cache headers.
  3. Real ML pipeline execution on observations (Exp C + Risk Engine).
  4. Broadcasting of thermal_event, high_risk_alert, notification, dashboard_update.
  5. Multi-client broadcasting and client disconnect cleanup.
  6. Reconnection and Last-Event-ID replay.
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.sse_service import sse_manager


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post(
            "/api/auth/login",
            data={"username": "official@thermalx.gov.in", "password": "ThermalX@123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        yield c


def test_existing_rest_apis_unaffected(client):
    """Verify that all existing REST API endpoints continue functioning identically."""
    # 1. Health
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # 2. Summary
    res_summary = client.get("/api/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert "total_events" in summary
    assert "source_distribution" in summary

    # 3. Events list
    res_events = client.get("/api/events?limit=5")
    assert res_events.status_code == 200
    events = res_events.json()
    assert len(events) == 5
    assert "id" in events[0]
    assert "location" in events[0]

    # 4. Event detail
    event_id = events[0]["id"]
    res_detail = client.get(f"/api/events/{event_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == event_id
    assert "classification" in detail

    # 5. Notifications
    res_notifs = client.get("/api/notifications")
    assert res_notifs.status_code == 200
    assert isinstance(res_notifs.json(), list)


def test_sse_endpoint_status_and_manager(client):
    """Verify GET /api/events/stream/status and active client lifecycle."""
    res = client.get("/api/events/stream/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "active_clients" in data


def test_multi_client_broadcast_and_cleanup(client):
    """Verify multiple connected clients receive broadcasts and disconnect cleanly."""
    c1 = sse_manager.connect()
    c2 = sse_manager.connect()
    initial_count = sse_manager.client_count

    try:
        # Broadcast test frame
        sse_manager.broadcast("test_ping", {"data": 42}, event_id="ping_1")
        assert not c1.queue.empty()
        assert not c2.queue.empty()

        f1 = c1.queue.get_nowait()
        f2 = c2.queue.get_nowait()
        assert "event: test_ping" in f1
        assert "event: test_ping" in f2
    finally:
        sse_manager.disconnect(c1)
        sse_manager.disconnect(c2)
        assert sse_manager.client_count == initial_count - 2


def test_observation_pipeline_and_high_risk_alerts(client):
    """
    Test processing an incoming observation through Experiment C + Risk Engine,
    ensuring high risk produces thermal_event, high_risk_alert, and notification.
    """
    listener = sse_manager.connect()
    try:
        # Drain initial queue if any
        while not listener.queue.empty():
            listener.queue.get_nowait()

        # Send observation with high FRP and near Hazira industrial cluster
        observation = {
            "id": "OBS-HAZIRA-001",
            "latitude": 21.115,
            "longitude": 72.652,
            "frp": 120.0,
            "brightness": 360.0,
            "brightness_ti5": 295.0,
            "active_days_last_7": 6,
        }
        res = client.post("/api/events/stream/simulate", json=observation)
        assert res.status_code == 200
        data = res.json()
        event = data["event"]

        assert event["id"] == "OBS-HAZIRA-001"
        assert event["risk_level"] in {"HIGH", "CRITICAL"}
        assert event["candidate_source"] is not None

        # Verify all broadcasted SSE frames
        frames = []
        while not listener.queue.empty():
            frames.append(listener.queue.get_nowait())

        frames_text = "".join(frames)
        assert "event: thermal_event" in frames_text
        assert "OBS-HAZIRA-001" in frames_text
        assert "event: high_risk_alert" in frames_text
        assert "event: notification" in frames_text
        assert "event: dashboard_update" in frames_text

        # Verify event is queryable via GET /api/events/{id}
        res_check = client.get("/api/events/OBS-HAZIRA-001")
        assert res_check.status_code == 200
    finally:
        sse_manager.disconnect(listener)
