# Setup Zero AI from Scratch on Windows 11 / 10

This guide is written for a developer or collaborator setting up Zero AI on a fresh Windows workstation. Follow these instructions in order.

---

## 1. System Requirements & Hardware Considerations

- **Operating System:** Windows 11 (64-bit) or Windows 10 (Build 19045+).
- **Processor:** Intel Core i5/i7/i9 (10th gen+) or AMD Ryzen 5/7/9 (6+ cores).
- **RAM:** Minimum 16 GB (24 GB+ recommended for running 7B models comfortably).
- **Graphics Card (Optional but Recommended):** NVIDIA RTX GPU (4 GB+ VRAM) with CUDA support for accelerated local AI generation. *(Zero also runs on CPU using Ollama's automatic CPU fallback).*
- **Disk Space:**
  - Codebase & Python Virtual Environment: ~3 GB.
  - Ollama Application & Llama 3.2 model: ~4.5 GB.
  - Recommended free SSD space: **15 GB+**.

---

## 2. Step 1: Install Git for Windows

1. Download Git for Windows from the official portal: [git-scm.com/download/win](https://git-scm.com/download/win).
2. Run the installer with default settings (ensure **Git Credential Manager** is checked).
3. Open a new **PowerShell** window and verify:
   ```powershell
   git --version
   ```
   *Expected Output:* `git version 2.40.0.windows.1` or higher.

---

## 3. Step 2: Install Python 3.12 (64-bit)

Zero AI is validated against **Python 3.12** (and 3.11).

> [!WARNING]
> Do **not** install Python 3.13 yet. Python 3.13 removes legacy standard library audio modules (`aifc`, `audioop`) that are required by `SpeechRecognition`.

1. Download Python 3.12 (e.g. 3.12.7 or 3.12.10) 64-bit installer from [python.org/downloads/windows](https://www.python.org/downloads/windows/).
2. **Important:** On the first installer screen, check the box:
   `[X] Add python.exe to PATH`
3. Click **Install Now**.
4. Open a new PowerShell window and verify:
   ```powershell
   python --version
   ```
   *Expected Output:* `Python 3.12.x`

---

## 4. Step 3: Clone the Zero Repository

Clone your repository to your desired code directory (e.g., `C:\code` or `D:\code`):

```powershell
mkdir -p C:\code
cd C:\code
git clone https://github.com/<your-username>/zero-ai.git ZERO
cd ZERO
```

---

## 5. Step 4: Create and Activate the Virtual Environment

Create an isolated virtual environment (`.venv`):

```powershell
python -m venv .venv
```

Activate the virtual environment in PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

> [!NOTE]
> If PowerShell displays an execution policy restriction (`running scripts is disabled on this system`), run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then re-run `.\.venv\Scripts\Activate.ps1`.

---

## 6. Step 5: Install Project Dependencies

Upgrade `pip` and install all required packages:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install Playwright browser binaries (for executive HTML-to-PDF export):
```powershell
playwright install chromium
```

Verify package installation:
```powershell
python -c "import PySide6, win32gui, psutil, pyttsx3, speech_recognition; print('Core dependencies imported successfully.')"
```

---

## 7. Step 6: Configure Environment (`.env`)

Copy the configuration template:

```powershell
Copy-Item .env.example .env
```

Open `.env` in your text editor (e.g. VS Code or Notepad):
```powershell
notepad .env
```

Verify the default local settings:
```ini
APP_NAME=Zero
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8765
LOG_LEVEL=INFO

# Local AI Configuration (Ollama)
ZERO_MODE=local_only
AI_PROVIDER=ollama
AI_API_KEY=
AI_MODEL=llama3.2
AI_API_BASE=http://127.0.0.1:11434/v1
LOCAL_CHAT_MODEL=llama3.2
LOCAL_CODE_MODEL=qwen2.5-coder:7b
EXTERNAL_AI_ENABLED=false
WEB_SEARCH_ENABLED=false

# Persistence & Database
DATABASE_URL=sqlite:///./data/zero.db
TIMEZONE=Asia/Kolkata
```
Save and close the file. No cloud API keys are needed!

---

## 8. Step 7: Install and Start Ollama

1. Download Ollama for Windows from [ollama.com/download/windows](https://ollama.com/download/windows).
2. Run `OllamaSetup.exe`. Once installed, Ollama starts automatically in your Windows system tray.
3. Open PowerShell and verify:
   ```powershell
   ollama --version
   ```
   *Expected Output:* `ollama version is 0.3.x` (or newer).

4. Pull the local chat model:
   ```powershell
   ollama pull llama3.2
   ```

5. (Optional) Pull the coding specialist model:
   ```powershell
   ollama pull qwen2.5-coder:7b
   ```

6. Test local inference:
   ```powershell
   ollama run llama3.2 "Introduce yourself in one sentence."
   ```

For detailed Ollama guidance, GPU allocation, and performance tuning, see [`GitHub/OLLAMA_LLAMA_LOCAL_SETUP.md`](file:///c:/D-drive/code/ZERO/GitHub/OLLAMA_LLAMA_LOCAL_SETUP.md).

---

## 9. Step 8: Run the Automated Test Suite

Before launching Zero, run the automated test suite to ensure all subsystems are functioning:

```powershell
.\.venv\Scripts\pytest.exe -v
```
*Expected Output:* All tests pass (`PASSED`).

---

## 10. Step 9: Launch Zero AI

You have three launch options:

### Option A: Interactive Streaming Voice with Live Captions HUD (Recommended)
```powershell
.\.venv\Scripts\python.exe run.py --voice
```
- A sleek, floating Live Caption HUD window appears on your desktop.
- State badge will indicate `LISTENING`.
- Speak into your microphone: *"Zero, show my system status"* or *"Zero, open Notepad"*.
- You can interrupt Zero at any time while it is speaking!

### Option B: Full PySide6 Desktop GUI (Chat, Telemetry & Knowledge Explorer)
```powershell
.\.venv\Scripts\python.exe run.py
```
- Launches the main futuristic JARVIS desktop window with reactive vector AI orb, sidebar navigation, conversation transcript, and system health status.

### Option C: Automated Launcher Script
```cmd
run.bat
```
*(Automatically creates `.venv`, verifies dependencies, and starts Zero).*

---

## 11. Maintenance, Backups & Uninstallation

### Updating the Project
To pull new updates from your collaborator:
```powershell
git checkout main
git pull origin main
pip install -r requirements.txt
```

### Recreating the Virtual Environment Safely
If your Python environment ever becomes corrupted:
```powershell
deactivate
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### Backing Up User Data
Before performing system maintenance, back up your local data:
- `data/zero.db` (Conversation history, activity logs, memories).
- `Knowledge/` (Your personal documents and notes).

### Clean Uninstallation
To completely remove Zero:
1. Delete the `ZERO` directory.
2. (Optional) Uninstall Ollama from Windows Settings → Installed Apps.
3. (Optional) Delete Ollama model weights from `C:\Users\<username>\.ollama`.
