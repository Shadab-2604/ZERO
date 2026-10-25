# ZERO AI — System Architecture (Phase 1)

## 1. System Overview

Zero is a personal AI system desktop assistant designed with a decoupled, modular Python architecture and a native PySide6 graphical interface inspired by cinematic AI assistants (JARVIS).

```
+---------------------------------------------------------------------------------------+
|                                     ZERO DESKTOP GUI                                  |
|                                                                                       |
|  +--------------------+   +------------------------------------+   +---------------+  |
|  |   SidebarWidget    |   |           QStackedWidget           |   | InfoPanel     |  |
|  | - Assistant Core   |   | - ChatPanelWidget (AI Orb + Chat)  |   | - Live Clock  |  |
|  | - History Archive  |   | - HistoryPanelWidget               |   | - Health HUD  |  |
|  | - Daily Briefing   |   | - BriefingPanelWidget              |   | - Objectives  |  |
|  | - Project Activity |   | - SystemPanelWidget                |   | - Last Session|  |
|  | - System Status    |   | - SettingsPanelWidget              |   |               |  |
|  | - Settings         |   |                                    |   |               |  |
|  +--------------------+   +------------------------------------+   +---------------+  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  |                      StatusBarWidget (Real Subsystem Telemetry)                 |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
                                        ▲
                       Qt Signals / Thread-safe Event Bridge
                                        ▼
+---------------------------------------------------------------------------------------+
|                                  CORE ASSISTANT SUBSYSTEM                             |
|                                                                                       |
|  +-------------------+    +--------------------+    +-------------------------------+ |
|  |   StateManager    |    |    IntentRouter    |    |        BriefingService        | |
|  | (Thread-safe Enum)|    | (Rule/Pattern Match|    | (Truthful History & Health)   | |
|  +-------------------+    +--------------------+    +-------------------------------+ |
|                                       ▲                                               |
|                                       ▼                                               |
|  +---------------------------------------------------------------------------------+  |
|  |                   ConversationManager (Dialogue & Memory Coordinator)           |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
            ▲                                      ▲                        ▲
            ▼                                      ▼                        ▼
+-----------------------+              +-----------------------+  +-------------------+
|  AI PROVIDER ENGINE   |              |   LOCAL FASTAPI REST  |  |  VOICE SUBSYSTEM  |
|                       |              | (127.0.0.1:8765)      |  |                   |
| - BaseAIProvider      |              | - /health             |  | - SpeechSynthesizer
| - DemoAIProvider      |              | - /api/assistant/*    |  | - SpeechRecognizer
| - CloudAIProvider     |              | - /api/briefing/*     |  | - WakeWordListener
| - AIProviderFactory   |              | - /api/settings/*     |  | - VoiceManager    |
+-----------------------+              +-----------------------+  +-------------------+
            ▲                                      ▲                        ▲
            +--------------------------------------+------------------------+
                                        ▼
+---------------------------------------------------------------------------------------+
|                                 MEMORY & PERSISTENCE                                  |
|                                                                                       |
|  - SQLite (data/zero.db) via SQLAlchemy ORM (Thread-safe engine)                      |
|  - Models: Conversation, Message, SessionRecord, ActivityEvent, SessionSummary, Task  |
|  - Repositories: ConversationStore, ActivityStore                                     |
+---------------------------------------------------------------------------------------+
```

---

## 2. Component Breakdown

