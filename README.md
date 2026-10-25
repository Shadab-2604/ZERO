# ZERO AI — Personal Desktop Assistant

Zero is an advanced, local-first personal AI desktop assistant inspired by cinematic AI interfaces (JARVIS). Built with a decoupled, high-performance Python architecture and a native PySide6 graphical interface, Zero features reactive vector HUD elements, a real-time floating Live Caption HUD, streaming PCM Voice Activity Detection (VAD) with instant barge-in interruption, a local SQLite FTS5 Knowledge RAG store, safe allowlisted Windows desktop automation, and 100% offline open-weight LLM inference powered by Ollama.

---

## 🌟 Key Capabilities

1. **Local-First AI Intelligence (Ollama HTTP 127.0.0.1:11434)**:
   - **Dual-Model Intelligent Routing**:
     - **General Assistant**: `llama3.2:latest` (3B) for ultra-fast, natural conversational responses, summaries, and daily briefings.
     - **Coding & Engineering**: `qwen2.5-coder:7b` for code synthesis, multi-file refactoring, debugging, and SQL queries.
     - **Deterministic Calculations**: Evaluated locally in Python using AST parsing for 100% precision with zero LLM arithmetic hallucination.
   - **Zero Cloud Leakage**: No conversation or personal data ever leaves your computer.

2. **Real-Time Streaming Voice & Floating Live Caption HUD**:
   - **Low-Latency Streaming PCM Audio**: Uses PyAudio with dynamic RMS energy Voice Activity Detection (VAD).
   - **Silence Continuation Window**: 1.8-second pause threshold with up to 5.0-second continuation to let you pause mid-thought without premature submission.
   - **Instant Barge-In Interruption**: Start speaking at any point during assistant speech to instantly halt Windows SAPI5 TTS playback and transition to the `INTERRUPTED` state.
   - **Floating Semi-Transparent HUD**: Transcribes user speech and displays assistant responses in real-time above other desktop windows.

3. **Local Knowledge RAG Engine (`Knowledge/`)**:
   - Ingests user-provided reference documents (`.pdf`, `.docx`, `.pptx`, `.xlsx`, `.txt`, `.md`).
   - SQLite FTS5 full-text indexing with BM25 keyword relevance ranking and SHA-256 content deduplication.
   - Grounded context retrieval with relative file path citations in assistant responses.

4. **Safe Windows Desktop Automation & System Diagnostics**:
   - Enumerate visible application windows, window states (normal, minimized, maximized), and process telemetry.
   - Bring windows to foreground, minimize, maximize, and restore.
   - Graceful application closure via `WM_CLOSE` (detects unsaved prompts without auto-dismissing).
   - Launch verified applications from an approved system allowlist (Chrome, Notepad, Calc, Explorer, Terminal, Task Manager).
   - Deep network diagnostics (DNS lookup, ICMP ping latency, network interface enumeration, socket port connectivity).
   - Strict security: Zero arbitrary shell execution, zero registry writes, zero administrator elevation.

5. **Verified HTML-to-PDF Document Generation (`exports/`)**:
   - Compiles executive markdown reports into modern styled HTML documents with syntax-highlighted code boxes and structured tables.
   - Headless Chromium rendering via Playwright exporting verified PDF artifacts directly into `exports/`.

