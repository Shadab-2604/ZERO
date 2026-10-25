# ZERO AI — JARVIS Desktop Assistant (Phase 1: Foundation)

Zero is a personal AI system desktop assistant inspired by cinematic AI interfaces. Built with a modular Python backend and a futuristic native PySide6 desktop GUI, Zero features reactive state-driven animated vector HUD elements, asynchronous audio/speech pipelines, local REST APIs, persistent SQLite activity and memory stores, and honest offline demo capabilities.

---

## Key Features

1. **Futuristic Cinematic GUI (PySide6)**:
   - Primary near-black palette (`#050505`) with `#00FF88` neon green accents.
   - Vector-animated reactive AI Orb featuring dynamic pulsing outer rings, glowing core, and state-adaptive visual feedback (SLEEPING, READY, LISTENING, THINKING, SPEAKING, ERROR).
   - Interactive Left Navigation Sidebar, Main Assistant Transcript, Collapsible Right HUD Telemetry Panel, and Real-time Status Bar.

2. **Wake & Sleep State Engine**:
   - Explicit Assistant State Machine: `STARTING`, `SLEEPING`, `READY`, `LISTENING`, `THINKING`, `SPEAKING`, `ERROR`.
   - Voice and text commands: `"Zero, wake up"`, `"Zero, sleep"`, `"Zero, give me today's briefing"`, `"Zero, summarize yesterday's work"`, `"Zero, stop speaking"`, and `"Zero, open settings"`.

3. **Truthful Daily Briefing & Project Memory**:
   - Local timezone-aware greetings (`"Good morning"`, `"Good afternoon"`, `"Good evening"`).
   - Generates authentic briefings from local activity events, session summaries, task items, and health checks.
   - Zero fabrication: On a fresh launch, truthfully states it is the first recorded session without inventing phantom tasks.
   - Avoids repetitive duplicate briefings within the same active session unless explicitly prompted.

4. **Modular AI Provider Abstraction**:
   - Built-in honest **Local Demo AI Provider**: Works 100% offline without requiring external API keys.
   - Plug-and-play Cloud Provider abstraction: Supports OpenAI, Gemini, Anthropic, and local Ollama via environment variables.

5. **Integrated Local REST API (FastAPI)**:
   - Bound to `127.0.0.1:8765` for desktop isolation and security.
   - Endpoints:
     - `GET /health`: Comprehensive subsystem telemetry.
     - `GET /api/assistant/state`: Live assistant state.
     - `POST /api/assistant/wake`: Wake assistant.
     - `POST /api/assistant/sleep`: Sleep assistant.
     - `POST /api/assistant/chat`: Converse with Zero.
     - `GET /api/briefing/today`: Retrieve current briefing.
     - `GET /api/activity/recent`: Recent stored activity.
     - `GET /api/settings/public`: Safe non-secret settings.

6. **Desktop Audio Subsystem**:
   - Asynchronous speech synthesis (TTS via pyttsx3) and speech recognition (STT via SpeechRecognition) running in dedicated background worker threads to keep the UI smooth and non-blocking.
   - Non-blocking push-to-talk, speech interruption (`"Zero, stop speaking"`), and microphone mute switch.

---

## Quick Start Guide

### 1. Requirements
- Python 3.11 or Python 3.12 (64-bit recommended)
- Windows, Linux, or macOS

### 2. Windows Installation & Launch
Run the automated batch script:
```cmd
run.bat
```
This script will automatically:
1. Verify Python availability.
2. Create `.venv` if not already present.
3. Seed `.env` from `.env.example`.
4. Install all dependencies from `requirements.txt`.
5. Launch the Zero AI Desktop Assistant.

### 3. Linux / macOS Launch
Run the startup shell script:
```bash
chmod +x run.sh
./run.sh
```

### 4. Manual Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
pip install -e . --no-deps

# Seed configuration
cp .env.example .env

