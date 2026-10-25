"""
Integration tests for Zero AI local REST API endpoints.
Validates HTTP response codes, payload structure, and state consistency.
"""

import pytest
from fastapi.testclient import TestClient
from app.api.server import create_app
from app.memory.database import init_db
from app.core.assistant import get_assistant


@pytest.fixture(scope="module")
def client():
    init_db()
    assistant = get_assistant()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_get_health(client):
    """Test GET /health returns real subsystem health."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "mode" in data
    assert "database" in data
    assert "ai_provider" in data
    assert "resources" in data


def test_assistant_state_endpoints(client):
    """Test GET /api/assistant/state and wake/sleep transitions."""
    # 1. State initial
    res_state = client.get("/api/assistant/state")
    assert res_state.status_code == 200
    assert "state" in res_state.json()

    # 2. Wake
    res_wake = client.post("/api/assistant/wake")
    assert res_wake.status_code == 200
    assert res_wake.json()["status"] == "awakened"

    # 3. Chat
    res_chat = client.post(
        "/api/assistant/chat",
        json={"message": "Give me an operational status update"},
    )
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    assert "reply" in chat_data
    assert len(chat_data["reply"]) > 0

    # 4. Sleep
    res_sleep = client.post("/api/assistant/sleep")
    assert res_sleep.status_code == 200
    assert res_sleep.json()["status"] == "sleeping"


def test_briefing_and_activity_endpoints(client):
    """Test GET /api/briefing/today and GET /api/activity/recent."""
    # Briefing
    res_briefing = client.get("/api/briefing/today")
    assert res_briefing.status_code == 200
    briefing_data = res_briefing.json()
    assert "text" in briefing_data
    assert briefing_data["delivered"] is True

    # Activity
    res_activity = client.get("/api/activity/recent?limit=5")
    assert res_activity.status_code == 200
    act_data = res_activity.json()
    assert "activities" in act_data
    assert isinstance(act_data["activities"], list)


def test_settings_public_endpoint(client):
    """Test GET /api/settings/public returns safe settings."""
    response = client.get("/api/settings/public")
    assert response.status_code == 200
    settings_data = response.json()
    assert settings_data["app_name"] == "Zero"
    assert "ai_api_key_status" in settings_data
    assert "ai_api_key" not in settings_data
