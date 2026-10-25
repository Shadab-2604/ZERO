"""
Zero AI — Request and Application Coordination Controllers Facade.

Responsibilities:
- Central assistant lifecycle coordination (ZeroAssistant from app.core.assistant).
- Timezone-aware daily briefing controller (BriefingService from app.core.briefing_service).
- Intent routing and classification controller (IntentRouter from app.core.intent_router).
"""

from app.core.assistant import ZeroAssistant, get_assistant
from app.core.briefing_service import BriefingService
from app.core.intent_router import IntentRouter, IntentType

__all__ = [
    "ZeroAssistant",
    "get_assistant",
    "BriefingService",
    "IntentRouter",
    "IntentType",
]