### 2.1 Graphical User Interface (`app/gui/`)
- **Main Window (`app/gui/main_window.py`)**: Root orchestrator. Connects navigation, views, status bars, and thread-safe Qt state bridges.
- **AI Orb (`app/gui/widgets/ai_orb.py`)**: Reactive vector-painted Qt widget (`QPainter`). Adapts pulsing, rotating orbital arcs, and glow intensity to assistant states without downloading or storing raster assets.
- **Chat Panel (`app/gui/widgets/chat_panel.py`)**: Chat transcript, message bubbles with role-based formatting, push-to-talk button, and background worker threads (`AIWorkerThread`) preventing GUI freezing.
- **Briefing Panel (`app/gui/widgets/briefing_panel.py`)**: Dedicated view for structured briefings, task lists with completion actions, and audit logs.
- **Settings Panel (`app/gui/widgets/settings_panel.py`)**: Live configuration for providers, model names, voice switches, and database retention with masked secret inputs.
- **HUD Info Panel (`app/gui/widgets/info_panel.py`)**: Live clock, telemetry counters, pending objectives, and previous session summary.
- **Status Bar (`app/gui/widgets/status_bar.py`)**: Displays real health checks for the Database, AI Provider, Voice Engine, and Host CPU/RAM.

### 2.2 Core Engine (`app/core/`)
- **State Machine (`app/core/state_manager.py`)**: Thread-safe manager governing `STARTING`, `SLEEPING`, `READY`, `LISTENING`, `THINKING`, `SPEAKING`, and `ERROR` states.
- **Intent Router (`app/core/intent_router.py`)**: Maps natural language utterances and transcripts to intents (`WAKE`, `SLEEP`, `BRIEFING`, `SUMMARIZE_PREVIOUS`, `SHOW_ACTIVITY`, `OPEN_SETTINGS`, `STOP_SPEAKING`, `CANCEL`, `TEXT_MODE`, `CHAT`).
- **Briefing Service (`app/core/briefing_service.py`)**: Compiles truthful, timezone-aware daily briefings strictly from stored database events. Prevents repetitive briefing delivery within the same session.
- **Assistant Coordinator (`app/core/assistant.py`)**: Central singleton mediating between GUI, API, and worker subsystems.

### 2.3 AI Provider Abstraction (`app/ai/`)
- **Base Interface (`app/ai/base.py`)**: Abstract base class defining `generate_response` and `generate_summary`.
- **Demo Provider (`app/ai/providers/demo_provider.py`)**: Honest local offline provider for testing and zero-credential environments. Clearly identifies responses as Demo Mode.
- **Cloud Provider (`app/ai/providers/cloud_provider.py`)**: HTTP REST client supporting OpenAI, Gemini, Anthropic, and Ollama with error recovery and request timeout bounds.
- **Factory (`app/ai/provider_factory.py`)**: Automatically falls back to the Demo provider if external credentials are unconfigured or failing.

### 2.4 Voice Subsystem (`app/voice/`)
- **Speech Synthesis (`app/voice/speech_synthesis.py`)**: Asynchronous text-to-speech worker thread with pyttsx3, COM isolation on Windows, and immediate interruption (`stop`).
- **Speech Recognition (`app/voice/speech_recognition.py`)**: Asynchronous microphone recording and transcription off the main thread.
- **Wake Listener (`app/voice/wake_listener.py`)**: Dedicated background thread detecting the configured wake phrase while filtering out the assistant's own synthesized voice.
- **Manager (`app/voice/manager.py`)**: Coordinates push-to-talk, microphone muting, and lifecycle shutdown.

### 2.5 Memory & Storage (`app/memory/`)
- **Database Engine (`app/memory/database.py`)**: SQLite with SQLAlchemy ORM using parameterized queries, thread safety, automatic schema migrations, and backup capabilities.
- **Models (`app/memory/models.py`)**: Timezone-aware tables for `conversations`, `messages`, `sessions`, `activity_events`, `session_summaries`, `tasks`, and `user_preferences`.
- **Repositories**: `ConversationStore` and `ActivityStore` provide isolated data access methods with transaction rollback guarantees.

### 2.6 Local REST API (`app/api/`)
- FastAPI web server running in a background daemon thread.
- Bound strictly to `127.0.0.1:8765` for security.
- Comprehensive endpoints for state inspection, remote wake/sleep, chatting, briefing retrieval, and settings management.
