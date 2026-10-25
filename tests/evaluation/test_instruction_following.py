"""
Tests for Instruction Following, Negative Constraints, and Structured Output.
Phase 3 Evaluation: Instruction Compliance.
"""

import json
import re
import pytest
from unittest.mock import MagicMock, patch
from app.core.assistant import ZeroAssistant


def test_inst_001_exact_bullet_summary():
    """INST-001: Summarize text into exactly three bullet points."""
    text_to_summarize = (
        "Operating systems use virtual memory to provide applications with dedicated memory addresses. "
        "Page tables map virtual pages to physical DRAM frames. "
        "When physical memory fills up, page replacement algorithms swap inactive pages to disk storage."
    )
    mock_resp = (
        "• Virtual memory isolates application memory spaces using dedicated address tables.\n"
        "• Page tables perform real-time translation between virtual pages and physical DRAM frames.\n"
        "• Inactive pages are swapped to disk storage when physical RAM capacity is reached."
    )
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        assistant = ZeroAssistant()
        assistant.initialize()
        assistant.wake()
        res = assistant.process_input(f"Summarize the following text into exactly three bullet points:\n{text_to_summarize}")
        reply = res["reply_text"].split("\n\n**Sources:**")[0].strip()
        bullets = [b for b in reply.split("\n") if b.strip().startswith(("•", "-", "*"))]
        assert len(bullets) == 3


def test_inst_002_json_only_output():
    """INST-002: Return valid JSON only with keys: name, status, verified."""
    mock_resp = '{"name": "Zero System", "status": "active", "verified": true}'
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        assistant = ZeroAssistant()
        assistant.initialize()
        assistant.wake()
        res = assistant.process_input("Return valid JSON only, with the fields name, status, and verified.")
        reply = res["reply_text"].split("\n\n**Sources:**")[0].strip()
        data = json.loads(reply)
        assert "name" in data
        assert "status" in data
        assert "verified" in data
        assert isinstance(data["verified"], bool)


def test_inst_003_negative_constraint_no_numbers():
    """INST-003: Explain calculation without using any numeric digits."""
    mock_resp = (
        "To find the final discounted price, take the base price of the item and determine the specified percentage. "
        "Multiply the total amount by the reduction rate, and then subtract that resulting value from the initial cost."
    )
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        assistant = ZeroAssistant()
        assistant.initialize()
        assistant.wake()
        res = assistant.process_input("Explain how to perform this calculation, but do not show any numbers.")
        reply_body = res["reply_text"].split("\n\n**Sources:**")[0].strip()
        # Ensure no digits 0-9 appear in model reply
        digits = re.findall(r"\d", reply_body)
        assert len(digits) == 0


def test_inst_004_impossible_request_missing_document():
    """INST-004: What does the document say? I have not provided a document."""
    mock_resp = "I cannot tell you what the document says because you have not provided or referenced any document."
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        assistant = ZeroAssistant()
        assistant.initialize()
        assistant.wake()
        res = assistant.process_input("What does the document say? I have not provided a document.")
        assert any(w in res["reply_text"].lower() for w in ("not provided", "no document", "cannot", "specify"))
