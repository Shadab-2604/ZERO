# Zero AI — Windows Installation & Operation Guide

Welcome to **Zero AI**, a personal desktop AI assistant inspired by JARVIS, built with Python, PySide6, FastAPI, and SQLite FTS5.

This document provides complete, tested instructions for installing, configuring, operating, and troubleshooting Zero AI on Windows 10 and Windows 11.

---

## 1. System Requirements & Prerequisites

### Required Software
* **Operating System:** Windows 10 (64-bit) or Windows 11 (64-bit).
* **Python Runtime:** Python **3.11** or **3.12** (64-bit). *Note: Python 3.12.10 is recommended.*
* **Shell:** Windows PowerShell or Command Prompt.
* **Network:** Internet access for initial package downloads and optional cloud AI providers.
* **Audio Hardware:** Working microphone (for speech input) and speakers/headphones (for voice synthesis).

> [!IMPORTANT]
> When installing Python from [python.org](https://www.python.org/downloads/windows/), ensure you check:
> **☑ Add python.exe to PATH**

---

## 2. Quick Automated Setup (Recommended)

Run the automated Windows setup script from an elevated or standard PowerShell terminal in the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

The script will automatically:
1. Verify Python 3.11+ runtime.
2. Create the project-local virtual environment (`.venv`).
3. Upgrade pip and install all dependencies from `requirements.txt`.
4. Install the required Playwright Chromium headless browser.
5. Ensure `Knowledge/`, `exports/`, `data/`, and `logs/` directories exist.
6. Initialize `.env` safely from `.env.example` without overwriting valid keys.
7. Run the system diagnostics doctor (`scripts/doctor.py`).

---

## 3. Step-by-Step Manual Installation

If you prefer to configure the environment manually, follow these steps:

### Step 3.1: Verify Python Version
Open PowerShell and verify:
```powershell
python --version
```
Expected output: `Python 3.11.x` or `Python 3.12.x`.

### Step 3.2: Create and Activate Virtual Environment
```powershell
# Navigate to project root
cd c:\D-drive\code\ZERO

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

### Step 3.3: Install Python Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.4: Install Playwright Chromium Browser
Zero generates high-fidelity executive PDF reports using headless Chromium:
```powershell
playwright install chromium
```

### Step 3.5: Ensure Project Directories Exist
```powershell
New-Item -ItemType Directory -Force -Path Knowledge, data, exports, logs, scripts, tests | Out-Null
```

---

## 4. Configuring Environment & Secrets Safely

Copy `.env.example` to `.env` if `.env` does not already exist:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

### Configuration Keys Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `AI_PROVIDER` | `demo` | Active intelligence provider (`demo`, `openai`, `gemini`, `anthropic`, `ollama`) |
| `AI_API_BASE` | *(Empty / default)* | Target API base URL (e.g. `https://agent-router.net/aggregate/openai/v1`) |
| `AI_API_KEY` | *(Empty)* | API Key. Masked in UI and never printed to terminal or logs. |
| `AI_MODEL` | *(Auto-selected)* | Target model ID (e.g. `gpt-4o-mini`, `gemini-1.5-flash`) |
| `VOICE_ENABLED` | `false` | Enable or disable microphone STT and speaker TTS |
| `WAKE_WORD_ENABLED`| `false` | Background wake detection ("Zero, wake up") |
| `TTS_VOICE_RATE` | `180` | Speech synthesis speed (Words Per Minute) |
| `TTS_VOICE_VOLUME`| `0.9` | Speech synthesis volume (0.0 to 1.0) |
| `DATABASE_URL` | `sqlite:///./data/zero.db` | Local SQLite database path |
| `TIMEZONE` | `Asia/Kolkata` | User local timezone for briefings |

> [!TIP]
> **Offline Demo Mode:** Zero runs immediately without any API key in `demo` mode. All UI, knowledge base search, speech commands, and PDF generation work offline.

---

## 5. Optional Components (OCR & Office Converters)

Zero includes built-in native parsers for PDF, DOCX, PPTX, XLSX, CSV, JSON, Markdown, and 25+ programming languages. Optional legacy formats can be enabled:

1. **Optical Character Recognition (OCR) for Images (`.png`, `.jpg`):**
   * Download and install Tesseract OCR for Windows from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
   * Ensure `tesseract.exe` is added to your Windows system `PATH`.
   * Install python wrapper: `pip install pytesseract`.

2. **Legacy Office Formats (`.doc`, `.ppt`, `.xls`, `.odt`):**
   * Install LibreOffice for Windows from [libreoffice.org](https://www.libreoffice.org/).
   * Ensure `soffice.exe` is in your Windows `PATH`. Zero will automatically detect it and convert legacy binary office documents during ingestion.

---

## 6. Pre-Flight Diagnostic Checks

Run the system doctor to verify that all subsystems are operational:

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
```

### Test AI Connection (Optional Cloud Providers)
If you have configured an API key in `.env`:
```powershell
.\.venv\Scripts\python.exe scripts\test_ai_connection.py
```

### Test Knowledge Indexing & Search
```powershell
.\.venv\Scripts\python.exe scripts\test_knowledge.py
```

### Test PDF Generation Pipeline
```powershell
.\.venv\Scripts\python.exe scripts\test_pdf_export.py
```

---

## 7. Launching Zero AI

Launch the desktop assistant:

```powershell
.\.venv\Scripts\python.exe run.py
```

The application will start:
* **Desktop GUI:** PySide6 HUD window with real-time audio orb, navigation sidebar, chat transcript, and live status bar.
* **Local REST API:** Running in a background daemon thread on `http://127.0.0.1:8765`.
* **Knowledge Base Engine:** Monitoring the `Knowledge/` folder for document queries.

---

## 8. Operating Features

### 8.1 Knowledge Base (`Knowledge/` Folder & RAG)
1. Drop documents (`.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.txt`, `.md`, source code files) directly into `Knowledge/`.
2. Open the **📚 Knowledge Base** view in the sidebar.
3. Click **🔄 Reindex All** or search your documents directly.
4. In the Chat panel, ask questions about your documents (e.g. *"What is in the architecture document?"* or *"Zero, search my knowledge for API endpoints"*).
5. Zero will cite the exact document and section/page: `[Doc: filename.md (Section Name)]`.

### 8.2 Voice Interaction & Commands
When voice is enabled in **⚙️ Settings**:
* **"Zero, wake up"** — Activates Zero, wakes the assistant, and delivers a natural briefing of recent tasks.
* **"Zero, sleep"** — Returns Zero to idle sleep mode.
* **"Zero, stop speaking"** — Immediately interrupts and silences voice synthesis without losing the transcript.
* **"Zero, repeat that"** — Speaks the previous response aloud again.
* **"Zero, search my knowledge for [topic]"** — Executes targeted full-text retrieval on your local knowledge base.
* **"Zero, rebuild knowledge"** — Triggers a full rescan and reindex of the `Knowledge/` directory.

> [!NOTE]
> Code blocks are displayed with full syntax highlighting in the chat window, but are summarized naturally in voice speech so Zero doesn't recite complex syntax character-by-character.

### 8.3 PDF Document Generation
Ask Zero to create a report or document:
* *"Zero, generate a project plan for our mobile app"*
* *"Zero, create a report on system architecture"*
* *"Export notes to pdf"*

Zero will compile an executive HTML document, render it with Playwright Chromium, and display a clickable **📥 Download PDF** button directly in the conversation transcript. Generated files are saved safely to `exports/`.

### 8.4 Searchable History
* Select **💬 Conversation History** from the sidebar.
* Type any keyword into the search bar to filter conversations in real-time.
* Click any conversation thread to view past messages or resume the discussion.
* Delete individual conversations or clear all records with a confirmation dialog.

---

## 9. Troubleshooting & FAQ

### Problem: "No module named 'pyaudio'" or Microphone Input Fails
* **Solution:** Install the precompiled Windows wheel:
  ```powershell
  .\.venv\Scripts\python.exe -m pip install PyAudio
  ```
* Verify your microphone permissions in **Windows Settings > Privacy & Security > Microphone**.

### Problem: PDF Generation Fails with "Executable doesn't exist at..."
* **Solution:** Playwright requires its Chromium browser binary:
  ```powershell
  .\.venv\Scripts\python.exe -m playwright install chromium
  ```

### Problem: Speech Synthesis Sounds Robotic or Doesn't Play
* **Solution:** In **⚙️ Settings > Voice Controls**:
  * Adjust the **Speech Rate** (recommended: 170-190 WPM).
  * Select your preferred output voice (e.g. *Microsoft David Desktop* or *Microsoft Zira Desktop*).
  * Click **🔊 Test Voice Output** to verify audio output.

### Problem: AI Connection Test Times Out
* **Solution:** Verify that your proxy or firewall allows outgoing HTTPS requests to `https://agent-router.net` or your configured base URL.

---

## 10. Maintenance & Backup

### Backing Up Data
All conversation history and knowledge index tables are stored in `data/zero.db`.
* In **⚙️ Settings**, click **Backup Database** to generate a timestamped backup in `data/backups/`.
* Your documents in `Knowledge/` and generated PDFs in `exports/` are standard files and can be backed up with any backup tool.

### Running Automated Tests
Run the full 71-test validation suite:
```powershell
.\.venv\Scripts\pytest.exe -v
```

---

## 11. Safe Uninstall Instructions

To cleanly uninstall Zero AI:
1. Close the Zero desktop window.
2. Delete the virtual environment folder:
   ```powershell
   Remove-Item -Recurse -Force .venv
   ```
3. (Optional) Remove local database and generated exports if you no longer need them:
   ```powershell
   Remove-Item -Recurse -Force data, exports, logs
   ```
4. Your original files in `Knowledge/` remain untouched.
