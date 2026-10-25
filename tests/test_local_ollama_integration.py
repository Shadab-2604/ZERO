"""
Automated tests for Zero AI Local Ollama Integration.

Covers:
1. Ollama connection availability & health check.
2. Installed-model detection and tag parsing.
3. General vs coding model routing (Llama vs Qwen Coder).
4. Deterministic local calculation engine (arithmetic & percentages).
5. Missing-model detection and actionable user guidance.
6. Failed inference, connection errors, and timeout resilience.
7. Strict local-only network boundary enforcement (EXTERNAL_AI_ENABLED=false).
8. Knowledge retrieval grounding, citations, and truthful unverified fallback.
9. Secret redaction and public configuration security.
10. End-to-end assistant integration via ZeroAssistant.
"""

from unittest.mock import MagicMock, patch, PropertyMock
import httpx
import pytest

from app.ai.local_service import LocalAIService, RouteTarget
from app.ai.provider_factory import AIProviderFactory
from app.ai.providers.cloud_provider import CloudAIProvider
from app.config.settings import Settings, get_settings
from app.core.assistant import ZeroAssistant
from app.core.calculator import LocalCalculator, CalculationResult
from app.core.state_manager import AssistantState
from app.knowledge.store import SearchResult
from app.memory.database import init_db


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


# ==============================================================================
# 1. Connection Availability & Health Check
# ==============================================================================

def test_ollama_connection_availability_mocked():
    """Verify is_available property correctly handles HTTP 200 vs unreachable."""
    service = LocalAIService(api_base="http://127.0.0.1:11434/v1")

    # Mock success (status 200)
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        assert service.is_available is True

    # Mock failure (connection refused)
    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Connection refused")):
        assert service.is_available is False


def test_ollama_live_connection():
    """Verify live connection to running local Ollama daemon."""
    service = LocalAIService(api_base="http://127.0.0.1:11434/v1")
    assert service.is_available is True, (
        "Local Ollama daemon must be running at http://127.0.0.1:11434"
    )


# ==============================================================================
# 2. Installed Model Detection
# ==============================================================================

def test_installed_model_detection_parsing():
    """Verify list_installed_models extracts full and short model names."""
    service = LocalAIService(api_base="http://127.0.0.1:11434/v1")

    mock_response_data = {
        "models": [
            {"name": "llama3.2:latest", "size": 2000000000},
            {"name": "qwen2.5-coder:3b", "size": 1900000000},
            {"name": "qwen2.5-coder:7b", "size": 4700000000},
        ]
    }

    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response_data)
        models = service.list_installed_models()
        assert "llama3.2:latest" in models
        assert "llama3.2" in models
        assert "qwen2.5-coder:3b" in models
        assert "qwen2.5-coder:7b" in models


def test_live_installed_models_detected():
    """Verify local models exist in the running Ollama instance."""
    service = LocalAIService(api_base="http://127.0.0.1:11434/v1")
    installed = service.list_installed_models()
    assert any("llama3.2" in m for m in installed), "llama3.2 must be installed"
    assert any("qwen2.5-coder" in m for m in installed), "qwen2.5-coder must be installed"


# ==============================================================================
# 3. Model Routing (General vs Coding)
# ==============================================================================

def test_model_routing_general_queries():
    """Verify conversational and general queries route to Llama."""
    service = LocalAIService()

    general_queries = [
        "Good morning Zero, what can you do?",
        "Explain the theory of relativity in simple terms.",
        "Who was Alan Turing?",
        "Write a polite email declining a meeting.",
        "What is the capital of Japan?",
    ]

    for q in general_queries:
        route, target = service.classify_route(q)
        assert route == RouteTarget.CHAT, f"Query '{q}' should route to CHAT"
        assert target == service._chat_model


def test_model_routing_coding_queries():
    """Verify programming, debugging, and code queries route to Qwen Coder."""
    service = LocalAIService()

    coding_queries = [
        "Write a Python function to compute SHA-256 hash of a file.",
        "How do I fix IndexError: list index out of range in Python?",
        "Implement a binary search algorithm in TypeScript.",
        "Write a SQL query with INNER JOIN to aggregate user orders.",
        "Here is my code:\n```python\ndef test(): pass\n```\nHow do I add a docstring?",
        "Debug this regular expression pattern for emails.",
        "Write pytest unit test cases for my function.",
    ]

    for q in coding_queries:
        route, target = service.classify_route(q)
        assert route == RouteTarget.CODE, f"Query '{q}' should route to CODE"
        assert target == service._code_model


# ==============================================================================
# 4. Deterministic Calculation Engine
# ==============================================================================

