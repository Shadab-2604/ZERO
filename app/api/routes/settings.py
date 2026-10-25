"""
Safe settings inspection, preference updates, and AI connection diagnostics routes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.config.settings import get_settings
from app.memory.activity_store import ActivityStore
from app.ai.connection_tester import AIConnectionTester

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class PreferenceUpdateRequest(BaseModel):
    key: str
    value: str


class ConnectionTestRequest(BaseModel):
    api_base: str | None = None
    api_key: str | None = None
    update_env: bool = False


@router.get("/public")
def get_public_settings():
    """Return safe public configuration dictionary without any secrets."""
    settings = get_settings()
    return settings.get_public_dict()


@router.post("/preference")
def update_preference(req: PreferenceUpdateRequest):
    """Update a persistent user preference."""
    ActivityStore.set_preference(req.key, req.value)
    return {"status": "updated", "key": req.key, "value": req.value}


@router.post("/test-ai-connection")
def test_ai_connection(req: ConnectionTestRequest = ConnectionTestRequest()):
    """
    Test live AI connection against Agent Router or OpenAI-compatible endpoint.
    Performs authentication and completion checks and returns sanitized diagnostics.
    """
    settings = get_settings()
    api_base = req.api_base or settings.ai_api_base or "https://agent-router.net/aggregate/openai/v1"
    api_key = req.api_key or settings.ai_api_key

    tester = AIConnectionTester(
        api_base=api_base,
        api_key=api_key,
        timeout=settings.ai_timeout,
    )
    report = tester.run_full_diagnostic(
        preferred_model=settings.ai_model,
        update_env_on_success=req.update_env,
    )
    return report.to_dict()
