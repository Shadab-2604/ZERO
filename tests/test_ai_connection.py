"""
Unit and integration tests for AI Connection Tester, Model Discovery,
Completion Verification, and Safe .env Configuration Updates.
All network requests are mocked to prevent external API calls and credit usage.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai.connection_tester import (
    AIConnectionTester,
    AuthTestResult,
    CompletionTestResult,
    DiagnosticReport,
)
from app.ai.providers.cloud_provider import CloudAIProvider
from app.api.server import create_app
from app.config.settings import Settings


# ---------------------------------------------------------------------------
# 1. Credential Redaction & Security Tests
# ---------------------------------------------------------------------------

def test_mask_key_redacts_credentials_safely():
    """Verify mask_key protects secrets without leaking sensitive tokens."""
    # Empty or None keys
    assert AIConnectionTester.mask_key("") == "[NOT CONFIGURED]"
    assert AIConnectionTester.mask_key(None) == "[NOT CONFIGURED]"  # type: ignore

    # Very short keys
    assert AIConnectionTester.mask_key("short") == "[REDACTED]"
    assert AIConnectionTester.mask_key("12345678") == "[REDACTED]"

    # Typical API keys
    masked = AIConnectionTester.mask_key("aak_akid_6931f409389fd4db07e42c37b8")
    assert "6931f409389fd4db07e42c37" not in masked
    assert masked.startswith("aak_")
    assert masked.endswith("37b8")
    assert "****" in masked


def test_authentication_aborts_without_api_key():
    """Verify authentication fails fast if no API key is configured."""
    tester = AIConnectionTester(api_key="")
    res = tester.test_authentication()
    assert not res.success
    assert res.category == "AUTH_FAILURE"
    assert "missing" in res.message.lower()


# ---------------------------------------------------------------------------
# 2. Authentication & Model Catalog Parsing Tests (Mocked)
# ---------------------------------------------------------------------------

def test_authentication_success_and_catalog_deduplication():
    """Verify HTTP 200 response parses and deduplicates models in order."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "object": "list",
        "data": [
            {"id": "gpt-4o-mini"},
            {"id": "gemini-1.5-flash"},
            {"id": "gpt-4o-mini"},  # Duplicate
            "claude-3-5-haiku",      # Plain string ID format
            {"id": ""},              # Empty ID should be ignored
        ],
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    tester = AIConnectionTester(api_key="sk-testkey1234567890")
    result = tester.test_authentication(client=mock_client)

    assert result.success is True
    assert result.status_code == 200
    assert result.category == "SUCCESS"
    assert len(result.models) == 3
    assert result.models == ["gpt-4o-mini", "gemini-1.5-flash", "claude-3-5-haiku"]


@pytest.mark.parametrize(
    "status_code,expected_category",
    [
        (401, "AUTH_FAILURE"),
        (403, "PERMISSION_DENIED"),
        (429, "RATE_LIMITED"),
        (500, "SERVER_ERROR"),
        (503, "SERVER_ERROR"),
    ],
)
def test_authentication_http_error_categories(status_code, expected_category):
    """Verify HTTP error status codes map to sanitized categories."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = {"error": {"message": "Simulated error"}}

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    tester = AIConnectionTester(api_key="sk-testkey1234567890")
    result = tester.test_authentication(client=mock_client)

    assert result.success is False
    assert result.status_code == status_code
    assert result.category == expected_category
    assert result.models == []


def test_authentication_network_timeout():
    """Verify ConnectTimeout maps to TIMEOUT category."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.ConnectTimeout("Connection timed out")

    tester = AIConnectionTester(api_key="sk-testkey1234567890")
    result = tester.test_authentication(client=mock_client)

    assert result.success is False
    assert result.category == "TIMEOUT"
    assert "timed out" in result.message.lower()


def test_authentication_invalid_json():
    """Verify invalid JSON payload on 200 is safely reported as SERVER_ERROR."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    tester = AIConnectionTester(api_key="sk-testkey1234567890")
    result = tester.test_authentication(client=mock_client)

    assert result.success is False
    assert result.category == "SERVER_ERROR"


# ---------------------------------------------------------------------------
# 3. Model Filtering and Candidate Prioritization
# ---------------------------------------------------------------------------

def test_filter_candidate_models_prioritizes_lightweight():
    """Verify lightweight/low-cost text models are prioritized over expensive ones."""
    catalog = [
        "text-embedding-3-small",  # Non-text (deprioritized/excluded)
        "claude-3-opus-20240229",  # Expensive frontier model (deprioritized)
        "dall-e-3",                # Image generation (excluded)
        "gpt-4o-mini",             # Lightweight Tier 1
        "claude-3-5-haiku",        # Lightweight Tier 1
        "whisper-1",               # Audio (excluded)
        "meta-llama/llama-3.1-8b", # Tier 2 general text
    ]

    tester = AIConnectionTester()
    candidates = tester.filter_candidate_models(catalog, max_candidates=3)

    assert "gpt-4o-mini" in candidates
    assert "claude-3-5-haiku" in candidates
    assert "dall-e-3" not in candidates
    assert "whisper-1" not in candidates
    assert "text-embedding-3-small" not in candidates
    assert len(candidates) <= 3


def test_filter_candidate_models_prioritizes_configured_preference():
    """Verify user's preferred model is prioritized first if available."""
    catalog = ["gpt-4o-mini", "claude-3-5-haiku", "deepseek-chat"]
    tester = AIConnectionTester()
    candidates = tester.filter_candidate_models(
        catalog,
        preferred_model="deepseek-chat",
        max_candidates=2,
    )
    assert candidates[0] == "deepseek-chat"