def test_calculation_engine_arithmetic():
    """Verify exact arithmetic without LLM hallucination."""
    expressions = [
        ("What is 15 * 8?", 120),
        ("Calculate 100 / 4 + 7", 32),
        ("2 ** 8", 256),
        ("(45 + 55) * 3", 300),
    ]

    for text, expected in expressions:
        res = LocalCalculator.try_calculate(text)
        assert res.is_calculation is True, f"Failed to detect calculation in: {text}"
        assert res.result == expected
        assert str(expected) in res.explanation


def test_calculation_engine_percentages():
    """Verify exact percentage calculations."""
    percentage_tests = [
        ("What is 18% of 450?", 81.0),
        ("Calculate 25% of 80", 20.0),
        ("increase 200 by 15%", 230.0),
        ("decrease 100 by 20%", 80.0),
    ]

    for text, expected in percentage_tests:
        res = LocalCalculator.try_calculate(text)
        assert res.is_calculation is True, f"Failed to detect percentage in: {text}"
        assert abs(res.result - expected) < 1e-4
        assert res.formatted_result in res.explanation


def test_calculation_routing_priority():
    """Verify calculation engine intercepts before sending to LLM."""
    service = LocalAIService()
    route, metadata = service.classify_route("What is 125 * 4?")
    assert route == RouteTarget.CALCULATION
    assert isinstance(metadata, CalculationResult)
    assert metadata.result == 500

    # Ensure generate_response returns deterministic calculation
    response = service.generate_response([{"role": "user", "content": "What is 125 * 4?"}])
    assert "500" in response
    assert "Result:" in response


# ==============================================================================
# 5. Missing-Model & Offline Handling
# ==============================================================================

def test_missing_model_produces_actionable_error():
    """Verify informative error if configured model is not installed."""
    service = LocalAIService(
        api_base="http://127.0.0.1:11434/v1",
        chat_model="nonexistent-model-xyz",
    )

    with patch.object(LocalAIService, "is_available", new_callable=PropertyMock, return_value=True), \
         patch.object(service, "list_installed_models", return_value=["llama3.2", "qwen2.5-coder:3b"]):
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_response([{"role": "user", "content": "Hello"}])
        err_msg = str(exc_info.value)
        assert "not installed in Ollama" in err_msg
        assert "ollama pull nonexistent-model-xyz" in err_msg


def test_offline_ollama_produces_actionable_error():
    """Verify readable error when Ollama daemon is offline."""
    service = LocalAIService(api_base="http://127.0.0.1:11434/v1")

    with patch.object(LocalAIService, "is_available", new_callable=PropertyMock, return_value=False), \
         patch.object(service, "list_installed_models", return_value=[]):
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_response([{"role": "user", "content": "Hello"}])
        assert "Local Ollama service is not reachable" in str(exc_info.value)


def test_inference_timeout_handling():
    """Verify timeout produces a helpful user-facing error."""
    service = LocalAIService(timeout=0.01)

    with patch.object(LocalAIService, "is_available", new_callable=PropertyMock, return_value=True), \
         patch.object(service, "list_installed_models", return_value=["llama3.2"]), \
         patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timeout")):
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_response([{"role": "user", "content": "Hello"}])
        assert "timed out" in str(exc_info.value).lower()


# ==============================================================================
# 6. Local-Only Network Boundary Enforcement
# ==============================================================================

def test_local_only_enforcement_blocks_external_host():
    """Verify requests to external endpoints are strictly blocked when EXTERNAL_AI_ENABLED=false."""
    with patch("app.ai.local_service.get_settings") as mock_settings:
        mock_settings.return_value = Settings(
            EXTERNAL_AI_ENABLED=False,
            AI_API_BASE="https://api.openai.com/v1",
        )
        service = LocalAIService(api_base="https://api.openai.com/v1")
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_response([{"role": "user", "content": "Hello"}])
        assert "External AI is disabled" in str(exc_info.value)
        assert "Cannot connect to remote host" in str(exc_info.value)


def test_cloud_provider_blocks_external_when_disabled():
    """Verify CloudAIProvider respects EXTERNAL_AI_ENABLED=false."""
    with patch("app.ai.providers.cloud_provider.get_settings") as mock_settings:
        mock_settings.return_value = Settings(
            EXTERNAL_AI_ENABLED=False,
            AI_API_BASE="https://agent-router.net/aggregate/openai/v1",
            AI_API_KEY="dummy-key",
        )
        provider = CloudAIProvider(
            provider_name="openai",
            api_base="https://agent-router.net/aggregate/openai/v1",
            api_key="dummy-key",
            model_name="gpt-4o",
        )
        with pytest.raises(RuntimeError) as exc_info:
            provider.generate_response([{"role": "user", "content": "Hello"}])
        assert "External AI is disabled" in str(exc_info.value)


