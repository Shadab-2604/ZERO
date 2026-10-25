"""
Zero AI — Local AI Subsystem & Ollama Model Routing Engine.

Purpose:
Coordinates 100% offline open-weight language model inference via the local
Ollama REST API (`http://127.0.0.1:11434`). Applies dual-model routing between
general conversational models and specialized coding models, backed by local
deterministic calculation safeguards.

Responsibilities:
- Triaging user prompts into `CALCULATION`, `CODE`, or `CHAT` route targets:
  - `CALCULATION`: Handled deterministically by `LocalCalculator` (zero hallucination).
  - `CODE`: Routed to `qwen2.5-coder:7b` for code synthesis, debugging, and SQL analysis.
  - `CHAT`: Routed to `llama3.2:latest` (3B) for fast natural dialogue and daily briefings.
- Augmenting prompt context with retrieved RAG knowledge passages.
- Managing HTTP client connection pooling, request timeouts, and error recovery.

Important Dependencies & Integrations:
- Ollama runtime (`http://127.0.0.1:11434`).
- `httpx`: High-performance asynchronous and synchronous HTTP client.
- `app.core.calculator.LocalCalculator`: Safe AST-based deterministic arithmetic engine.

Deliberately Does Not Handle:
- Parsing, indexing, or chunking raw documents (handled strictly in `app.knowledge`).
- Storing conversation messages or audit history (handled strictly in `app.memory`).
- Direct audio capture or TTS voice rendering (handled strictly in `app.voice`).
"""

from enum import Enum
import json
import logging
import re
from typing import Any
import httpx

from app.ai.base import BaseAIProvider
from app.config.settings import get_settings
from app.core.calculator import LocalCalculator, CalculationResult

logger = logging.getLogger(__name__)


class RouteTarget(str, Enum):
    """Routing targets for user input processing."""
    CALCULATION = "CALCULATION"
    CODE = "CODE"
    CHAT = "CHAT"