# ---------------------------------------------------------------------------
# 4. Chat Completion Testing (Mocked)
# ---------------------------------------------------------------------------

def test_model_completion_success():
    """Verify valid chat completion response is properly validated."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "chatcmpl-123",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Zero AI connection successful",
                },
                "finish_reason": "stop",
            }
        ],
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    tester = AIConnectionTester(api_key="sk-testkey1234567890")
    res = tester.test_model_completion("gpt-4o-mini", client=mock_client)

    assert res.success is True
    assert res.status_code == 200
    assert res.category == "SUCCESS"
    assert "Zero AI connection successful" in res.response_text


def test_model_completion_empty_choices():
    """Verify empty choices array is treated as CONTENT_MISMATCH."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "chatcmpl-123", "choices": []}

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    tester = AIConnectionTester(api_key="sk-testkey1234567890")
    res = tester.test_model_completion("gpt-4o-mini", client=mock_client)

    assert res.success is False
    assert res.category == "CONTENT_MISMATCH"


def test_model_completion_model_not_found():
    """Verify HTTP 404 maps to MODEL_NOT_FOUND."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": {"message": "Model not found"}}

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    tester = AIConnectionTester(api_key="sk-testkey1234567890")
    res = tester.test_model_completion("nonexistent-model", client=mock_client)

    assert res.success is False
    assert res.category == "MODEL_NOT_FOUND"


# ---------------------------------------------------------------------------
# 5. Safe .env File Update Tests
# ---------------------------------------------------------------------------

def test_safe_update_env_preserves_comments_and_secrets(tmp_path: Path):
    """Verify .env updater modifies only requested keys and preserves existing secrets."""
    env_file = tmp_path / ".env"
    initial_content = (
        "# Zero AI Configuration\n"
        "APP_NAME=Zero\n"
        "AI_PROVIDER=demo\n"
        "AI_API_KEY=aak_akid_secret_key_never_overwrite_12345\n"
        "AI_MODEL=\n"
        "# Database settings\n"
        "DATABASE_URL=sqlite:///zero.db\n"
    )
    env_file.write_text(initial_content, encoding="utf-8")

    tester = AIConnectionTester(env_path=env_file)
    success = tester.safe_update_env(
        {
            "AI_PROVIDER": "openai",
            "AI_API_BASE": "https://agent-router.net/aggregate/openai/v1",
            "AI_MODEL": "gpt-4o-mini",
        }
    )

    assert success is True
    updated = env_file.read_text(encoding="utf-8")

    # Verify target keys updated
    assert "AI_PROVIDER=openai\n" in updated
    assert "AI_API_BASE=https://agent-router.net/aggregate/openai/v1\n" in updated
    assert "AI_MODEL=gpt-4o-mini\n" in updated

    # Verify secret is perfectly preserved
    assert "AI_API_KEY=aak_akid_secret_key_never_overwrite_12345\n" in updated

    # Verify unrelated comments and settings preserved
    assert "# Zero AI Configuration\n" in updated
    assert "APP_NAME=Zero\n" in updated
    assert "# Database settings\n" in updated
    assert "DATABASE_URL=sqlite:///zero.db\n" in updated


def test_safe_update_env_handles_missing_file(tmp_path: Path):
    """Verify safe_update_env gracefully handles non-existent file."""
    env_file = tmp_path / "does_not_exist.env"
    tester = AIConnectionTester(env_path=env_file)
    assert tester.safe_update_env({"AI_MODEL": "gpt-4o-mini"}) is False


# ---------------------------------------------------------------------------
# 6. Full Diagnostic Flow Tests (Mocked)
# ---------------------------------------------------------------------------

def test_run_full_diagnostic_aborts_early_on_auth_failure(tmp_path: Path):
    """Verify diagnostic does not test models nor touch .env if auth fails."""
    env_file = tmp_path / ".env"
    env_file.write_text("AI_PROVIDER=demo\nAI_API_KEY=invalid_key\n", encoding="utf-8")

    tester = AIConnectionTester(
        api_key="invalid_key",
        env_path=env_file,
    )

    # Mock test_authentication to return 401 AUTH_FAILURE
    with patch.object(
        tester,
        "test_authentication",
        return_value=AuthTestResult(
            success=False,
            status_code=401,
            category="AUTH_FAILURE",
            message="Invalid key",
        ),
    ):
        report = tester.run_full_diagnostic()

        assert report.auth_result.success is False
        assert report.verified_models == []
        assert report.selected_model is None
        assert report.config_updated is False
        assert len(report.tested_candidates) == 0

        # Verify .env was not changed
        content = env_file.read_text(encoding="utf-8")
        assert "AI_PROVIDER=demo\n" in content


def test_run_full_diagnostic_success_flow(tmp_path: Path):
    """Verify complete diagnostic flow selects verified model and updates .env."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=demo\nAI_API_KEY=valid_key_12345678\nAI_MODEL=\n",
        encoding="utf-8",
    )

    tester = AIConnectionTester(
        api_base="https://agent-router.net/aggregate/openai/v1",
        api_key="valid_key_12345678",
        env_path=env_file,
    )

    # Mock auth success
    mock_auth = AuthTestResult(
        success=True,
        status_code=200,
        category="SUCCESS",
        message="Authentication successful",
        models=["gpt-4o-mini", "claude-3-5-haiku"],
    )

    # Mock completion success
    mock_comp = CompletionTestResult(
        model_id="gpt-4o-mini",
        success=True,
        status_code=200,
        category="SUCCESS",
        response_text="Zero AI connection successful",
        latency_ms=120.0,
    )

    with patch.object(tester, "test_authentication", return_value=mock_auth), \
         patch.object(tester, "test_model_completion", return_value=mock_comp):
        report = tester.run_full_diagnostic(target_verified_count=1)

        assert report.auth_result.success is True
        assert "gpt-4o-mini" in report.verified_models
        assert report.selected_model == "gpt-4o-mini"
        assert report.config_updated is True

        # Verify .env was updated
        updated_env = env_file.read_text(encoding="utf-8")
        assert "AI_PROVIDER=openai\n" in updated_env
        assert "AI_MODEL=gpt-4o-mini\n" in updated_env
        assert "AI_API_KEY=valid_key_12345678\n" in updated_env


