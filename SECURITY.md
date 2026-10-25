# Security Policy & Guidelines for Zero AI

## 1. Overview
Zero AI is designed as a local-first, privacy-respecting desktop assistant. It operates using local models (Ollama), local storage (SQLite), and local hardware interfaces. This security policy outlines how credentials, private documents, system permissions, and vulnerabilities are managed.

---

## 2. Strict Security & Permission Boundary

Zero adheres to an explicit least-privilege architecture:
- **No Arbitrary Shell Execution:** Zero's AI layer has **no** exposed tools to run arbitrary command-line strings, bash scripts, CMD commands, or PowerShell snippets.
- **No Arbitrary File Write or Deletion:** Zero cannot create, overwrite, modify, move, or delete arbitrary user files or folders.
- **No Registry Modifications:** Zero has no access to Windows Registry writing or system configuration manipulation.
- **Safe Window Controls:** Zero can only focus, minimize, restore, maximize, and gracefully request window close (`WM_CLOSE`) for running applications.
- **Detection of Unsaved Work:** On window close, Zero detects if an application presents an unsaved-work prompt and halts immediately; it **never** automatically clicks *Save*, *Discard*, or *Delete*.
- **Local Application Scope:** Zero runs with standard Windows user permissions and **never** requests or requires Administrator privileges.

> [!WARNING]
> While Zero enforces a strict Python-level allowlist on tools, the Python runtime executes under your standard Windows user account. Never run Zero as an Administrator.

---

## 3. Secret & Credential Protection

### What Must NEVER Be Committed to Version Control:
- `.env` files containing any private keys, local tokens, or user configuration.
- Actual cloud API keys (e.g., OpenAI, Gemini, Anthropic).
- Personal documents, financial statements, or private notes located in `Knowledge/`.
- Local database files (`data/zero.db`), database backups, or WAL journals.
- Generated PDF exports (`exports/*.pdf`) or diagnostic telemetry with sensitive system details.
- Downloaded large language model weights (`*.gguf`, `*.bin`, `*.safetensors`).

### Safe Template Usage
Always commit changes using `.env.example` with sanitized placeholder values:
```bash
# Correct: Placeholder values in .env.example
AI_API_KEY=
DATABASE_URL=sqlite:///./data/zero.db
LOCAL_CHAT_MODEL=llama3.2
```

---

## 4. Reporting a Security Vulnerability

If you discover a security vulnerability or credential leak in this repository:
1. **Do not create a public GitHub issue.**
2. Send an email to the repository owner or message them privately.
3. If an API key or secret was accidentally committed, immediately rotate and revoke the credential at its provider dashboard.
4. Follow the guidance in [`GitHub/SECURITY_PRE_PUSH_CHECKLIST.md`](file:///c:/D-drive/code/ZERO/GitHub/SECURITY_PRE_PUSH_CHECKLIST.md) to inspect and clean the repository.