6. **Stitch Obsidian Command PySide6 Desktop GUI**:
   - High-contrast obsidian dark palette (`#050505` canvas, `#101412` surface, `#151A18` container, `#1E2623` border) with `#00FF88` cybernetic neon green accents.
   - **Unified 36px Titlebar**: Integrated window title, active local model chip (`llama3.2 [LOCAL]`), real-time CPU & RAM hardware telemetry, and native window actions.
   - **64px Slim Navigation Rail**: Quick navigation across Command Center, Live Transcript & Code, Knowledge Vault, System Control, Model Settings, and Diagnostics.
   - **Command Center Screen**: Live telemetry inference (Ollama latency, sensor states, memory), Procedural dynamic AI Core Orb with reactive state transitions (`READY`, `LISTENING`, `HEARING YOU`, `PROCESSING`, `SPEAKING`, `INTERRUPTED`, `ERROR`), Quick Action Deck (*Analyze Display*, *Index Local Docs*, *Automate Active App*, *Export Session PDF*), and real-time auditable event stream.
   - **Live Voice Transcript & Code Intelligence Screen**: Dual-pane workspace with live activity filters (*All Activity*, *Speech Only*, *Code Outputs*, *Tool Executions*), instant `Ctrl+F` search, TTS speech re-synthesis (*Listen Again*), syntax-formatted code container with line numbering, copy action, and safe, user-confirmed execution sandbox.
   - **System Control & Automation Screen**: Live Managed Windows Registry bento grid populated from real Win32 APIs, window actions (*Focus*, *Minimize*, *Maximize*, *Restore*, *Graceful Close* with unsaved work prompt protection, *Send to Background*, *Tile Left*), Command Palette (`Ctrl+K`), and Target Ambiguity Resolution modal.
   - **Persistent 40px Bottom Voice Dock**: Dynamic real-time audio equalizer bars, state badge, microphone mute toggle, speech interruption (`[ESC]`), and force push-to-talk (`Hold [Space]`).

7. **Isolated Local REST API (FastAPI 127.0.0.1:8765)**:
   - Loopback-bound REST API for process isolation and IPC.
   - Endpoints for health telemetry, assistant state, chat conversation, briefings, knowledge sync, and artifact downloads.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **OS**: Windows 10/11 (64-bit recommended)
- **Python**: 3.11 or 3.12
- **Ollama**: Installed and running locally (`ollama serve`)
  ```powershell
  ollama pull llama3.2
  ollama pull qwen2.5-coder:7b
  ```

### 2. Launching Zero

Launch Zero using the unified `run.py` entry point:

- **Desktop GUI Mode (Default)**:
  ```powershell
  .\.venv\Scripts\python.exe run.py
  ```
- **Streaming Voice Assistant with Floating Live Caption HUD**:
  ```powershell
  .\.venv\Scripts\python.exe run.py --voice
  ```
- **Interactive Terminal Assistant (CLI Mode)**:
  ```powershell
  .\.venv\Scripts\python.exe run.py --cli
  ```
- **Headless Local REST API Server**:
  ```powershell
  .\.venv\Scripts\python.exe run.py --api-only
  ```

Or double-click `run.bat` on Windows.

---

## 📁 Repository Structure

```text
ZERO/
├── app/
│   ├── __init__.py           # Subsystem package root metadata and versioning
│   ├── bootstrap.py          # Unified application bootstrap and hardware discovery
│   ├── main.py               # GUI mode entry point runner
│   ├── ai/                   # Local AI abstraction, Ollama routing, and connectivity tests
│   ├── api/                  # Isolated loopback REST API server (FastAPI 127.0.0.1:8765)
│   ├── config/               # Pydantic Settings and rotating logging setup
│   ├── controllers/          # Canonical controller facade re-exporting assistant components
│   ├── core/                 # Central assistant engine, state machine, calculator, intent router
│   ├── database/             # Canonical database facade re-exporting engine and models
│   ├── exports/              # Document compilation and verified Playwright PDF artifact generation
│   ├── gui/                  # PySide6 desktop graphical interface, theme QSS, and widgets
│   ├── knowledge/            # Local RAG knowledge base subsystem (parsers, chunker, FTS5 store)
│   ├── memory/               # SQLite database models, conversation & activity repositories
│   ├── models/               # Canonical schemas and database models facade
│   ├── services/             # High-level services facade (desktop control, window manager)
│   ├── system/               # System health and hardware diagnostic probes
│   ├── tools/                # Approved security-allowlisted tools and action registry
│   ├── ui/                   # Canonical UI facade re-exporting MainWindow and HUD
│   ├── utils/                # Path resolution and timezone utilities
│   └── voice/                # Real-time audio streaming, VAD, SAPI5 TTS, and wake listener
├── Knowledge/                # User reference documents for local RAG (.pdf, .docx, .txt, etc.)
├── data/                     # Local SQLite database (zero.db)
├── exports/                  # Generated verified PDF reports and documents
├── logs/                     # Rotating application execution logs (zero.log)
├── scripts/                  # Standalone diagnostic, evaluation, and benchmark scripts
├── tests/                    # 187 automated unit, integration, and red-team evaluation tests
├── docs/                     # Architectural, cleanup, and developer guides
├── GitHub/                   # GitHub collaboration and setup documentation
├── .env.example              # Template configuration file with default parameters
├── .gitignore                # Comprehensive Git exclusion rules
├── pyproject.toml            # Project packaging metadata and test configurations
├── requirements.txt          # Pinned compatible Python runtime dependencies
├── run.py                    # Multi-mode unified CLI entry point
├── run.bat                   # Windows batch launcher script
└── run.sh                    # Linux/macOS launcher script
```

