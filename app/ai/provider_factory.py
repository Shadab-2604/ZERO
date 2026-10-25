"""
Factory for creating and switching AI providers based on application configuration.
"""

import logging
from app.ai.base import BaseAIProvider
from app.ai.providers.demo_provider import DemoAIProvider
from app.ai.providers.cloud_provider import CloudAIProvider
from app.ai.local_service import LocalAIService
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """Instantiates configured AI provider or provides safe local demo fallback."""

    @staticmethod
    def get_provider() -> BaseAIProvider:
        """Create provider according to settings."""
        import os
        env_provider = os.getenv("AI_PROVIDER")
        settings = get_settings(reload=bool(env_provider))
        provider_type = (env_provider or settings.ai_provider).strip().lower()

        # 1. Explicit demo provider requested
        if provider_type == "demo":
            logger.info("Using Local Demo AI Provider (Zero offline mode).")
            return DemoAIProvider()

        # 2. Local-only mode or Ollama provider explicitly selected
        if provider_type == "ollama" or settings.zero_mode == "local_only":
            logger.info(
                "Initializing Local AI Service (Ollama: Chat=%s, Code=%s).",
                settings.local_chat_model,
                settings.local_code_model,
            )
            return LocalAIService(
                api_base=settings.ai_api_base,
                chat_model=settings.local_chat_model,
                code_model=settings.local_code_model,
                timeout=settings.ai_timeout,
            )

        # 3. Cloud provider with external AI enabled
        if not settings.external_ai_enabled:
            logger.warning(
                "Cloud provider '%s' requested, but EXTERNAL_AI_ENABLED is false. Routing to LocalAIService.",
                provider_type,
            )
            return LocalAIService(
                api_base=settings.ai_api_base,
                chat_model=settings.local_chat_model,
                code_model=settings.local_code_model,
                timeout=settings.ai_timeout,
            )

        if not settings.ai_api_key:
            logger.warning(
                "Provider '%s' specified, but AI_API_KEY is missing. Falling back to DemoAIProvider.",
                provider_type,
            )
            return DemoAIProvider()

        try:
            logger.info("Initializing Cloud AI Provider: %s", provider_type)
            return CloudAIProvider(
                provider_name=provider_type,
                api_key=settings.ai_api_key,
                model_name=settings.ai_model,
                api_base=settings.ai_api_base,
                timeout=settings.ai_timeout,
            )
        except Exception as e:
            logger.error("Failed to initialize cloud provider %s: %s. Falling back to Demo.", provider_type, e)
            return DemoAIProvider()
