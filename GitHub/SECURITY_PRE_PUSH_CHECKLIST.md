# Security Pre-Push Checklist for Zero AI

Before running `git push` to upload code to GitHub, complete this mandatory security audit. This checklist ensures that no credentials, private notes, local databases, or runtime artifacts are inadvertently published.

---

## Pre-Push Verification Matrix

| Check Item | Description | Verification Command (PowerShell) | Expected Safe Result | Pass? |
| :--- | :--- | :--- | :--- | :---: |
| **1. `.env` File** | Secret environment variables file | `git status --porcelain .env` | Empty output (must **not** be tracked or staged) | [ ] |
| **2. `.env.example`** | Configuration template | `Select-String -Path .env.example -Pattern "aak_", "sk-", "ghp_"` | Empty output (only blank placeholders permitted) | [ ] |
| **3. API Credentials** | Raw API keys in source or tests | `git diff --cached \| Select-String -Pattern "sk-[a-zA-Z0-9]{20,}"` | Empty output (no live keys staged) | [ ] |
| **4. SQLite Database** | Local user history and embeddings | `git status --porcelain data/` | Only `data/.gitkeep` allowed | [ ] |
| **5. Personal Documents**| Private PDFs, docx, notes | `git status --porcelain Knowledge/` | Only `README.md`, `.gitkeep`, and sample fixtures | [ ] |
| **6. Runtime Logs** | Debug logs with personal state | `git status --porcelain logs/` | Only `logs/.gitkeep` allowed | [ ] |
| **7. PDF Exports** | Generated reports in `exports/` | `git status --porcelain exports/` | Only `exports/.gitkeep` allowed | [ ] |
| **8. Virtual Environment**| `.venv/` or Python packages | `git status --porcelain .venv/` | Empty output (must be ignored) | [ ] |
| **9. Python Caches** | `__pycache__` and `.pyc` files | `git status --porcelain \| Select-String "__pycache__"` | Empty output | [ ] |
| **10. Model Weights** | Large `.gguf`, `.bin`, `.safetensors`| `git status --porcelain \| Select-String "\.gguf\|\.bin\|\.safetensors"` | Empty output | [ ] |
| **11. Remote URL Auth** | Credentials embedded in git remote | `git remote -v` | Must **not** contain usernames/passwords in URL | [ ] |
| **12. Git History Audit**| Credentials in previous commits | `git log -p -S "AI_API_KEY=" -n 5` | No raw keys in commit patches | [ ] |

---

## Detailed Step-by-Step Security Checks

### 1. Environment & Secret Audit
Run this command from the repository root:
```powershell
git status --ignored
```
Verify that `.env` appears under **Ignored files**, and does **not** appear under "Changes to be committed" or "Untracked files".

Verify that `.env.example` contains only empty placeholder strings:
```powershell
Get-Content .env.example | Select-String "AI_API_KEY"
# Must display: AI_API_KEY=
```

### 2. Working Tree Credential Scan
Scan all staged files for common token patterns:
```powershell
git diff --cached | Select-String -Pattern "sk-[a-zA-Z0-9]{20,}", "ghp_[a-zA-Z0-9]{20,}", "BEGIN PRIVATE KEY", "password\s*=\s*['\"][^'\"]+"
```
If any real secret matches are returned:
1. Immediately unstage the file: `git restore --staged <file_path>`
2. Replace the secret with an environment variable lookup `os.getenv("VARIABLE_NAME")`.
3. If a live credential was previously stored in `.env`, treat it as potentially exposed and rotate it at the provider's console.

### 3. Knowledge Base & Personal Data Privacy
Zero's `Knowledge/` folder is designed to store personal research, documentation, and books.
Run:
```powershell
git status Knowledge/
```
Ensure that no personal `.pdf`, `.docx`, `.xlsx`, or `.txt` files are staged.
Only the following files should ever be committed to `Knowledge/`:
- `Knowledge/.gitkeep`
- `Knowledge/README.md`
- `Knowledge/Zero_Evaluation_Fixture.txt` (Sanitized test fixture)
- `Knowledge/zero_architecture_overview.md` (Sanitized architecture spec)

### 4. Git Remote URL Security Check
Ensure your Git remote URL does not contain an embedded token:
```powershell
git remote -v
```
- **Safe:** `https://github.com/username/repo.git`
- **UNSAFE:** `https://ghp_secrettoken12345@github.com/username/repo.git`

If an embedded token exists, remove it immediately:
```powershell
git remote set-url origin https://github.com/username/repo.git
```
Git Credential Manager will handle authentication securely without placing tokens in the URL.

---

## 5. What To Do If A Secret Was Already Committed Locally

If a secret was committed locally but **not yet pushed** to GitHub:
```powershell
# Undo the last commit while keeping your local code changes in working directory:
git reset --soft HEAD~1

# Unstage the secret file:
git restore --staged .env

# Verify working tree is clean of staged secrets:
git status
```

> [!CAUTION]
> If a secret was already pushed to a remote GitHub repository in a prior commit, rewriting Git history (`git filter-branch` or BFG Repo-Cleaner) will alter commit hashes. More importantly, automated bots scan public commits within seconds of pushing. **You MUST rotate or revoke the leaked credential immediately.**
