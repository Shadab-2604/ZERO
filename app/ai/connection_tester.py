"""
Automatic AI Provider Connection Tester & Model Selector for Agent Router / OpenAI-compatible APIs.
Performs authentication verification, model discovery, completion validation,
and safe non-destructive configuration updates without leaking credentials.
"""

from dataclasses import dataclass, field
import logging
import os
import re
import time
from pathlib import Path
from typing import Any
import httpx
from app.utils.paths import get_env_file_path

logger = logging.getLogger(__name__)

# Patterns for lightweight/cost-effective models
_LIGHTWEIGHT_KEYWORDS = [
    "mini",
    "flash",
    "haiku",
    "turbo",
    "small",
    "lite",
    "deepseek-chat",
    "deepseek-v3",
    "3.5-turbo",
    "4o-mini",
]

# Patterns for models that should be deprioritized/avoided in automatic lightweight testing
_EXPENSIVE_KEYWORDS = [
    "opus",
    "o1",
    "o3",
    "embed",
    "dall-e",
    "whisper",
    "tts",
    "moderation",
    "rerank",
    "bge",
    "realtime",
    "audio",
]


@dataclass
class AuthTestResult:
    """Result of API authentication and catalog inspection."""
    success: bool
    status_code: int | None
    category: str  # SUCCESS, AUTH_FAILURE, PERMISSION_DENIED, RATE_LIMITED, SERVER_ERROR, NETWORK_ERROR, TIMEOUT
    message: str
    models: list[str] = field(default_factory=list)
    latency_ms: float = 0.0


@dataclass
class CompletionTestResult:
    """Result of testing an individual model's chat completion."""
    model_id: str
    success: bool
    status_code: int | None
    category: str  # SUCCESS, AUTH_FAILURE, MODEL_NOT_FOUND, RATE_LIMITED, SERVER_ERROR, CONTENT_MISMATCH, TIMEOUT, NETWORK_ERROR
    response_text: str = ""
    latency_ms: float = 0.0
    error_message: str | None = None


