"""
Zero AI — Core Assistant Engine & Lifecycle Orchestration.

Responsibilities:
- State Machine management (AssistantState: SLEEPING, LISTENING, HEARING_YOU, PROCESSING, SPEAKING, INTERRUPTED).
- Natural language intent classification and routing (IntentRouter).
- Assistant conversation orchestration (ZeroAssistant).
- Timezone-aware daily briefing generation (BriefingService).
- Safe deterministic calculations (ZeroCalculator).
"""

from app.core.assistant import ZeroAssistant
from app.core.state_manager import AssistantState, StateManager
from app.core.intent_router import IntentRouter, IntentType
from app.core.briefing_service import BriefingService
from app.core.conversation_manager import ConversationManager

__all__ = [
    "ZeroAssistant",
    "AssistantState",
    "StateManager",
    "IntentRouter",
    "IntentType",
    "BriefingService",
    "ConversationManager",
]
