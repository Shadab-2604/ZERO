"""
Tests covering Configuration, Security, Secret Redaction, and API Loopback Binding.
Covers:
- Scenario 1: Application starts with no .env file
- Scenario 14: Secrets do not appear in logs or API responses
- Scenario 15: Invalid API requests are rejected safely
- Scenario 16: The API binds to loopback by default
"""

import os
import pytest
from app.config.settings import Settings
from app.config.logging_config import RedactingFormatter
import logging
from fastapi.testclient import TestClient
from app.api.server import create_app


def test_app_starts_with_no_env_file(tmp_path, monkeypatch):
    """Scenario 1: Validate default settings load cleanly when no .env exists."""
    # Ensure no environment variables override defaults
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Point to nonexistent env file
    settings = Settings(_env_file=tmp_path / "nonexistent.env")
    assert settings.app_name == "Zero"
    assert settings.ai_provider == "demo"
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 8765
    assert settings.ai_api_key == ""


def test_secrets_do_not_appear_in_logs():
    """Scenario 14a: Verify RedactingFormatter sanitizes secret keys."""
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Connecting with api-key=sk-1234567890abcdef and password=secretpass",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "sk-1234567890abcdef" not in formatted
    assert "secretpass" not in formatted
    assert "[REDACTED]" in formatted


def test_secrets_do_not_appear_in_public_settings_and_api():
    """Scenario 14b: Verify public settings endpoint masks secrets."""
    settings = Settings(AI_API_KEY="super_secret_token_12345", AI_PROVIDER="openai")
    public_dict = settings.get_public_dict()

    assert "super_secret_token_12345" not in str(public_dict)
    assert public_dict["ai_api_key_status"] == "configured (••••••••)"

    # Test via FastAPI test client
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/settings/public")
    assert response.status_code == 200
    res_json = response.json()
    assert "super_secret_token_12345" not in str(res_json)


def test_api_binds_to_loopback_by_default():
    """Scenario 16: Verify API host defaults strictly to 127.0.0.1."""
    settings = Settings()
    assert settings.app_host in ("127.0.0.1", "localhost")


def test_invalid_api_requests_rejected_safely():
    """Scenario 15: Invalid payloads return 422 Unprocessable Entity safely."""
    app = create_app()
    client = TestClient(app)

    # Empty payload to chat
    response = client.post("/api/assistant/chat", json={})
    assert response.status_code == 422

    # Wrong data types
    response = client.post("/api/assistant/chat", json={"message": 12345})
    assert response.status_code == 422

    # Exceeding max length
    oversized_message = "x" * 5000
    response = client.post("/api/assistant/chat", json={"message": oversized_message})
    assert response.status_code == 422
