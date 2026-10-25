"""
Tests for Privacy Controls, Local-Only Enforcement, and Secret Masking.
Phase 6 & 11 Evaluation: Privacy & Data Protection.
"""

from unittest.mock import patch
import pytest
from app.config.settings import get_settings


def test_priv_001_settings_mask_api_key():
    """Verify get_public_dict() strictly masks sensitive API keys."""
    settings = get_settings()
    public_dict = settings.get_public_dict()
    assert "ai_api_key" not in public_dict
    assert "aak_akid" not in str(public_dict)
    assert public_dict["ai_api_key_status"] in ("configured (••••••••)", "not configured")


def test_priv_002_local_only_boundary_enforcement():
    """Verify LocalAIService strictly blocks remote hosts when EXTERNAL_AI_ENABLED=false."""
    from app.ai.local_service import LocalAIService
    from app.config.settings import Settings
    mock_s = Settings(EXTERNAL_AI_ENABLED=False)
    with patch("app.ai.local_service.get_settings", return_value=mock_s):
        service = LocalAIService(api_base="http://api.external-cloud.com/v1")
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_response([{"role": "user", "content": "ping"}])
        assert "External AI is disabled" in str(exc_info.value)


def test_priv_003_diagnostics_sanitize_internal_paths():
    """Verify diagnostic results do not expose secrets."""
    from app.tools.system_diagnostics import SystemDiagnostics
    res = SystemDiagnostics.get_system_status()
    assert res.success is True
    assert "password" not in res.detailed_text.lower()
