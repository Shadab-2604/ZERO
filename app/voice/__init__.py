"""
Zero AI — Real-Time Voice, Streaming Recognition, and Speech Synthesis.

Responsibilities:
- Real-time PCM audio streaming with dynamic RMS Energy Voice Activity Detection (StreamingVoiceRecognizer).
- Pause continuation window (1.8s silence threshold, up to 5s continuation).
- Barge-in audio interruption during speech playback.
- Windows SAPI5 COM speech synthesis worker with markdown/code cleaning (SpeechSynthesizer).
- Voice coordination facade (VoiceManager).
- Continuous wake-word listener (WakeWordListener).
"""

from app.voice.manager import VoiceManager
from app.voice.stream_listener import StreamingVoiceRecognizer, calculate_rms
from app.voice.speech_synthesis import SpeechSynthesizer
from app.voice.speech_recognition import SpeechRecognizer
from app.voice.wake_listener import WakeWordListener

# Backwards compatibility alias
VoiceRecognizer = SpeechRecognizer

__all__ = [
    "VoiceManager",
    "StreamingVoiceRecognizer",
    "calculate_rms",
    "SpeechSynthesizer",
    "SpeechRecognizer",
    "VoiceRecognizer",
    "WakeWordListener",
]