def test_provider_factory_routes_to_local_service():
    """Verify AIProviderFactory instantiates LocalAIService when configured for ollama or local_only."""
    with patch("app.ai.provider_factory.get_settings") as mock_settings:
        mock_settings.return_value = Settings(
            AI_PROVIDER="ollama",
            ZERO_MODE="local_only",
            EXTERNAL_AI_ENABLED=False,
            LOCAL_CHAT_MODEL="llama3.2",
            LOCAL_CODE_MODEL="qwen2.5-coder:3b",
        )
        provider = AIProviderFactory.get_provider()
        assert isinstance(provider, LocalAIService)


# ==============================================================================
# 7. Knowledge Grounding & Truthful Citations
# ==============================================================================

def test_knowledge_unverified_fallback():
    """When a document question has no matches in Knowledge, assistant returns unverified notice."""
    assistant = ZeroAssistant()
    assistant.initialize()
    assistant.wake()

    mock_kb = MagicMock()
    mock_kb.format_rag_context.return_value = ("", [])

    with patch("app.core.conversation_manager.get_knowledge_service", return_value=mock_kb):
        res = assistant.process_input("According to my files, what is the secret recipe for XYZ pudding?")
        reply = res["reply_text"]
        assert "could not be verified" in reply or "Knowledge base" in reply


def test_knowledge_citation_grounding():
    """When documents are retrieved, citations are grounded with filenames."""
    assistant = ZeroAssistant()
    assistant.initialize()
    assistant.wake()

    mock_result = SearchResult(
        source_file="project_notes.md",
        section_label="Architecture",
        content="Project Zero uses a local SQLite FTS5 database for fast indexed retrieval.",
        score=0.95,
        chunk_index=0,
        metadata={},
    )

    mock_kb = MagicMock()
    mock_kb.format_rag_context.return_value = (
        "--- Reference Document [1] ---\nSource: project_notes.md (Architecture)\nContent: Project Zero uses SQLite FTS5.",
        [mock_result],
    )

    mock_provider = MagicMock()
    mock_provider.generate_response.return_value = (
        "Based on your documents, Zero uses SQLite FTS5 for indexing."
    )

    with patch("app.core.conversation_manager.get_knowledge_service", return_value=mock_kb), \
         patch.object(assistant.conversation_manager, "get_provider", return_value=mock_provider):
        res = assistant.process_input("What database does Zero use according to my notes?")
        reply = res["reply_text"]
        # Assistant includes source citation
        assert "project_notes.md" in reply


# ==============================================================================
# 8. Secret Redaction & Safety
# ==============================================================================

def test_secret_redaction_in_settings():
    """Verify API keys and sensitive tokens are completely masked in public dict."""
    settings = Settings(
        AI_API_KEY="aak_secret_test_key_1234567890",
        AI_PROVIDER="ollama",
    )
    public_dict = settings.get_public_dict()
    assert "aak_secret_test_key_1234567890" not in str(public_dict)
    assert public_dict["ai_api_key_status"] == "configured (••••••••)"
    assert public_dict["zero_mode"] == "local_only"
    assert public_dict["external_ai_enabled"] is False


# ==============================================================================
# 9. Real Live Smoke Inference Test (Ollama)
# ==============================================================================

def test_live_chat_inference_llama():
    """Smoke test: execute live inference on local Llama 3.2."""
    service = LocalAIService(timeout=30.0)
    if not service.is_available:
        pytest.skip("Local Ollama daemon not reachable.")

    installed = service.list_installed_models()
    if not any("llama3.2" in m for m in installed):
        pytest.skip("llama3.2 not installed locally.")

    response = service.generate_response(
        messages=[{"role": "user", "content": "Respond with the single word: CONFIRMED."}],
    )
    assert len(response.strip()) > 0
    assert "CONFIRMED" in response.upper()


def test_live_code_inference_qwen_coder():
    """Smoke test: execute live coding inference on local Qwen Coder."""
    service = LocalAIService(timeout=30.0)
    if not service.is_available:
        pytest.skip("Local Ollama daemon not reachable.")

    installed = service.list_installed_models()
    if not any("qwen2.5-coder" in m for m in installed):
        pytest.skip("qwen2.5-coder not installed locally.")

    prompt = "Write a python function to add two numbers: def add(a: int, b: int) -> int:"
    response = service.generate_response(
        messages=[{"role": "user", "content": prompt}],
    )
    assert "def add" in response or "return a + b" in response or "int" in response
