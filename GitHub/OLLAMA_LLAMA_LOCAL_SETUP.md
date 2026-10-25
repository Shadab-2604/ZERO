# Ollama & Local Llama Setup Guide for Zero AI

Zero AI is built around a 100% local AI architecture powered by **Ollama**. This ensures zero API costs, complete privacy, zero telemetry leakage, and offline availability.

Each collaborator downloads and runs their own local models on their machine. **Model weights are never committed to Git.**

---

## 1. Official Documentation & References

- **Ollama Windows Download:** [ollama.com/download/windows](https://ollama.com/download/windows)
- **Official Documentation:** [docs.ollama.com](https://docs.ollama.com/)
- **Ollama Local REST API:** [docs.ollama.com/api/introduction.md](https://docs.ollama.com/api/introduction.md)
- **Llama 3.2 Model Library:** [ollama.com/library/llama3.2](https://ollama.com/library/llama3.2)
- **Qwen 2.5 Coder Model Library:** [ollama.com/library/qwen2.5-coder](https://ollama.com/library/qwen2.5-coder)

---

## 2. Installing or Updating Ollama on Windows

1. Download the Windows installer (`OllamaSetup.exe`) from [ollama.com/download/windows](https://ollama.com/download/windows).
2. Run the installer. It will install to `C:\Users\<username>\AppData\Local\Programs\Ollama` and create a startup task in your Windows System Tray.
3. Open a new PowerShell terminal and verify:
   ```powershell
   ollama --version
   ```
   *Expected Output:* `ollama version is 0.3.x` (or newer). (On the primary test system: `0.34.2`).

### Checking If the Ollama Service Is Running:
Ollama runs an HTTP server on `http://127.0.0.1:11434`. Check its status in PowerShell:
```powershell
curl.exe -s http://127.0.0.1:11434/
```
*Expected Output:* `Ollama is running`

If it is not running, launch it from the Windows Start Menu or run:
```powershell
ollama serve
```

---

## 3. Pulling the Required Models

Zero AI uses two primary local open-weight models:
1. **`llama3.2` (3B parameters, ~2.0 GB):** Default model for natural conversation, daily briefings, intent understanding, and general reasoning.
2. **`qwen2.5-coder:7b` (7B parameters, ~4.7 GB) or `qwen2.5-coder:3b` (~1.9 GB):** Specialist coding model for code generation, software architecture, and debugging.

### Pulling the Models:
Run these commands in PowerShell:

```powershell
# 1. Pull Llama 3.2 (Conversational Core):
ollama pull llama3.2

# 2. Pull Qwen 2.5 Coder (Coding Specialist):
ollama pull qwen2.5-coder:7b
```
*(If your system has less than 16 GB of RAM, pull `qwen2.5-coder:3b` instead for lighter memory footprint).*

### Inspecting Installed Models:
Verify that the models are installed locally:
```powershell
ollama list
```
*Sample Output:*
```text
NAME                ID              SIZE      MODIFIED
llama3.2:latest     a80c4f17acd5    2.0 GB    5 hours ago
qwen2.5-coder:7b    dae161e27b0e    4.7 GB    5 hours ago
```

---

## 4. Interactive Testing & API Validation

### Interactive Model Test:
Test direct model execution in your console:
```powershell
ollama run llama3.2 "Explain the purpose of an operating system in two concise sentences."
```
Verify that the model responds quickly and coherently. (Type `/bye` to exit interactive mode).

### Testing the REST API Endpoint:
Zero connects to Ollama via its local HTTP API (`http://127.0.0.1:11434/api/generate`):
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body (ConvertTo-Json @{
    model = "llama3.2"
    prompt = "Respond with 'LOCAL_OLLAMA_VERIFIED' and nothing else."
    stream = $false
}) -ContentType "application/json" | Select-Object -ExpandProperty response
```
*Expected Output:* `LOCAL_OLLAMA_VERIFIED`

---

## 5. GPU Acceleration & Resource Monitoring

Ollama automatically detects NVIDIA CUDA, AMD ROCm, or Intel GPUs:
- When a compatible GPU is detected, Ollama offloads layers to GPU VRAM for 60–120+ tokens/second inference.
- If no GPU is available, Ollama gracefully falls back to CPU multi-threading.

### How to Check GPU Offloading:
While running an inference query, open a second PowerShell window and check:
```powershell
ollama ps
```
*Sample Output:*
```text
NAME               ID              SIZE      PROCESSOR    UNTIL
llama3.2:latest    a80c4f17acd5    2.8 GB    100% GPU     4m59s
```
If `PROCESSOR` shows `100% GPU`, full hardware acceleration is active.

On NVIDIA systems, you can also run:
```powershell
nvidia-smi
```
to inspect active VRAM consumption.

---

## 6. Configuring Zero AI to Use the Local Models

Zero reads its configuration from [`.env`](file:///c:/D-drive/code/ZERO/.env). Confirm that your `.env` contains:

```ini
# Core AI Provider
ZERO_MODE=local_only
AI_PROVIDER=ollama
AI_API_BASE=http://127.0.0.1:11434/v1
AI_MODEL=llama3.2

# Specialized Local Models
LOCAL_CHAT_MODEL=llama3.2
LOCAL_CODE_MODEL=qwen2.5-coder:7b

# Privacy & Isolation
EXTERNAL_AI_ENABLED=false
WEB_SEARCH_ENABLED=false
```

Zero's AI abstraction ([`app/ai/ollama_client.py`](file:///c:/D-drive/code/ZERO/app/ai/ollama_client.py)) will automatically route conversational prompts to `llama3.2` and code generation requests to `qwen2.5-coder`.

---

## 7. Troubleshooting Common Ollama Issues

### 1. Connection Refused (`127.0.0.1:11434`)
- **Cause:** Ollama service is not running.
- **Fix:** Start Ollama from your Windows Start Menu, or run `ollama serve` in a terminal. Check your Windows System Tray to ensure the Ollama llama icon is active.

### 2. Model Not Found (`model 'llama3.2' not found, try pulling it first`)
- **Cause:** Model was not pulled or model tag is mistyped.
- **Fix:** Run `ollama list` to check installed tags. Re-run `ollama pull llama3.2`.

### 3. Out of Memory / System Sluggishness
- **Cause:** Loading 7B or 14B models on systems with insufficient RAM or VRAM.
- **Fix:** In `.env`, switch `LOCAL_CODE_MODEL` to `qwen2.5-coder:3b` or `llama3.2:latest`. 3B models run comfortably on systems with only 8–16 GB RAM.

### 4. Generation Timeouts
- **Cause:** CPU-only inference on older hardware under high thread load.
- **Fix:** In `app/ai/ollama_client.py`, the default timeout is set to 30.0 seconds. For larger prompts on CPU, you can increase `timeout=60.0`.
