# Zero AI — GitHub Collaboration & Developer Documentation Hub

Welcome to the Zero AI documentation center. This directory contains comprehensive, practical, verified documentation for cloning, configuring, running, and contributing to the Zero AI desktop assistant on Windows.

---

## 1. What is Zero AI?

Zero AI is a local-first, privacy-focused desktop assistant inspired by cinematic JARVIS-like interfaces. It operates on a Windows workstation using local open-weight language models (`llama3.2` and `qwen2.5-coder`), an interactive PySide6 graphical interface, a local SQLite Knowledge Base (RAG), real-time streaming voice input with barge-in interruption, a floating Live Caption HUD, and safe, allowlisted Windows desktop automation.

---

## 2. Verified Capabilities & System Architecture

Zero's capabilities are implemented and validated by unit and integration tests:

| Subsystem | Verified Capabilities | Technology |
| :--- | :--- | :--- |
| **Local AI Engine** | Zero cloud dependence. Local chat and technical coding via HTTP REST API. | Ollama, Llama 3.2 (3B), Qwen 2.5 Coder (7B/3B) |
| **Voice & Speech** | Real-time streaming PCM listener, energy VAD, barge-in interruption during TTS, 1.8s silence continuation window, code-aware spoken summaries. | PyAudio, SpeechRecognition, pyttsx3 (SAPI5 COM) |
| **Stitch Desktop GUI** | High-contrast obsidian dark interface with 36px telemetry titlebar, 64px navigation rail, Command Center with procedural AI orb, Live Transcript with Ctrl+F and code execution, and System Control window bento registry with safe allowlisted operations. | PySide6, Obsidian Command Theme, Win32API |
| **Live Caption HUD** | Floating transparent overlay showing live word stream, states (`LISTENING`, `HEARING YOU`, `PROCESSING`, `SPEAKING`, `INTERRUPTED`), markdown & code browser. | PySide6 Qt Widgets |
| **Desktop Automation** | Safe window controls: Focus, Minimize, Restore, Maximize, Tile Left, graceful `WM_CLOSE`. Application discovery via Start Menu shortcuts. Read-only system telemetry (CPU, RAM, Disk, Network). | Windows User32, Win32GUI, WinSta0\Default, psutil |
| **Knowledge Base (RAG)** | Recursive subfolder scanning, SHA-256 deduplication, incremental sync, search citations with relative paths, media rejection. | SQLite FTS5, PyPDF, python-docx, openpyxl |
| **Executive Reports** | HTML report generation with styled typography, tables, and downloadable PDF output. | WeasyPrint / Playwright Chromium |
| **Security Layer** | Strict Python allowlist. Zero arbitrary shell, bash, CMD, PowerShell, file-writing, or registry tools exposed to the LLM. | `ActionRegistry` allowlist |

---

## 3. Supported Environment & Software Requirements

- **Operating System:** Windows 11 (64-bit) or Windows 10 (22H2 64-bit).
- **Python:** Python **3.11** or **3.12** (64-bit). *(Python 3.13 is not recommended due to audio library deprecations).*
- **Git:** Git for Windows (v2.40+).
- **Local AI Server:** Ollama for Windows (v0.3.0+).
- **Hardware Recommended:**
  - CPU: Intel Core i5/i7 (8+ cores) or AMD Ryzen equivalent.
  - RAM: 16 GB minimum (24 GB+ recommended).
  - GPU: Dedicated NVIDIA GPU (4 GB+ VRAM) for accelerated inference, or fast multi-core CPU.
  - Storage: 15 GB+ free SSD space for dependencies and model weights.

---

## 4. Quick Launch Commands

From the project root:

```powershell
# 1. Start Zero AI in Voice Mode with Live Captions HUD:
.\.venv\Scripts\python.exe run.py --voice

# 2. Start Zero AI in Desktop GUI Mode (Chat Window & Telemetry):
.\.venv\Scripts\python.exe run.py

# 3. Start Zero in Headless CLI Mode:
.\.venv\Scripts\python.exe run.py --cli
```

---

## 5. Complete Documentation Index

| Guide | Description |
| :--- | :--- |
| **[`SAFE_GITHUB_PUSH_GUIDE.md`](file:///c:/D-drive/code/ZERO/GitHub/SAFE_GITHUB_PUSH_GUIDE.md)** | Step-by-step instructions for initializing, reviewing, and pushing code to a private GitHub repository without leaking secrets. |
| **[`SETUP_FROM_SCRATCH_WINDOWS.md`](file:///c:/D-drive/code/ZERO/GitHub/SETUP_FROM_SCRATCH_WINDOWS.md)** | Clean installation walkthrough for a new developer setting up Zero on a fresh Windows machine. |
| **[`OLLAMA_LLAMA_LOCAL_SETUP.md`](file:///c:/D-drive/code/ZERO/GitHub/OLLAMA_LLAMA_LOCAL_SETUP.md)** | Installing Ollama, pulling `llama3.2` and `qwen2.5-coder`, GPU verification, and local API testing. |
| **[`COLLABORATION_WORKFLOW.md`](file:///c:/D-drive/code/ZERO/GitHub/COLLABORATION_WORKFLOW.md)** | Branching strategy, pull requests, resolving merge conflicts, and peer review practices. |
| **[`SECURITY_PRE_PUSH_CHECKLIST.md`](file:///c:/D-drive/code/ZERO/GitHub/SECURITY_PRE_PUSH_CHECKLIST.md)** | Mandatory pre-flight checklist to verify no credentials, `.env`, or private files are staged. |
| **[`VERSION_COMPATIBILITY.md`](file:///c:/D-drive/code/ZERO/GitHub/VERSION_COMPATIBILITY.md)** | Official version matrix for Python, Git, Ollama, PySide6, and project dependencies. |
| **[`TROUBLESHOOTING.md`](file:///c:/D-drive/code/ZERO/GitHub/TROUBLESHOOTING.md)** | Solutions for common audio device locks, Ollama connection timeouts, COM errors, and window management quirks. |

---

## 6. Known Limitations & Unimplemented Features

To maintain complete architectural honesty, the following capabilities are currently scoped for future milestones:
- **Offline ASR:** Current streaming recognition defaults to the Google Web Speech API with PocketSphinx fallback. GPU-accelerated local `faster-whisper` is planned for Phase 2.
- **Neural Wake Word:** Wake detection currently uses audio frame phrase matching. A lightweight dedicated neural model (`openWakeWord`) is not yet embedded.
- **Multi-Turn Tool Chaining:** Desktop actions currently execute one atomic tool per turn (e.g., *"Zero, open Chrome"*). Multi-step compound workflows (e.g., *"Open Chrome, then minimize VS Code"*) are handled sequentially across separate voice turns.
- **OS Security Boundary:** The Python allowlist restricts what tools the AI can dispatch, but the process runs with your Windows user permissions. It is not an OS-level hypervisor sandbox.
