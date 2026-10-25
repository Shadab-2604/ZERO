"""
Zero AI Unified Execution Entrypoint.
Supports:
  python run.py             (Default: PySide6 Desktop GUI + Background API)
  python run.py --voice     (Hands-free continuous voice assistant in terminal)
  python run.py --cli       (Interactive typed terminal session)
  python run.py --api-only  (Headless FastAPI server only)
"""

import sys
import argparse
import time
import queue
import threading
from app.bootstrap import bootstrap_application
from app.core.assistant import get_assistant
from app.core.state_manager import AssistantState
from app.api.server import get_api_server_manager


def run_gui():
    from app.main import main
    sys.exit(main())


def run_api_only():
    print("[ZERO AI] Starting in API-only mode...")
    bootstrap_application(start_api_server=True)
    print("[ZERO AI] API Server running on http://127.0.0.1:8765. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[ZERO AI] Stopping API server...")
        get_api_server_manager().stop()


def run_voice_continuous():
    """
    Hands-free continuous voice assistant lifecycle:
    LISTENING -> HEARING YOU -> PROCESSING -> SPEAKING -> LISTENING
    With Live Caption HUD Window, barge-in audio interruption, and real-time streaming recognition.
    No Enter key required between turns. Automatically speaks every answer.
    """
    from PySide6.QtWidgets import QApplication
    from app.config.settings import get_settings
    from app.voice.manager import VoiceManager
    from app.gui.widgets.caption_window import LiveCaptionWindow

    settings = get_settings()
    settings.voice_enabled = True

    print("[ZERO AI] Starting in Hands-Free Continuous Voice Assistant mode...")
    bootstrap_application(start_api_server=True)
    assistant = get_assistant()
    voice_manager = VoiceManager()
    assistant.set_speech_stop_callback(voice_manager.stop_speaking)

    # Pause wake listener to avoid microphone device contention with streaming listener
    voice_manager.pause_wake_listener()

    # Initialize PySide6 Application for Live Caption HUD
    qt_app = QApplication.instance() or QApplication(sys.argv)

    processing_queue: queue.Queue[str] = queue.Queue()
    stop_event = threading.Event()

    def handle_user_submit(text: str):
        if text and text.strip():
            processing_queue.put(text.strip())

    caption_window = LiveCaptionWindow(
        on_user_submit=handle_user_submit,
        on_stop_speaking=voice_manager.stop_speaking,
        on_toggle_mute=voice_manager.toggle_mute,
    )
    caption_window.show()

    # Connect VoiceManager streaming listener
    def on_state_changed(state, reason):
        assistant.state_manager.transition_to(state, reason=reason)
        caption_window.state_updated.emit(state.value, reason)

    def on_partial_transcript(partial_text):
        caption_window.partial_caption_updated.emit(partial_text)

    def on_final_transcript(final_text):
        caption_window.final_transcript_ready.emit(final_text)
        processing_queue.put(final_text)

    def on_audio_error(error_msg):
        caption_window.error_occurred.emit(error_msg)

    streaming_listener = voice_manager.create_streaming_listener(
        on_state_changed=on_state_changed,
        on_partial_transcript=on_partial_transcript,
        on_final_transcript=on_final_transcript,
        on_error=on_audio_error,
        silence_threshold_seconds=1.8,
        continuation_window_seconds=5.0,
    )

    # Background non-blocking stdin reader for optional typed input
    def _stdin_worker():
        while not stop_event.is_set():
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                typed = line.strip()
                if typed:
                    print(f"You (Typed) > {typed}")
                    caption_window.final_transcript_ready.emit(typed)
                    processing_queue.put(typed)
            except Exception:
                break

    stdin_thread = threading.Thread(target=_stdin_worker, name="ZeroStdinReader", daemon=True)
    stdin_thread.start()

    # Background voice coordinator loop
    def _voice_coordinator():
        # Deliver wake greeting aloud
        greeting = assistant.wake()
        print(f"\nZero > {greeting}\n")
        caption_window.assistant_reply_ready.emit(greeting, greeting)
        caption_window.state_updated.emit(AssistantState.SPEAKING.value, "Greeting user")
        voice_manager.speak(greeting, wait=True)
        caption_window.state_updated.emit(AssistantState.LISTENING.value, "Listening for speech")

        # Start streaming microphone listener
        streaming_listener.start()

        print("\n" + "=" * 65)
        print("  🎤 ZERO CONTINUOUS VOICE & LIVE CAPTIONS ACTIVE (Hands-Free)")
        print("  Speak naturally into your microphone.")
        print("  Barge-in: Speak anytime while Zero is talking to interrupt immediately.")
        print("  Commands: 'Zero, sleep' | 'Zero, stop speaking' | 'Zero, quit'")
        print("  (You may also type a question or 'q' anytime and press Enter)")
        print("=" * 65 + "\n")

        while not stop_event.is_set():
            try:
                user_input = processing_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if not user_input or not user_input.strip():
                continue

            clean_input = user_input.strip()
            print(f"\nYou > {clean_input}")

            # Check for direct quit commands
            if clean_input.lower() in ("exit", "quit", "q", "zero quit"):
                farewell = assistant.sleep()
                print(f"\nZero > {farewell}\n")
                caption_window.assistant_reply_ready.emit(farewell, farewell)
                caption_window.state_updated.emit(AssistantState.SPEAKING.value, "Farewell")
                voice_manager.speak(farewell, wait=True)
                assistant.shutdown()
                stop_event.set()
                caption_window.close()
                break

            # Check for direct stop speaking command
            if clean_input.lower() in ("zero stop speaking", "stop speaking", "be quiet", "silence"):
                voice_manager.stop_speaking()
                caption_window.state_updated.emit(AssistantState.LISTENING.value, "Speech halted")
                continue

            # Process input through assistant (Local AI / Tools / Diagnostics)
            caption_window.state_updated.emit(AssistantState.PROCESSING.value, "Processing request")
            assistant.state_manager.transition_to(AssistantState.PROCESSING, reason="Processing request")

            response = assistant.process_input(clean_input)
            reply = response["reply_text"]
            spoken = response.get("spoken_text") or reply

            print(f"\nZero [{response['state']}] > {reply}\n")
            caption_window.assistant_reply_ready.emit(reply, spoken)

            # Check if assistant transitioned to sleep
            if response["state"] == AssistantState.SLEEPING.value:
                caption_window.state_updated.emit(AssistantState.SLEEPING.value, "Sleeping")
                voice_manager.speak(spoken, wait=True)
                print("\n[Zero is sleeping. Say 'Zero, wake up' or type to resume.]\n")
                continue

            # Speak answer aloud (barge-in monitoring continues active in streaming_listener!)
            caption_window.state_updated.emit(AssistantState.SPEAKING.value, "Speaking response")
            assistant.state_manager.transition_to(AssistantState.SPEAKING, reason="Speaking response")
            voice_manager.speak(spoken, wait=True)

            # When speech completes naturally without interruption
            if assistant.state_manager.current_state != AssistantState.INTERRUPTED:
                assistant.state_manager.transition_to(AssistantState.LISTENING, reason="Speech complete")
                caption_window.state_updated.emit(AssistantState.LISTENING.value, "Listening for speech")

    coordinator_thread = threading.Thread(target=_voice_coordinator, name="ZeroVoiceCoordinator", daemon=True)
    coordinator_thread.start()

    try:
        qt_app.exec()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        stop_event.set()
        if streaming_listener:
            streaming_listener.stop()
        voice_manager.shutdown()
        get_api_server_manager().stop()


