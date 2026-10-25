# Zero AI — Comprehensive Troubleshooting Guide

This guide contains diagnostic steps and solutions for common runtime, audio, AI, desktop automation, and Git issues on Windows.

---

## 1. Audio & Voice Subsystem Issues

### Problem: Zero speaks initial greeting, then subsequent turns produce text but no sound
- **Root Cause:** SAPI5 engine COM uninitialization or voice worker queue deadlock.
- **Solution:**
  1. Verify the voice worker thread is active:
     ```powershell
     .\.venv\Scripts\python.exe -c "from app.voice.manager import VoiceManager; vm = VoiceManager(); vm.speak('Voice test'); vm.wait_until_done(); print('Audio operational')"
     ```
  2. If an error `CoInitialize has not been called` appears, ensure `pythoncom` is installed (`pip install pywin32`) and that speech requests pass through `VoiceManager.speak()` rather than direct engine calls.

### Problem: `PyAudio: No Default Input Device Available` or `Device Unavailable`
- **Root Cause:** Windows microphone privacy settings are blocking Python, or headset is disconnected.
- **Solution:**
  1. Open Windows Settings → **Privacy & Security** → **Microphone**.
  2. Ensure **Microphone access** is turned **On**.
  3. Ensure **Let desktop apps access your microphone** is turned **On**.
  4. Check active audio input devices:
     ```powershell
     .\.venv\Scripts\python.exe -c "import pyaudio; p = pyaudio.PyAudio(); print([(i, p.get_device_info_by_host_api_device_index(0, i)['name']) for i in range(p.get_device_count())])"
     ```

### Problem: Installing PyAudio Fails with `Microsoft Visual C++ 14.0 is required`
- **Root Cause:** Attempting to build PyAudio from source without pre-compiled wheels.
- **Solution:**
  Ensure you are using Python 3.11 or 3.12 (64-bit). Pre-compiled wheels for PyAudio 0.2.14 exist on PyPI for Windows 64-bit:
  ```powershell
  pip install --only-binary :all: PyAudio
  ```

---

## 2. Local AI & Ollama Issues

### Problem: `Cannot connect to Ollama at http://127.0.0.1:11434`
- **Root Cause:** Ollama service is stopped or listening on a non-default interface.
- **Solution:**
  1. Check if the Ollama service process is running:
     ```powershell
     Get-Process -Name "ollama*" -ErrorAction SilentlyContinue
     ```
  2. If not running, start Ollama:
     ```powershell
     Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
     ```
  3. Test connectivity:
     ```powershell
     curl.exe -s http://127.0.0.1:11434/
     # Must return: "Ollama is running"
     ```

### Problem: Empty or Extremely Slow AI Responses
- **Root Cause:** GPU VRAM exhaustion forcing layers to CPU swap, or running models too large for system RAM.
- **Solution:**
  1. Check active loaded models and memory usage:
     ```powershell
     ollama ps
     ```
  2. If using `qwen2.5-coder:7b` on a laptop with 8 GB RAM, switch `.env` to `LOCAL_CODE_MODEL=qwen2.5-coder:3b` or `llama3.2:latest`.
  3. To unload idle models from VRAM:
     ```powershell
     ollama stop llama3.2
     ollama stop qwen2.5-coder:7b
     ```

---

## 3. Windows Desktop Automation & System Awareness Issues

### Problem: Zero says *"Could not find an open window matching 'Chrome'"*
- **Root Cause:** Window Station desktop isolation in subshells, or the application is minimized to the system tray without a top-level window.
- **Solution:**
  1. Verify window enumeration from the interactive desktop:
     ```powershell
     .\.venv\Scripts\python.exe -c "from app.services.desktop_control import get_desktop_service; print(get_desktop_service().list_windows())"
     ```
  2. Ensure the target application has a visible window on the active desktop.
  3. If the app is closed, say *"Zero, open Chrome"* rather than *"Zero, switch to Chrome"*.

### Problem: Windows Denies Focus / Foreground Activation
- **Root Cause:** Windows Foreground Lock (`LockSetForegroundWindow`). Windows prevents background applications from stealing foreground focus if another window has user input lock.
- **Solution:**
  Zero's `restore_window()` un-minimizes the window via `ShowWindow(SW_RESTORE)` regardless of foreground lock. You can also click the taskbar or use the Push-To-Talk button in the Live Caption HUD.

### Problem: Application Displays Unsaved Changes Dialog on Close
- **Behavior:** This is an intentional security design!
- **Explanation:** Zero detects modal unsaved-work prompts on `WM_CLOSE` and will **never** automatically click *Save* or *Discard* on your behalf.
- **Solution:** Switch to the application window and save or discard your document manually.

---

## 4. PDF Generation & Playwright Issues

### Problem: `Executable doesn't exist at ...\ms-playwright\chromium-...`
- **Root Cause:** Playwright browser binaries were not installed after package installation.
- **Solution:**
  Run the Playwright browser installer:
  ```powershell
  .\.venv\Scripts\playwright.exe install chromium
  ```

---

## 5. Git & GitHub Authentication Issues

### Problem: `git push` fails with `Permission to user/repo denied to other_user`
- **Root Cause:** Windows Credential Manager has cached an older GitHub account credential.
- **Solution:**
  1. Open Windows Start Menu → search **Credential Manager**.
  2. Select **Windows Credentials**.
  3. Under **Generic Credentials**, find `git:https://github.com`.
  4. Click **Remove**.
  5. Re-run `git push -u origin main`. Git Credential Manager will prompt for a fresh browser login.

### Problem: `LF will be replaced by CRLF` warnings in Git
- **Explanation:** Normal cross-platform line ending translation on Windows.
- **Solution:**
  Configure Git to handle line endings automatically:
  ```powershell
  git config --global core.autocrlf true
  ```
