"""
Tests for General Question Answering, Persona Adherence, and Context Retention.
Phase 3 Evaluation: General Conversation.
"""

import re
import pytest
from unittest.mock import MagicMock, patch
from app.core.assistant import ZeroAssistant
from app.ai.local_service import LocalAIService, RouteTarget


def test_gen_qa_001_persona_introduction():
    """GEN-001: Introduce yourself as Zero in exactly two sentences."""
    assistant = ZeroAssistant()
    assistant.initialize()
    assistant.wake()

    mock_resp = "I am Zero, your elite personal desktop AI assistant. I am engineered to assist with workflows, system tasks, and intelligent automation."
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        result = assistant.process_input("Introduce yourself as Zero in exactly two sentences.")
        reply = result["reply_text"].split("\n\n**Sources:**")[0].strip()
        assert "Zero" in reply
        # Sentence count check
        sentences = [s.strip() for s in reply.split(".") if s.strip()]
        assert len(sentences) == 2


def test_gen_qa_002_ram_vs_vram_beginner():
    """GEN-002: Explain the difference between RAM and VRAM to a beginner."""
    mock_resp = (
        "Think of RAM as your computer's general workspace for everyday programs like browsers and documents, "
        "managed by the CPU. In contrast, VRAM is specialized high-speed memory dedicated exclusively to your graphics card (GPU) "
        "to handle heavy visuals, 3D rendering, and video display."
    )
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        assistant = ZeroAssistant()
        assistant.initialize()
        assistant.wake()
        res = assistant.process_input("Explain the difference between RAM and VRAM to a beginner.")
        assert "RAM" in res["reply_text"]
        assert "VRAM" in res["reply_text"]
        assert "GPU" in res["reply_text"] or "graphics" in res["reply_text"].lower()


def test_gen_qa_003_ram_vs_vram_developer_four_sentences():
    """GEN-003: Explain difference to experienced Python developer in <= 4 sentences."""
    mock_resp = (
        "System RAM holds CPU-bound application state and Python object heaps across the virtual memory space. "
        "VRAM is high-bandwidth memory (GDDR/HBM) directly attached to the GPU bus, critical for tensor allocations in PyTorch or CUDA kernels. "
        "Moving data between RAM and VRAM incurs PCIe transfer latency via operations like `.cuda()` or `.to(device)`. "
        "Optimizing neural network inference requires minimizing host-to-device memory copies."
    )
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        assistant = ZeroAssistant()
        assistant.initialize()
        assistant.wake()
        res = assistant.process_input("Explain the difference between RAM and VRAM to an experienced Python developer in no more than four sentences.")
        reply_body = res["reply_text"].split("\n\n**Sources:**")[0].strip()
        # Count sentences by ending periods followed by whitespace or end of string
        sentences = [s.strip() for s in re.split(r"[.!?](?:\s+|$)", reply_body) if s.strip()]
        assert len(sentences) <= 4
        assert any(t in res["reply_text"].lower() for t in ("cuda", "tensor", "pcie", "gpu", "host"))


def test_gen_qa_004_context_retention_port_number():
    """GEN-006 & GEN-007: Remember Orion uses port 43821 across turns without fabricating details."""
    assistant = ZeroAssistant()
    assistant.initialize()
    assistant.wake()

    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.side_effect = [
            "Understood. I have recorded that project Orion uses port 43821.",
            "Port 43821 was specified by you as the designated port for the Orion project. You have not provided any further technical protocol, service type, or configuration details regarding its specific function.",
        ]
        mock_get.return_value = mock_provider

        # Turn 1: Provide fact
        res1 = assistant.process_input("Remember this within the current conversation: the fictional project Orion uses port 43821. What port did I mention?")
        assert "43821" in res1["reply_text"]

        # Turn 2: Ask for meaning without inventing details
        res2 = assistant.process_input("Now explain what that port number means in the Orion project, without inventing details not supplied by me.")
        assert "43821" in res2["reply_text"]
        # Must acknowledge that further details were not supplied
        assert any(phrase in res2["reply_text"].lower() for phrase in ("not provided", "not supplied", "only specified", "no further details"))
