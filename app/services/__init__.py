"""
Zero AI — High-Level Services Facade.

Responsibilities:
- Windows desktop automation and system awareness (DesktopControlService from app.services.desktop_control).
- Local AI model inference and routing (LocalAIService from app.ai.local_service).
- Voice streaming, speech recognition, and TTS coordination (VoiceManager from app.voice.manager).
- Knowledge ingestion, indexing, and RAG retrieval (KnowledgeService from app.knowledge.service).
- Timezone-aware daily briefing service (BriefingService from app.core.briefing_service).
"""

from app.services.desktop_control import DesktopControlService, get_desktop_service
from app.ai.local_service import LocalAIService
from app.voice.manager import VoiceManager
from app.knowledge.service import KnowledgeService, get_knowledge_service
from app.core.briefing_service import BriefingService

__all__ = [
    "DesktopControlService",
    "get_desktop_service",
    "LocalAIService",
    "VoiceManager",
    "KnowledgeService",
    "get_knowledge_service",
    "BriefingService",
]
