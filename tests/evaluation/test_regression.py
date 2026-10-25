"""
Tests for Core Regressions and Multi-Turn Continuity.
Phase 8, 10 & 11 Evaluation: Regression Verification.
"""

from unittest.mock import MagicMock, patch
import pytest
from app.core.assistant import ZeroAssistant
from app.voice.speech_synthesis import SpeechSynthesizer


def test_reg_001_consecutive_responses_trigger_tts():
    """Verify consecutive turns trigger speech synthesis cleanly."""
    synth = SpeechSynthesizer()
    synth._local_engine = MagicMock()

    # 5 turns
    for i in range(5):
        synth.speak(f"Assistant turn response {i}", wait=False)

    assert synth._queue.qsize() == 5
    synth.stop()


def test_reg_002_speech_text_strips_markdown_code_blocks():
    """Verify speech cleaner removes code block syntax from spoken output."""
    raw = "Here is the implementation:\n```python\nprint('hello world')\n```\nIt works reliably."
    cleaned = SpeechSynthesizer.clean_text_for_speech(raw)
    assert "```" not in cleaned
    assert "print('hello world')" not in cleaned
    assert "code implementation" in cleaned.lower() or "screen" in cleaned.lower()


def test_reg_003_pdf_export_artifact_verification(tmp_path):
    """Verify PDF export produces valid %PDF magic bytes and nonempty file."""
    from app.exports.pdf_generator import PDFGenerator
    html = PDFGenerator.create_html_report(
        title="Evaluation Audit Report",
        body_markdown="## Executive Assessment\nSystem telemetry and safety evaluation completed successfully.",
        subtitle="Zero AI Test Harness",
    )
    pdf_path = PDFGenerator.generate_pdf(html, filename="test_eval_artifact.pdf")
    try:
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
        header = pdf_path.read_bytes()[:5]
        assert header == b"%PDF-"
    finally:
        if pdf_path.exists():
            pdf_path.unlink()
