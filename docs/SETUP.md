# ZERO AI — Setup & Configuration Guide

This guide covers complete installation, environment configuration, launching instructions, and troubleshooting for Zero AI.

---

## 1. Prerequisites

- **Python**: 3.11 or 3.12 (64-bit recommended)
- **Git** (optional, for version control)
- **Operating System**: Windows 10/11, Ubuntu 22.04+, or macOS 12+
- **Audio Hardware** (optional): Microphone for speech recognition; speakers/headphones for speech synthesis.

---

## 2. Automated Installation

### On Windows
Run the included launcher batch script:
```cmd
run.bat
```
The script will automatically detect Python, create `.venv`, install all packages from `requirements.txt`, initialize `.env`, and launch the desktop GUI.

### On Linux or macOS
Run the shell script:
```bash
chmod +x run.sh
./run.sh
```

---

## 3. Manual Step-by-Step Installation

### Step 1: Create Virtual Environment
```bash
python -m venv .venv
```

### Step 2: Activate the Virtual Environment
- **Windows (Command Prompt)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Linux/macOS**:
  ```bash
  source .venv/bin/activate
  ```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
pip install -e . --no-deps
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

---

## 4. Configuring AI Providers

Zero launches out of the box in **Demo Mode** without requiring any API keys. When you are ready to connect a cloud LLM, edit `.env`:

### OpenAI
```ini
AI_PROVIDER=openai
AI_API_KEY=sk-your-openai-api-key
AI_MODEL=gpt-4o-mini
```

### Google Gemini (OpenAI Compatibility Mode)
```ini
AI_PROVIDER=gemini
AI_API_KEY=your-gemini-api-key
AI_MODEL=gemini-1.5-flash
AI_API_BASE=https://generativelanguage.googleapis.com/v1beta/openai
```

### Local Ollama
```ini
AI_PROVIDER=ollama
AI_API_KEY=not-needed
AI_MODEL=llama3
AI_API_BASE=http://localhost:11434/v1
```

---

## 5. Launching Zero AI

### Mode 1: Full Desktop GUI + Local REST API (Default)
```bash
python run.py
```

### Mode 2: Interactive Terminal CLI
```bash
python run.py --cli
```

### Mode 3: Headless API Server
```bash
python run.py --api-only
```
Access the interactive OpenAPI Swagger documentation at:
```
http://127.0.0.1:8765/docs
```

---

## 6. Running Tests

Execute the 27 automated unit, integration, and GUI tests:
```bash
pytest -v
```

---

## 7. Troubleshooting

### Issue: "No module named 'PySide6'" or "No module named 'app'"
**Solution**: Ensure your virtual environment is active and the package is installed in editable mode:
```bash
.venv\Scripts\pip.exe install -e . --no-deps
```

### Issue: Microphone Access Error
**Solution**:
1. Check that a working microphone is connected and set as default recording device in Windows Sound settings.
2. Ensure desktop apps have microphone permissions enabled in Windows Privacy & Security settings.
3. You can still use push-to-talk or text input mode if a microphone is unavailable.

### Issue: TTS Engine Muted or Access Violation
**Solution**: Zero incorporates COM initialization isolation (`pythoncom.CoInitialize()`) on Windows. If your system lacks SAPI5 voices, audio will silently fall back to visual transcripts without crashing the GUI.