class LocalAIService(BaseAIProvider):
    """
    Central local AI inference and model routing engine for Zero AI.
    
    Routes user requests between Python AST deterministic evaluation and local
    Ollama models (Llama 3.2 for dialogue, Qwen 2.5 Coder for programming).
    """

    # Keyword and syntax patterns for detecting coding/programming queries
    CODE_KEYWORDS = {
        "python", "javascript", "typescript", "html", "css", "sql", "bash",
        "powershell", "rust", "golang", "c++", "c#", "java", "ruby", "php",
        "function", "class", "script", "algorithm", "debug", "refactor",
        "syntax", "regex", "traceback", "exception", "compile", "compiler",
        "docstring", "type hint", "type annotation", "unittest", "pytest",
        "git", "docker", "fastapi", "flask", "pyside", "qt", "react", "vue",
        "code", "coding", "program", "programming", "implement", "snippet",
        "method", "decorator", "variable", "recursion", "hashlib",
        "query", "queries", "join", "database", "table", "schema", "endpoint",
        "indexerror", "typeerror", "valueerror", "keyerror", "attributeerror",
        "syntaxerror", "nameerror", "zerodivisionerror", "importerror", "modulenotfounderror",
    }

    CODE_PATTERNS = [
        re.compile(r"```[a-zA-Z0-9_\+\-]*\n"),  # Markdown code blocks
        re.compile(r"\b(def|class|fn|func|function|import|export|return)\b\s+[a-zA-Z0-9_]+"),
        re.compile(r"\b(write|create|implement|debug|fix|explain)\b.*?\b(code|function|script|class|algorithm|regex|query|sql|database|table|error|bug|issue)\b", re.IGNORECASE),
        re.compile(r"\b(how\s+to\s+code|how\s+to\s+implement|write\s+a\s+program|fix\s+this|debug\s+this)\b", re.IGNORECASE),
        re.compile(r"\b(syntax|runtime|index|key|type|value|attribute|name|import)\s*error\b", re.IGNORECASE),
    ]

    def __init__(
        self,
        api_base: str | None = None,
        chat_model: str | None = None,
        code_model: str | None = None,
        timeout: float = 60.0,
    ):
        settings = get_settings()
        self._api_base = (api_base or settings.ai_api_base or "http://127.0.0.1:11434/v1").rstrip("/")
        # Derive Ollama native base (strip /v1 if present for direct api checks)
        self._ollama_base = re.sub(r"/v1/?$", "", self._api_base)
        self._chat_model = chat_model or settings.local_chat_model or "llama3.2"
        self._code_model = code_model or settings.local_code_model or "qwen2.5-coder:3b"
        self._timeout = timeout

    @property
    def name(self) -> str:
        return f"Local Ollama Service (Chat: {self._chat_model}, Code: {self._code_model})"

    @property
    def is_available(self) -> bool:
        """Check if local Ollama daemon is reachable."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self._ollama_base}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    def list_installed_models(self) -> list[str]:
        """Fetch list of model tags currently available in local Ollama instance."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self._ollama_base}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = data.get("models", [])
                    tags = []
                    for m in models:
                        name = m.get("name", "")
                        if name:
                            tags.append(name)
                            # Also include short name (e.g. 'llama3.2' for 'llama3.2:latest')
                            if ":" in name:
                                tags.append(name.split(":")[0])
                    return list(set(tags))
        except Exception as e:
            logger.warning("Could not query Ollama installed models: %s", e)
        return []

    def classify_route(self, text: str) -> tuple[RouteTarget, Any]:
        """
        Determine whether query is arithmetic calculation, coding, or general chat.
        Returns (RouteTarget, route_metadata).
        """
        # 1. Deterministic Calculation Check
        calc_result = LocalCalculator.try_calculate(text)
        if calc_result.is_calculation:
            return RouteTarget.CALCULATION, calc_result

        # 2. Coding and Programming Check
        normalized_lower = text.lower()
        words = set(re.findall(r"\b[a-zA-Z0-9_\+\-]+\b", normalized_lower))

        # Check keyword intersection
        if len(words.intersection(self.CODE_KEYWORDS)) >= 2:
            return RouteTarget.CODE, self._code_model

        # Check explicit code regex patterns
        for pattern in self.CODE_PATTERNS:
            if pattern.search(text):
                return RouteTarget.CODE, self._code_model

        # Check for single high-signal coding words
        high_signal_words = {"docstring", "typehint", "pytest", "unittest", "traceback", "regex"}
        if words.intersection(high_signal_words):
            return RouteTarget.CODE, self._code_model

        # 3. Default to General Chat (Llama)
        return RouteTarget.CHAT, self._chat_model

    def generate_response(
        self, messages: list[dict], system_prompt: str | None = None
    ) -> str:
        """
        Route message thread to calculation engine, Qwen Coder, or Llama.
        Executes strictly on local loopback.
        """
        settings = get_settings()

        # Enforce local-only network boundary
        if not settings.external_ai_enabled:
            from urllib.parse import urlparse
            parsed = urlparse(self._ollama_base)
            hostname = (parsed.hostname or "").lower()
            if hostname not in ("127.0.0.1", "localhost", "::1"):
                raise RuntimeError(
                    f"External AI is disabled (EXTERNAL_AI_ENABLED=false). Cannot connect to remote host '{hostname}'."
                )

        # Get latest user message to classify route
        latest_user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                latest_user_text = m.get("content", "")
                break

        route_target, metadata = self.classify_route(latest_user_text)

        # Case 1: Exact deterministic arithmetic calculation
        if route_target == RouteTarget.CALCULATION and isinstance(metadata, CalculationResult):
            logger.info("Executing local deterministic calculation: %s", metadata.expression)
            return metadata.explanation

        # Determine target model
        target_model = self._code_model if route_target == RouteTarget.CODE else self._chat_model
        logger.info("Routing query to model '%s' (Route: %s)", target_model, route_target.value)

        # Verify Ollama server connectivity
        installed_models = self.list_installed_models()
        if not installed_models and not self.is_available:
            raise RuntimeError(
                f"Local Ollama service is not reachable at {self._ollama_base}. "
                "Please verify that Ollama is running on your computer."
            )

        # Verify model exists locally
        short_target = target_model.split(":")[0]
        if installed_models and not any(
            target_model == m or short_target == m or f"{short_target}:latest" == m
            for m in installed_models
        ):
            raise RuntimeError(
                f"Local model '{target_model}' is not installed in Ollama. "
                f"Please open PowerShell and run: ollama pull {target_model}"
            )

        # Build payload
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        for m in messages:
            payload_messages.append({"role": m["role"], "content": m["content"]})

        chat_url = f"{self._ollama_base}/api/chat"
        payload = {
            "model": target_model,
            "messages": payload_messages,
            "stream": False,
            "options": {
                "temperature": 0.3 if route_target == RouteTarget.CODE else 0.7,
                "num_ctx": 4096,
            },
            "keep_alive": "5m",
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(chat_url, json=payload)
                response.raise_for_status()
                data = response.json()
                msg = data.get("message", {})
                content = msg.get("content", "") or data.get("response", "")
                if not content.strip():
                    logger.warning("Empty response from %s, retrying once...", target_model)
                    import time
                    time.sleep(0.5)
                    retry_res = client.post(chat_url, json=payload)
                    retry_data = retry_res.json()
                    content = retry_data.get("message", {}).get("content", "") or retry_data.get("response", "")
                if not content.strip():
                    return f"I processed your query, but model '{target_model}' returned an empty reply. Please try rephrasing or asking again."
                return content.strip()
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to local Ollama daemon at {self._ollama_base}. "
                "Ensure Ollama is started locally."
            )
        except httpx.TimeoutException:
            raise RuntimeError(
                f"Inference request to model '{target_model}' timed out after {self._timeout}s. "
                "Your computer may be experiencing heavy load."
            )
        except httpx.HTTPStatusError as e:
            err_detail = ""
            try:
                err_detail = e.response.json().get("error", "")
            except Exception:
                err_detail = e.response.text
            raise RuntimeError(f"Ollama returned HTTP error {e.response.status_code}: {err_detail}")
        except Exception as e:
            logger.error("Local inference error on model %s: %s", target_model, e)
            raise RuntimeError(f"Local AI inference error: {str(e)}")

    def generate_summary(self, text: str) -> str:
        """Generate concise summary using local chat model."""
        prompt = (
            "Summarize the following project and session activity concisely in 2-3 sentences. "
            "Focus on accomplishments and pending items:\n\n" + text
        )
        return self.generate_response(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are ZERO, an intelligent executive assistant summarizing project activity.",
        )