def run_cli_interactive():
    """Standard typed terminal CLI session."""
    from app.config.settings import get_settings
    settings = get_settings()

    print("[ZERO AI] Starting in CLI mode...")
    bootstrap_application(start_api_server=True)
    assistant = get_assistant()

    greeting = assistant.wake()
    print(f"\nZero > {greeting}\n")

    try:
        while True:
            user_input = input("User > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                farewell = assistant.sleep()
                print(f"\nZero > {farewell}\n")
                assistant.shutdown()
                break

            response = assistant.process_input(user_input)
            print(f"\nZero [{response['state']}] > {response['reply_text']}\n")
    except (KeyboardInterrupt, EOFError):
        print("\n[ZERO AI] Shutting down...")
        assistant.shutdown()
    finally:
        get_api_server_manager().stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zero AI Assistant Launcher")
    parser.add_argument(
        "--api-only", action="store_true", help="Run local REST API server only"
    )
    parser.add_argument(
        "--cli", action="store_true", help="Run interactive terminal CLI assistant"
    )
    parser.add_argument(
        "--voice", action="store_true", help="Run interactive hands-free voice assistant mode"
    )

    args = parser.parse_args()

    if args.api_only:
        run_api_only()
    elif args.voice:
        run_voice_continuous()
    elif args.cli:
        run_cli_interactive()
    else:
        run_gui()