# Launch application
python run.py
```

### 5. Execution Modes
- **Streaming Voice Assistant with Live Captions HUD**:
  ```bash
  python run.py --voice
  ```
- **Desktop GUI + API Server (Default)**:
  ```bash
  python run.py
  ```
- **Interactive Terminal Assistant (CLI mode)**:
  ```bash
  python run.py --cli
  ```
- **Local REST API only (Headless mode)**:
  ```bash
  python run.py --api-only
  ```

---

## Collaboration & Developer Documentation

For complete, step-by-step developer guides on contributing, setting up on a fresh machine, and configuring local Ollama models:

- 📖 **[GitHub Documentation Hub](file:///c:/D-drive/code/ZERO/GitHub/README.md)**: Main developer and collaboration center.
- 🚀 **[Setup from Scratch on Windows](file:///c:/D-drive/code/ZERO/GitHub/SETUP_FROM_SCRATCH_WINDOWS.md)**: Clean installation for new contributors.
- 🦙 **[Local Ollama & Llama Setup](file:///c:/D-drive/code/ZERO/GitHub/OLLAMA_LLAMA_LOCAL_SETUP.md)**: 100% offline open-weight model setup.
- 🛡️ **[Safe GitHub Push Guide](file:///c:/D-drive/code/ZERO/GitHub/SAFE_GITHUB_PUSH_GUIDE.md)**: Step-by-step safe Git initialization and push.
- 🔒 **[Security Pre-Push Checklist](file:///c:/D-drive/code/ZERO/GitHub/SECURITY_PRE_PUSH_CHECKLIST.md)**: Secret audit and privacy verification.
- 🤝 **[Collaboration Workflow](file:///c:/D-drive/code/ZERO/GitHub/COLLABORATION_WORKFLOW.md)**: Branching, pull requests, and peer review.
- 📋 **[Version Compatibility Matrix](file:///c:/D-drive/code/ZERO/GitHub/VERSION_COMPATIBILITY.md)**: Validated software and dependency versions.
- 🔧 **[Troubleshooting Guide](file:///c:/D-drive/code/ZERO/GitHub/TROUBLESHOOTING.md)**: Audio device, SAPI5, and Ollama diagnostics.
- 📜 **[Contributing Guidelines](file:///c:/D-drive/code/ZERO/CONTRIBUTING.md)** & **[Security Policy](file:///c:/D-drive/code/ZERO/SECURITY.md)**


---

## Configuration & Environment Variables

Copy `.env.example` to `.env` to configure Zero:

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Zero` | Assistant identity name |
| `APP_ENV` | `development` | Operating environment (`development`, `production`, `testing`) |
| `APP_HOST` | `127.0.0.1` | Local REST API host (loopback isolation) |
| `APP_PORT` | `8765` | Local REST API port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `AI_PROVIDER` | `demo` | AI model provider (`demo`, `openai`, `gemini`, `anthropic`, `ollama`) |
| `AI_API_KEY` | *(empty)* | Secret key for cloud provider (never displayed or logged) |
| `AI_MODEL` | *(empty)* | Custom model name (e.g. `gpt-4o-mini`, `gemini-1.5-flash`) |
| `VOICE_ENABLED` | `false` | Enable or disable voice audio I/O |
| `WAKE_WORD_ENABLED` | `false` | Enable continuous wake word listener |
| `WAKE_WORD` | `zero wake up` | Wake phrase |
| `DATABASE_URL` | `sqlite:///./data/zero.db` | Persistent database path |
| `TIMEZONE` | `Asia/Kolkata` | Local timezone for greetings and timestamps |
| `BRIEFING_ON_STARTUP` | `true` | Deliver briefing upon initial launch |
| `BRIEFING_ON_WAKE` | `true` | Deliver briefing upon wake command |

---

## Running the Automated Test Suite

Zero includes an automated test suite covering all 18 core verification scenarios:
```bash
.venv\Scripts\pytest.exe -v
```

---

## Project Structure

```
zero/
├── app/
│   ├── main.py                     # GUI desktop entrypoint
│   ├── bootstrap.py                # Subsystem initialization & boot sequence
│   ├── config/                     # Settings & rotating log configuration
│   ├── api/                        # FastAPI local loopback server & routes
│   ├── core/                       # State machine, intent router, briefing, assistant
│   ├── ai/                         # Provider abstraction, demo provider, cloud provider
│   ├── voice/                      # TTS engine, speech recognizer, wake listener
│   ├── memory/                     # SQLite database models, conversation & activity stores
│   ├── system/                     # Subsystem health monitor & telemetry
│   ├── gui/                        # PySide6 windows, theme QSS, and HUD widgets
│   └── utils/                      # Path resolution & timezone utilities
├── data/                           # Local SQLite database files
├── logs/                           # Rotating application logs
├── tests/                          # Automated pytest test suites
├── docs/                           # Architectural & setup documentation
├── .env.example                    # Documented configuration template
├── requirements.txt                # Pinned dependency specifications
├── run.py                          # Unified launcher (GUI, CLI, API-only)
├── run.bat                         # Windows launch script
├── run.sh                          # Linux/macOS launch script
└── README.md
```
