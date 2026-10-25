"""
Daily briefing and project activity API endpoints.
"""

from fastapi import APIRouter
from app.core.assistant import get_assistant
from app.memory.activity_store import ActivityStore

router = APIRouter(prefix="/api", tags=["Briefing & Activity"])


@router.get("/briefing/today")
def get_today_briefing():
    """Retrieve or generate today's briefing."""
    assistant = get_assistant()
    return assistant.briefing_service.generate_briefing(force=True)


@router.get("/activity/recent")
def get_recent_activity(limit: int = 15):
    """Retrieve recent stored project activity records."""
    safe_limit = max(1, min(limit, 100))
    return {
        "count": safe_limit,
        "activities": ActivityStore.get_recent_activities(limit=safe_limit),
    }
