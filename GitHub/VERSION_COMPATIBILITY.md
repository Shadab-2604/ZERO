# Zero AI — Version Compatibility & Runtime Matrix

**Verification Date:** October 25, 2026  
**Auditor / Engineer:** Senior Python AI Systems Architect  
**Project Workspace:** `C:\D-drive\code\ZERO`

---

## 1. System Runtime Matrix

| Component | Verified Local Version | Recommended Version Range | Official Source | Compatibility Status & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Operating System** | Windows 11 (24H2 / 64-bit) | Windows 11 / Windows 10 (22H2+) | [microsoft.com/windows](https://www.microsoft.com/windows) | **Fully Compatible.** Win32 API and desktop UI automation tested. |
| **Python** | **3.12.10** (64-bit) | **3.11.x – 3.12.x** | [python.org/downloads](https://www.python.org/downloads/) | **Tested & Supported.** <br>⚠️ **Do NOT use Python 3.13:** Python 3.13 drops `aifc` and `audioop` from standard library, breaking `SpeechRecognition`. |
| **Git for Windows**| **2.54.0.windows.1** | 2.40.0+ | [git-scm.com/download/win](https://git-scm.com/download/win) | **Fully Compatible.** Includes Git Credential Manager for HTTPS auth. |
| **Ollama** | **0.34.2** | 0.3.0+ | [ollama.com/download/windows](https://ollama.com/download/windows) | **Fully Compatible.** Supports local REST endpoints on `127.0.0.1:11434`. |
| **PyAudio** | **0.2.14** | 0.2.14 | [pypi.org/project/PyAudio](https://pypi.org/project/PyAudio/) | **Tested & Supported.** Requires PortAudio C-bindings bundled in Windows wheel. |

---

## 2. Core Python Dependencies

| Package | Local Installed | `requirements.txt` Constraint | Purpose & Compatibility Notes |
| :--- | :--- | :--- | :--- |
| **`PySide6`** | 6.8.3 | `>=6.6.0,<6.9.0` | Desktop Qt6 interface, vector HUD, live caption overlay. |
| **`fastapi`** | 0.115.14 | `>=0.110.0,<0.116.0` | Local isolated REST API server (`127.0.0.1:8765`). |
| **`uvicorn`** | 0.32.1 | `[standard]>=0.28.0,<0.33.0` | ASGI web server. |
| **`pydantic`** | 2.14.1 | `>=2.6.0,<3.0.0` | Data modeling and schema validation (V2). |
| **`pydantic-settings`**| 2.16.1 | `>=2.2.0,<3.0.0` | Environment settings from `.env`. |
| **`sqlalchemy`** | 2.0.55 | `>=2.0.28,<2.1.0` | SQLite thread-safe persistence and ORM. |
| **`httpx`** | 0.28.1 | `>=0.27.0,<0.29.0` | Async HTTP client for Ollama API communication. |
| **`psutil`** | 6.1.1 | `>=5.9.8,<7.0.0` | Windows system telemetry and running process enumeration. |
| **`pyttsx3`** | 2.99 | `>=2.90` | Offline Windows SAPI5 text-to-speech engine. |
| **`pywin32`** | 312 | `>=306` | Windows Win32 API bindings for window control and COM STA. |
| **`SpeechRecognition`**| 3.17.0 | `>=3.10.0` | Audio frame speech transcription. |
| **`playwright`** | 1.64.1 | `>=1.40.0` | Headless Chromium engine for HTML-to-PDF export. |
| **`pytest`** | 8.4.2 | `>=8.1.0,<9.0.0` | Automated testing framework. |
| **`pytest-asyncio`** | 0.25.3 | `>=0.23.0,<0.26.0` | Async test fixtures. |

---

## 3. Supported Local Language Models

| Model Tag | Size on Disk | Context Window | Architecture | Recommended Usage in Zero |
| :--- | :--- | :--- | :--- | :--- |
| **`llama3.2:latest`** (3B) | ~2.0 GB | 128k tokens | Meta Llama 3.2 | **Default Chat Model.** Conversational responses, briefings, general queries. |
| **`llama3.2:1b`** (1B) | ~1.3 GB | 128k tokens | Meta Llama 3.2 | Low-RAM systems (<8 GB RAM). Fast response, basic reasoning. |
| **`qwen2.5-coder:7b`** (7B) | ~4.7 GB | 32k tokens | Alibaba Qwen 2.5 | **Technical / Coding Specialist.** Complex Python/C++ code generation. |
| **`qwen2.5-coder:3b`** (3B) | ~1.9 GB | 32k tokens | Alibaba Qwen 2.5 | Lightweight coding assistant for laptops without dedicated GPU. |

---

## 4. Known Platform Constraints

1. **Python 3.13 Deprecations:**
   Python 3.13 dropped legacy audio modules (`aifc` and `audioop`). The `SpeechRecognition` library relies on these internals when processing WAV chunk headers. Zero must be run under Python 3.11 or Python 3.12 until upstream libraries publish Python 3.13 native wheels.
2. **Windows SAPI5 COM Threading:**
   The Windows SAPI5 speech synthesizer requires Single-Threaded Apartment (STA) COM initialization. `app/voice/speech_synthesis.py` encapsulates this inside a dedicated worker thread with `pythoncom.CoInitialize()`. Direct calls from non-worker threads without COM initialization will raise Windows COM error `0x800401f0`.
3. **Interactive Desktop Station (`WinSta0\Default`):**
   Windows security isolates background services from interactive user desktops. Zero's desktop control engine uses `OpenDesktopW('Default')` to discover and manage interactive windows safely without requiring elevated administrator privileges.