@dataclass
class DiagnosticReport:
    """Consolidated diagnostic report with sanitized credentials."""
    provider: str
    api_base: str
    api_key_redacted: str
    auth_result: AuthTestResult
    models_discovered: int
    tested_candidates: list[CompletionTestResult] = field(default_factory=list)
    verified_models: list[str] = field(default_factory=list)
    selected_model: str | None = None
    selection_reason: str = ""
    config_updated: bool = False
    error_report: str | None = None
    suggested_fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert report to JSON-serializable dictionary."""
        return {
            "provider": self.provider,
            "api_base": self.api_base,
            "api_key": self.api_key_redacted,
            "authentication": {
                "success": self.auth_result.success,
                "status_code": self.auth_result.status_code,
                "category": self.auth_result.category,
                "message": self.auth_result.message,
                "latency_ms": round(self.auth_result.latency_ms, 2),
            },
            "models_discovered": self.models_discovered,
            "tested_candidates": [
                {
                    "model_id": c.model_id,
                    "success": c.success,
                    "status_code": c.status_code,
                    "category": c.category,
                    "response_snippet": c.response_text[:80] if c.response_text else "",
                    "latency_ms": round(c.latency_ms, 2),
                    "error": c.error_message,
                }
                for c in self.tested_candidates
            ],
            "verified_models": self.verified_models,
            "selected_model": self.selected_model,
            "selection_reason": self.selection_reason,
            "configuration_updated": self.config_updated,
            "error_report": self.error_report,
            "suggested_fix": self.suggested_fix,
        }

    def format_terminal_report(self) -> str:
        """Render readable diagnostic terminal output as requested."""
        auth_status = "SUCCESS" if self.auth_result.success else f"FAILED ({self.auth_result.category})"
        catalog_status = f"LOADED ({self.models_discovered} models)" if self.models_discovered > 0 else "EMPTY / FAILED"
        verified_str = str(self.verified_models) if self.verified_models else "None"
        selected_str = self.selected_model or "None"
        completion_status = "SUCCESS" if self.verified_models else "FAILED"
        config_status = "SUCCESS" if self.config_updated else "UNCHANGED"

        lines = [
            "==================================================",
            "          ZERO AI CONNECTION DIAGNOSTICS",
            "--------------------------------------------------",
            f"Provider:             {self.provider}",
            f"API Base:             {self.api_base}",
            f"API authentication:   {auth_status}",
            f"Model catalog:        {catalog_status}",
            f"Verified models:      {verified_str}",
            f"Selected model:       {selected_str}",
            f"Completion test:      {completion_status}",
            f"Configuration update: {config_status}",
            f"API key:              {self.api_key_redacted}",
            "--------------------------------------------------",
        ]

        if not self.auth_result.success or not self.verified_models:
            lines.append("DIAGNOSTIC NOTICE:")
            if self.error_report:
                lines.append(f"  Issue: {self.error_report}")
            if self.suggested_fix:
                lines.append(f"  Action: {self.suggested_fix}")
            lines.append("--------------------------------------------------")
        else:
            lines.append(f"Selection Reason: {self.selection_reason}")
            lines.append("Zero AI is ready for live neural inference.")
            lines.append("--------------------------------------------------")

        return "\n".join(lines)


class AIConnectionTester:
    """Tests and configures AI provider connection."""

    def __init__(
        self,
        api_base: str = "https://agent-router.net/aggregate/openai/v1",
        api_key: str | None = None,
        timeout: float = 15.0,
        env_path: Path | None = None,
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = (api_key or "").strip()
        # For local endpoints (Ollama / local loopback), a real API key is not required
        is_loopback = any(h in self.api_base for h in ("127.0.0.1", "localhost", "::1"))
        if is_loopback and not self.api_key:
            self.api_key = "ollama"  # Documented local compatibility placeholder
        self.timeout = timeout
        self.env_path = env_path or get_env_file_path()

    @staticmethod
    def mask_key(key: str) -> str:
        """Return masked key safely hiding secrets."""
        if not key:
            return "[NOT CONFIGURED]"
        if key == "ollama":
            return "[LOCAL / OLLAMA]"
        if len(key) <= 8:
            return "[REDACTED]"
        return f"{key[:4]}****{key[-4:]}"

    def _get_headers(self) -> dict[str, str]:
        """Construct standard OpenAI-compatible auth headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Zero-AI-Assistant/1.0",
        }

    def test_authentication(self, client: httpx.Client | None = None) -> AuthTestResult:
        """
        Verify credentials by querying GET {api_base}/models.
        Handles HTTP 200, 401, 403, 429, 5xx, timeouts, and network errors.
        """
        if not self.api_key:
            return AuthTestResult(
                success=False,
                status_code=None,
                category="AUTH_FAILURE",
                message="API key is missing in configuration. Please provide a valid AI_API_KEY in .env.",
            )

        models_url = f"{self.api_base}/models"
        headers = self._get_headers()

        start = time.perf_counter()
        owns_client = client is None
        http_client = client or httpx.Client(timeout=self.timeout)

        try:
            resp = http_client.get(models_url, headers=headers)
            latency = (time.perf_counter() - start) * 1000.0

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    raw_models = data.get("data", [])
                    model_ids = []
                    for m in raw_models:
                        if isinstance(m, dict) and "id" in m:
                            model_ids.append(str(m["id"]).strip())
                        elif isinstance(m, str):
                            model_ids.append(m.strip())

                    # Deduplicate while preserving order
                    deduped = list(dict.fromkeys(filter(bool, model_ids)))
                    return AuthTestResult(
                        success=True,
                        status_code=200,
                        category="SUCCESS",
                        message=f"Authentication successful. Discovered {len(deduped)} models.",
                        models=deduped,
                        latency_ms=latency,
                    )
                except Exception as json_err:
                    return AuthTestResult(
                        success=False,
                        status_code=200,
                        category="SERVER_ERROR",
                        message=f"Received HTTP 200 but failed to parse model catalog JSON: {json_err}",
                        latency_ms=latency,
                    )

            elif resp.status_code == 401:
                return AuthTestResult(
                    success=False,
                    status_code=401,
                    category="AUTH_FAILURE",
                    message="Authentication failed (HTTP 401: Invalid API Key). Please verify that AI_API_KEY is active and valid for Agent Router.",
                    latency_ms=latency,
                )
            elif resp.status_code == 403:
                return AuthTestResult(
                    success=False,
                    status_code=403,
                    category="PERMISSION_DENIED",
                    message="Access forbidden (HTTP 403: Permission Denied). The provided key lacks authorization for this endpoint.",
                    latency_ms=latency,
                )
            elif resp.status_code == 429:
                return AuthTestResult(
                    success=False,
                    status_code=429,
                    category="RATE_LIMITED",
                    message="Rate limit or quota exceeded (HTTP 429). Check account balance or concurrency limits.",
                    latency_ms=latency,
                )
            elif 500 <= resp.status_code < 600:
                return AuthTestResult(
                    success=False,
                    status_code=resp.status_code,
                    category="SERVER_ERROR",
                    message=f"Agent Router provider error (HTTP {resp.status_code}). The service may be temporarily unavailable.",
                    latency_ms=latency,
                )
            else:
                return AuthTestResult(
                    success=False,
                    status_code=resp.status_code,
                    category="SERVER_ERROR",
                    message=f"Unexpected response from models endpoint: HTTP {resp.status_code}.",
                    latency_ms=latency,
                )

        except httpx.ConnectTimeout:
            return AuthTestResult(
                success=False,
                status_code=None,
                category="TIMEOUT",
                message=f"Connection timed out after {self.timeout}s while connecting to {self.api_base}.",
                latency_ms=(time.perf_counter() - start) * 1000.0,
            )
        except httpx.ConnectError as ce:
            return AuthTestResult(
                success=False,
                status_code=None,
                category="NETWORK_ERROR",
                message=f"Network or DNS failure connecting to {self.api_base}: {type(ce).__name__}.",
                latency_ms=(time.perf_counter() - start) * 1000.0,
            )
        except Exception as e:
            return AuthTestResult(
                success=False,
                status_code=None,
                category="NETWORK_ERROR",
                message=f"Request failed: {type(e).__name__} ({str(e)}).",
                latency_ms=(time.perf_counter() - start) * 1000.0,
            )
        finally:
            if owns_client:
                http_client.close()

    def filter_candidate_models(
        self,
        model_ids: list[str],
        preferred_model: str | None = None,
        max_candidates: int = 5,
    ) -> list[str]:
        """
        Deduplicate and prioritize lightweight, cost-effective models for Zero.
        Avoids expensive reasoning/frontier models and non-text modalities.
        """
        candidates: list[str] = []

        # If user already configured a model, prioritize checking it first
        if preferred_model and preferred_model in model_ids:
            candidates.append(preferred_model)

        def is_usable_text_model(mid: str) -> bool:
            m_lower = mid.lower()
            return not any(exp in m_lower for exp in _EXPENSIVE_KEYWORDS)

        def is_lightweight(mid: str) -> bool:
            m_lower = mid.lower()
            return any(lw in m_lower for lw in _LIGHTWEIGHT_KEYWORDS)

        # 1. Tier 1: Known lightweight models (mini, flash, haiku, turbo, deepseek-chat)
        tier1 = [m for m in model_ids if is_usable_text_model(m) and is_lightweight(m)]

        # 2. Tier 2: Other general text models
        tier2 = [m for m in model_ids if is_usable_text_model(m) and not is_lightweight(m)]

        for m in tier1 + tier2:
            if m not in candidates:
                candidates.append(m)
            if len(candidates) >= max_candidates:
                break

        # Fallback to first available if none matched filters
        if not candidates and model_ids:
            candidates = model_ids[:max_candidates]

        return candidates

    def test_model_completion(
        self,
        model_id: str,
        client: httpx.Client | None = None,
    ) -> CompletionTestResult:
        """
        Send a minimal prompt request to verify model access:
        'Reply exactly: Zero AI connection successful'
        Uses max_tokens=20 and validates returned content.
        """
        completions_url = (
            self.api_base if self.api_base.endswith("/chat/completions") else f"{self.api_base}/chat/completions"
        )
        headers = self._get_headers()

        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": "Reply exactly: Zero AI connection successful",
                }
            ],
            "max_tokens": 20,
            "temperature": 0.0,
        }

        start = time.perf_counter()
        owns_client = client is None
        http_client = client or httpx.Client(timeout=self.timeout)

        try:
            resp = http_client.post(completions_url, json=payload, headers=headers)
            latency = (time.perf_counter() - start) * 1000.0

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        return CompletionTestResult(
                            model_id=model_id,
                            success=False,
                            status_code=200,
                            category="CONTENT_MISMATCH",
                            error_message="Response returned 200 but 'choices' array was empty.",
                            latency_ms=latency,
                        )

                    message = choices[0].get("message", {})
                    content = message.get("content", "").strip()

                    if not content:
                        return CompletionTestResult(
                            model_id=model_id,
                            success=False,
                            status_code=200,
                            category="CONTENT_MISMATCH",
                            error_message="Assistant response content was empty.",
                            latency_ms=latency,
                        )

                    return CompletionTestResult(
                        model_id=model_id,
                        success=True,
                        status_code=200,
                        category="SUCCESS",
                        response_text=content,
                        latency_ms=latency,
                    )
                except Exception as e:
                    return CompletionTestResult(
                        model_id=model_id,
                        success=False,
                        status_code=200,
                        category="SERVER_ERROR",
                        error_message=f"Failed to parse completion JSON: {e}",
                        latency_ms=latency,
                    )

            elif resp.status_code == 401:
                return CompletionTestResult(
                    model_id=model_id,
                    success=False,
                    status_code=401,
                    category="AUTH_FAILURE",
                    error_message="Authentication failed (HTTP 401).",
                    latency_ms=latency,
                )
            elif resp.status_code == 404:
                return CompletionTestResult(
                    model_id=model_id,
                    success=False,
                    status_code=404,
                    category="MODEL_NOT_FOUND",
                    error_message=f"Model '{model_id}' was not found or is unavailable on this route.",
                    latency_ms=latency,
                )
            elif resp.status_code == 429:
                return CompletionTestResult(
                    model_id=model_id,
                    success=False,
                    status_code=429,
                    category="RATE_LIMITED",
                    error_message="Rate limit or quota exceeded (HTTP 429).",
                    latency_ms=latency,
                )
            elif 500 <= resp.status_code < 600:
                return CompletionTestResult(
                    model_id=model_id,
                    success=False,
                    status_code=resp.status_code,
                    category="SERVER_ERROR",
                    error_message=f"Server error from provider (HTTP {resp.status_code}).",
                    latency_ms=latency,
                )
            else:
                return CompletionTestResult(
                    model_id=model_id,
                    success=False,
                    status_code=resp.status_code,
                    category="SERVER_ERROR",
                    error_message=f"Unexpected status: HTTP {resp.status_code}.",
                    latency_ms=latency,
                )

        except httpx.ConnectTimeout:
            return CompletionTestResult(
                model_id=model_id,
                success=False,
                status_code=None,
                category="TIMEOUT",
                error_message=f"Completion request timed out after {self.timeout}s.",
                latency_ms=(time.perf_counter() - start) * 1000.0,
            )
        except Exception as e:
            return CompletionTestResult(
                model_id=model_id,
                success=False,
                status_code=None,
                category="NETWORK_ERROR",
                error_message=f"Completion error: {type(e).__name__} ({str(e)})",
                latency_ms=(time.perf_counter() - start) * 1000.0,
            )
        finally:
            if owns_client:
                http_client.close()

    def safe_update_env(self, updates: dict[str, str]) -> bool:
        """
        Safely update .env file preserving comments, existing secrets, and formatting.
        Never overwrites keys not in `updates`.
        """
        if not self.env_path.exists():
            logger.warning(".env path %s does not exist. Cannot update.", self.env_path)
            return False

        try:
            lines = self.env_path.read_text(encoding="utf-8").splitlines(keepends=True)
            updated_keys = set()
            new_lines = []

            for line in lines:
                matched = False
                for key, val in updates.items():
                    pattern = rf"^{re.escape(key)}\s*=.*$"
                    if re.match(pattern, line):
                        new_lines.append(f"{key}={val}\n")
                        updated_keys.add(key)
                        matched = True
                        break
                if not matched:
                    new_lines.append(line)

            # Append any keys that weren't present
            for key, val in updates.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={val}\n")

            self.env_path.write_text("".join(new_lines), encoding="utf-8")
            logger.info("Successfully updated .env with keys: %s", list(updates.keys()))
            return True
        except Exception as e:
            logger.error("Failed to safely update .env: %s", e)
            return False

    def run_full_diagnostic(
        self,
        preferred_model: str | None = None,
        target_verified_count: int = 2,
        max_models_to_test: int = 5,
        update_env_on_success: bool = True,
    ) -> DiagnosticReport:
        """
        Perform complete diagnostic sequence:
        1. Test authentication via GET /models.
        2. If auth fails, abort early and generate actionable report without testing completions.
        3. Extract and prioritize candidate models.
        4. Test candidate completions until target verified count is reached.
        5. Select optimal model and safely update .env if verified.
        """
        redacted_key = self.mask_key(self.api_key)
        auth_res = self.test_authentication()

        if not auth_res.success:
            suggested_fix = (
                "Please check the AI_API_KEY in your .env file. Ensure your Agent Router "
                "API key is active, properly copied without surrounding quotes or whitespace, "
                "and has valid routing credits."
                if auth_res.category == "AUTH_FAILURE"
                else "Check network connectivity and API base URL in .env."
            )
            return DiagnosticReport(
                provider="Agent Router",
                api_base=self.api_base,
                api_key_redacted=redacted_key,
                auth_result=auth_res,
                models_discovered=0,
                tested_candidates=[],
                verified_models=[],
                selected_model=None,
                selection_reason="Authentication failed. No models could be tested.",
                config_updated=False,
                error_report=auth_res.message,
                suggested_fix=suggested_fix,
            )

        # Authentication Succeeded!
        catalog = auth_res.models
        candidates = self.filter_candidate_models(
            model_ids=catalog,
            preferred_model=preferred_model,
            max_candidates=max_models_to_test,
        )

        tested_results: list[CompletionTestResult] = []
        verified_models: list[str] = []

        logger.info("Testing candidate models: %s", candidates)

        for mid in candidates:
            res = self.test_model_completion(mid)
            tested_results.append(res)
            if res.success:
                verified_models.append(mid)
                logger.info("Model '%s' verified successfully (latency: %.1fms)!", mid, res.latency_ms)
                # Stop if we reached target verified count
                if len(verified_models) >= target_verified_count:
                    break
            else:
                logger.warning("Model '%s' failed completion: %s", mid, res.error_message)
                # Stop immediately if authentication or payment failure occurs during completions
                if res.category in ("AUTH_FAILURE", "RATE_LIMITED"):
                    break

        if not verified_models:
            return DiagnosticReport(
                provider="Agent Router",
                api_base=self.api_base,
                api_key_redacted=redacted_key,
                auth_result=auth_res,
                models_discovered=len(catalog),
                tested_candidates=tested_results,
                verified_models=[],
                selected_model=None,
                selection_reason="None of the tested candidate models returned a successful completion.",
                config_updated=False,
                error_report="Tested models failed chat completions.",
                suggested_fix="Verify route permissions or account credits on Agent Router.",
            )

        # Select best model: prefer preferred_model if verified, else fastest verified
        if preferred_model and preferred_model in verified_models:
            selected_model = preferred_model
            reason = f"Preserved previously configured model '{selected_model}' after successful verification."
        else:
            # Pick verified model with lowest latency
            best = min(
                [c for c in tested_results if c.success],
                key=lambda x: x.latency_ms,
            )
            selected_model = best.model_id
            reason = (
                f"Selected lightweight verified model '{selected_model}' "
                f"(fastest verified response: {best.latency_ms:.1f}ms)."
            )

        config_updated = False
        if update_env_on_success:
            updates = {
                "AI_PROVIDER": "openai",
                "AI_API_BASE": self.api_base,
                "AI_MODEL": selected_model,
            }
            config_updated = self.safe_update_env(updates)

        return DiagnosticReport(
            provider="Agent Router",
            api_base=self.api_base,
            api_key_redacted=redacted_key,
            auth_result=auth_res,
            models_discovered=len(catalog),
            tested_candidates=tested_results,
            verified_models=verified_models,
            selected_model=selected_model,
            selection_reason=reason,
            config_updated=config_updated,
        )
