"""
Zero AI — Artificial Intelligence Abstraction & Local Ollama Subsystem.

Responsibilities:
- Local open-weight LLM inference via Ollama HTTP API (Llama 3.2, Qwen 2.5 Coder).
- Provider abstraction (BaseAIProvider) and factory (AIProviderFactory).
- Offline fallback and demo provider (DemoProvider).
- AI connectivity testing and diagnostics (AIConnectionTester).

Non-responsibilities:
- Speech recognition or audio synthesis (handled in app.voice).
- Intent classification or state management (handled in app.core).
"""

from app.ai.base import BaseAIProvider
from app.ai.local_service import LocalAIService, RouteTarget
from app.ai.provider_factory import AIProviderFactory
from app.ai.connection_tester import AIConnectionTester

__all__ = [
    "BaseAIProvider",
    "LocalAIService",
    "RouteTarget",
    "AIProviderFactory",
    "AIConnectionTester",
]
