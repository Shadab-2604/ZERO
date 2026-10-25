"""
Cloud API-backed AI provider for Zero using HTTP requests (OpenAI-compatible / Generic LLM API).
"""

import logging
import httpx
from app.ai.base import BaseAIProvider
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class CloudAIProvider(BaseAIProvider):
    """
    Cloud-backed LLM provider supporting OpenAI, Gemini OpenAI-compatible,
    Ollama, and compatible REST inference endpoints.
    """

    def __init__(
        self,
        provider_name: str,
        api_key: str,
        model_name: str | None = None,
        api_base: str | None = None,
        timeout: float = 30.0,
    ):
        self._provider_name = provider_name
        self._api_key = api_key
        self._model_name = model_name or self._default_model_for(provider_name)
        self._api_base = api_base or self._default_base_for(provider_name)
        self._timeout = timeout

    def _default_model_for(self, provider: str) -> str:
        provider = provider.lower()
        if "openai" in provider:
            return "gpt-4o-mini"
        elif "gemini" in provider:
            return "gemini-1.5-flash"
        elif "anthropic" in provider:
            return "claude-3-5-sonnet-20241022"
        elif "ollama" in provider:
            return "llama3"
        return "gpt-3.5-turbo"

    def _default_base_for(self, provider: str) -> str:
        provider = provider.lower()
        if "openai" in provider:
            return "https://api.openai.com/v1"
        elif "gemini" in provider:
            return "https://generativelanguage.googleapis.com/v1beta/openai"
        elif "ollama" in provider:
            return "http://localhost:11434/v1"
        return "https://api.openai.com/v1"

    @property
    def name(self) -> str:
        return f"Cloud Provider ({self._provider_name}: {self._model_name})"

    @property
    def endpoint(self) -> str:
        """Resolved chat completions endpoint avoiding path duplication."""
        base = (self._api_base or "").rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    @property
    def is_available(self) -> bool:
        if "ollama" in self._provider_name.lower():
            return True
        return bool(self._api_key and len(self._api_key.strip()) > 0)

    def generate_response(
        self, messages: list[dict], system_prompt: str | None = None
    ) -> str:
        settings = get_settings()
        if not settings.external_ai_enabled:
            from urllib.parse import urlparse
            parsed = urlparse(self.endpoint)
            hostname = (parsed.hostname or "").lower()
            if hostname not in ("127.0.0.1", "localhost", "::1"):
                raise RuntimeError(
                    f"External AI is disabled (EXTERNAL_AI_ENABLED=false). Blocked request to external host '{hostname}'."
                )

        if not self.is_available:
            raise ValueError(
                f"API Key for {self._provider_name} is not configured in .env."
            )

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        for m in messages:
            payload_messages.append({"role": m["role"], "content": m["content"]})

        url = self.endpoint

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        data = {
            "model": self._model_name,
            "messages": payload_messages,
            "temperature": 0.7,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=data, headers=headers)
                response.raise_for_status()
                json_data = response.json()
                content = json_data["choices"][0]["message"]["content"]
                return content.strip()
        except httpx.HTTPStatusError as e:
            logger.error("Cloud provider HTTP error: %s", e.response.status_code)
            raise RuntimeError(f"Cloud provider returned error: {e.response.status_code}")
        except Exception as e:
            logger.error("Cloud provider request failed: %s", type(e).__name__)
            raise RuntimeError(f"Failed to communicate with {self._provider_name}: {str(e)}")

    def generate_summary(self, text: str) -> str:
        """Generate summary via cloud provider."""
        prompt = (
            "Summarize the following project and session activity concisely in 2-3 sentences. "
            "Focus on accomplishments and pending items:\n\n" + text
        )
        return self.generate_response(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are ZERO, an intelligent executive assistant summarizing project activity.",
        )
