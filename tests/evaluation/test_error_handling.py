"""
Tests for Robustness, Error Handling, and Recovery.
Phase 11 & 14 Evaluation: Fault Tolerance.
"""

from unittest.mock import MagicMock, patch
import httpx
import pytest
from app.ai.local_service import LocalAIService
from app.core.assistant import ZeroAssistant


def test_err_001_empty_model_response_safe_recovery():
    """Verify empty LLM reply produces diagnostic notice instead of silent crash."""
    service = LocalAIService()
    with patch("httpx.Client.post") as mock_post, patch.object(service, "list_installed_models", return_value=["llama3.2"]):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"content": ""}, "response": ""}
        mock_post.return_value = mock_resp

        reply = service.generate_response([{"role": "user", "content": "hello"}])
        assert "empty reply" in reply.lower() or "rephrasing" in reply.lower()


def test_err_002_ollama_daemon_unreachable():
    """Verify daemon disconnection produces clear guidance, not unhandled stack trace."""
    from unittest.mock import PropertyMock
    service = LocalAIService()
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")), \
         patch.object(service, "list_installed_models", return_value=[]), \
         patch.object(type(service), "is_available", new_callable=PropertyMock, return_value=False):
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_response([{"role": "user", "content": "hello"}])
        assert "not reachable" in str(exc_info.value).lower()


def test_err_003_inference_timeout_recovery():
    """Verify inference timeout raises actionable error without crashing app."""
    service = LocalAIService(timeout=0.1)
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")), \
         patch.object(service, "list_installed_models", return_value=["llama3.2"]):
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_response([{"role": "user", "content": "hello"}])
        assert "timed out" in str(exc_info.value).lower()