# ---------------------------------------------------------------------------
# 7. Integration: API Route & CloudAIProvider URL Handling
# ---------------------------------------------------------------------------

def test_api_test_ai_connection_route():
    """Verify POST /api/settings/test-ai-connection returns sanitized diagnostic report."""
    app = create_app()
    with TestClient(app) as client:
        # Mock run_full_diagnostic inside route
        mock_report = DiagnosticReport(
            provider="Agent Router",
            api_base="https://agent-router.net/aggregate/openai/v1",
            api_key_redacted="aak_****2c37",
            auth_result=AuthTestResult(
                success=True,
                status_code=200,
                category="SUCCESS",
                message="Auth OK",
                models=["gpt-4o-mini"],
            ),
            models_discovered=1,
            verified_models=["gpt-4o-mini"],
            selected_model="gpt-4o-mini",
            selection_reason="Fastest verified",
            config_updated=False,
        )

        with patch.object(AIConnectionTester, "run_full_diagnostic", return_value=mock_report):
            response = client.post(
                "/api/settings/test-ai-connection",
                json={"api_base": "https://agent-router.net/aggregate/openai/v1"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "Agent Router"
            assert data["api_key"] == "aak_****2c37"
            assert data["selected_model"] == "gpt-4o-mini"
            assert data["authentication"]["success"] is True


def test_cloud_ai_provider_avoids_duplicate_chat_completions_url():
    """Verify CloudAIProvider normalizes API base URLs without path duplication."""
    # Case 1: Standard base URL
    p1 = CloudAIProvider(
        "openai",
        api_key="test-key",
        api_base="https://agent-router.net/aggregate/openai/v1",
    )
    assert p1.endpoint == "https://agent-router.net/aggregate/openai/v1/chat/completions"

    # Case 2: Base URL that already includes /chat/completions
    p2 = CloudAIProvider(
        "openai",
        api_key="test-key",
        api_base="https://agent-router.net/aggregate/openai/v1/chat/completions",
    )
    assert p2.endpoint == "https://agent-router.net/aggregate/openai/v1/chat/completions"

    # Case 3: Trailing slash
    p3 = CloudAIProvider(
        "openai",
        api_key="test-key",
        api_base="https://agent-router.net/aggregate/openai/v1/",
    )
    assert p3.endpoint == "https://agent-router.net/aggregate/openai/v1/chat/completions"
