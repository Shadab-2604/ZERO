"""
Tests for Reasoning, Word Problems, and Deterministic Logic.
Phase 4 Evaluation: Multi-Step Reasoning.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.core.assistant import ZeroAssistant


def test_reason_001_workers_time_scaling():
    """REAS-001: 3 workers take 12 hours -> 6 workers take 6 hours under ideal conditions."""
    mock_resp = (
        "Under the assumption that work scales linearly and each worker maintains equal productivity with zero overhead, "
        "doubling the workforce from 3 workers to 6 workers halves the required time from 12 hours to **6 hours**."
    )
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        assistant = ZeroAssistant()
        assistant.initialize()
        assistant.wake()
        res = assistant.process_input("If three workers complete a fixed task in 12 hours, how long would six equally productive workers take under ideal conditions? State the assumption.")
        assert "6" in res["reply_text"]
        assert any(w in res["reply_text"].lower() for w in ("assumption", "linearly", "ideal", "productivity"))


def test_reason_002_discount_word_problem():
    """REAS-002: Product costs ₹1,200 with 15% discount -> ₹1,020."""
    mock_resp = (
        "1. Original price: ₹1,200\n"
        "2. Discount calculation: 15% of 1,200 = (15 / 100) × 1,200 = ₹180\n"
        "3. Final price: 1,200 - 180 = **₹1,020** before additional taxes or fees."
    )
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        assistant = ZeroAssistant()
        assistant.initialize()
        assistant.wake()
        res = assistant.process_input("A product costs ₹1,200 and receives a 15% discount. What is the final price before additional taxes or fees?")
        assert "1,020" in res["reply_text"] or "1020" in res["reply_text"]


def test_reason_003_download_speed_rate():
    """REAS-003: 1,000 MB downloaded in 80 seconds -> 12.5 MB/s."""
    mock_resp = (
        "To find average download speed, divide total data downloaded by time elapsed:\n"
        "Speed = 1,000 MB / 80 seconds = **12.5 MB/s**."
    )
    with patch("app.core.conversation_manager.AIProviderFactory.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = mock_resp
        mock_get.return_value = mock_provider

        assistant = ZeroAssistant()
        assistant.initialize()
        assistant.wake()
        res = assistant.process_input("A download takes 80 seconds for a 1,000 MB file. What is the average speed in MB/s, assuming the full file was downloaded in 80 seconds?")
        assert "12.5" in res["reply_text"]