---

## ⌨️ Desktop Keyboard Shortcuts

| Shortcut | Scope | Action |
| :--- | :--- | :--- |
| `Ctrl+K` | Global / System Control | Open Command Palette / Window Quick Query |
| `Ctrl+F` | Transcript Workspace | Search dialogue history with instant match navigation |
| `Win+Shift+Z` | System-wide Hotkey | Bring Z.E.R.O. window to foreground or restore from tray |
| `Esc` | Voice Playback | Instant barge-in speech interruption |
| `Hold [Space]` | Footer Voice Dock | Push-to-talk force microphone recording |

---

## 🧪 Automated Testing

Zero includes an extensive automated test suite covering all subsystems (192 tests):

```powershell
# Run the complete test suite (192 tests, 100% passing)
.\.venv\Scripts\python.exe -m pytest

# Run with verbose test-by-test reporting
.\.venv\Scripts\python.exe -m pytest -v

# Run targeted subsystem test suites
.\.venv\Scripts\python.exe -m pytest tests/test_stitch_gui_integration.py
.\.venv\Scripts\python.exe -m pytest tests/test_local_ollama_integration.py
.\.venv\Scripts\python.exe -m pytest tests/test_desktop_control.py
.\.venv\Scripts\python.exe -m pytest tests/test_voice_interruption_and_captions.py
.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_and_rag.py
```

---

## 📖 Documentation Directory

- 📐 **[System Architecture Guide](file:///c:/D-drive/code/ZERO/docs/ARCHITECTURE.md)**: Full component breakdown, Mermaid sequence diagrams, and extension tutorials.
- 🧹 **[Codebase Audit & Cleanup Plan](file:///c:/D-drive/code/ZERO/docs/CODEBASE_AUDIT_AND_CLEANUP_PLAN.md)**: Structural audit and modularization plan.
- 📋 **[Cleanup Candidates Inventory](file:///c:/D-drive/code/ZERO/docs/CLEANUP_CANDIDATES.md)**: Evaluation of artifacts, mockups, and cache files.
- 🚀 **[Windows Setup Guide](file:///c:/D-drive/code/ZERO/INSTALL_WINDOWS.md)**: Complete guide to setting up Zero, Python, and Ollama on Windows.
- 🤝 **[GitHub Developer Hub](file:///c:/D-drive/code/ZERO/GitHub/README.md)**: Collaboration guide, safe git push workflows, and pre-push security checklists.
- 📜 **[Contributing Guidelines](file:///c:/D-drive/code/ZERO/CONTRIBUTING.md)** & **[Security Policy](file:///c:/D-drive/code/ZERO/SECURITY.md)**
