# Safe GitHub Push Guide for Zero AI

This guide walks you step-by-step through safely initializing, reviewing, and pushing the Zero AI codebase to GitHub without exposing secrets, personal documents, database files, or unnecessary artifacts.

---

## 1. Prerequisites: Verify Git Installation

Open **PowerShell** and verify that Git is installed and available:

```powershell
git --version
```
*Expected Output:* `git version 2.40.0.windows.1` or higher. (Current system has `git version 2.54.0.windows.1`).

If Git is not installed, download the official 64-bit installer from [git-scm.com/download/win](https://git-scm.com/download/win).

---

## 2. Inspect the Current Repository State

Before running any Git commands, check if the project directory is already a Git repository:

```powershell
cd C:\D-drive\code\ZERO
git status
```

- **If output is `fatal: not a git repository`:**
  Initialize the repository now:
  ```powershell
  git init -b main
  ```
  *Explanation:* This creates the `.git` metadata directory and sets your default branch name to `main`.

- **If output displays existing branches or commits:**
  Inspect your commit history and remote settings first:
  ```powershell
  git log --oneline -n 5
  git remote -v
  ```
  *Safety Warning:* Do not run `git init` or re-initialize if an existing repository is already configured with history you wish to preserve.

---

## 3. Configure Your Git Identity Locally

Set your commit name and email address. Use your GitHub account email (or GitHub's private `no-reply` email):

```powershell
git config --local user.name "Your Name"
git config --local user.email "your_email@example.com"
```

Verify the configuration:
```powershell
git config --local --list
```

---

## 4. Verify Safe Git Exclusions (`.gitignore`)

Zero includes a pre-configured, comprehensive `.gitignore` designed to block secrets, databases, and heavy files.

Verify that sensitive items are properly ignored before staging anything:

```powershell
# 1. Test that .env is ignored:
git check-ignore .env
# Expected output: .env

# 2. Test that virtual environment is ignored:
git check-ignore .venv
# Expected output: .venv

# 3. Test that local databases are ignored:
git check-ignore data/zero.db
# Expected output: data/*.db

# 4. Test that personal Knowledge PDFs are ignored:
git check-ignore Knowledge/sample.pdf
# Expected output: Knowledge/*
```

If any of these commands return blank output instead of the file path, stop immediately and check [`.gitignore`](file:///c:/D-drive/code/ZERO/.gitignore).

---

## 5. Review Files Before Staging (Never Run `git add .` Blindly)

Inspect all untracked files:

```powershell
git status -u
```

Review the list carefully:
- **Application source code:** `app/`, `run.py`, `run.bat`, `run.sh` (Should be staged).
- **Configuration templates:** `.env.example`, `pyproject.toml`, `requirements.txt` (Should be staged).
- **Public documentation:** `README.md`, `GitHub/`, `docs/`, `CONTRIBUTING.md`, `SECURITY.md` (Should be staged).
- **Automated test suite:** `tests/`, `scripts/` (Should be staged).
- **Sanitized test fixtures:** `Knowledge/README.md`, `Knowledge/Zero_Evaluation_Fixture.txt`, `Knowledge/zero_architecture_overview.md` (Should be staged).

### Staging Reviewed Files Selectively:
Stage only the approved directories and files:

```powershell
git add app/
git add tests/
git add scripts/
git add docs/
git add GitHub/
git add run.py run.bat run.sh
git add requirements.txt pyproject.toml
git add .env.example .gitignore
git add README.md CONTRIBUTING.md SECURITY.md
git add data/.gitkeep logs/.gitkeep exports/.gitkeep reports/.gitkeep
git add Knowledge/.gitkeep Knowledge/README.md Knowledge/Zero_Evaluation_Fixture.txt Knowledge/zero_architecture_overview.md
```

Check the staging area:
```powershell
git status
```
*Verification:* Ensure **no** `.env`, `.db`, `.log`, or personal `.pdf` files appear under "Changes to be committed".

---

## 6. Pre-Commit Secret Scan

Run a quick local text search to verify that no actual credentials or raw API keys were staged:

```powershell
# Verify no real API keys are staged in git diff:
git diff --cached | Select-String -Pattern "sk-[a-zA-Z0-9]{20,}", "AI_API_KEY=[a-zA-Z0-9]{10,}"
```
*Expected Output:* Blank (no matches found).

If any secret match appears, unstage the file immediately using `git restore --staged <file>`.

---

## 7. Create a Clean Initial Commit

Once verified, commit the staged files with a clear, descriptive message:

```powershell
git commit -m "feat: initial commit of Zero AI desktop assistant with streaming voice, captions, and desktop automation"
```

Verify your commit:
```powershell
git log -n 1 --stat
```

---

## 8. Create a Private GitHub Repository

1. Open your browser and navigate to [github.com/new](https://github.com/new).
2. **Repository name:** e.g., `zero-ai` or `ZERO`.
3. **Visibility:** Select **Private** (Recommended).
   > [!IMPORTANT]
   > Keep the repository **Private** to ensure your desktop configuration and conversations remain confidential between you and your collaborator.
4. **Initialize repository with:** Leave all checkboxes **unchecked** (Do *not* add a README, `.gitignore`, or license on GitHub, since we have created them locally).
5. Click **Create repository**.
6. Copy the repository HTTPS URL (e.g., `https://github.com/<your-username>/zero-ai.git`).

---

## 9. Configure the Remote & Authenticate

Set the remote URL on your local repository:

```powershell
git remote add origin https://github.com/<your-username>/zero-ai.git
```

Verify the remote:
```powershell
git remote -v
```

### Authentication:
When pushing over HTTPS on Windows, Git uses **Git Credential Manager** (pre-installed with Git for Windows):
1. Run the push command:
   ```powershell
   git push -u origin main
   ```
2. A browser window or modal will appear prompting you to sign in with your GitHub account.
3. Complete sign-in in your browser. Git Credential Manager will securely store your authentication token locally in Windows Credential Manager.

---

## 10. Verify the Pushed Repository

1. Refresh your GitHub repository page in the browser.
2. Confirm that:
   - All source code in `app/`, `tests/`, `GitHub/`, and `docs/` is present.
   - `.env` is **NOT** present (`.env.example` should be visible instead).
   - `data/zero.db` is **NOT** present (`data/.gitkeep` should be visible).
   - Personal files in `Knowledge/` are **NOT** present (only `README.md` and test fixtures).
   - No large `.zip` or audio `.wav` files were pushed.

---

## 11. Troubleshooting Blocked or Rejected Pushes

### Problem: `remote rejected: push declined due to secret detected`
GitHub's Secret Scanning will block pushes if it detects an API key (e.g. from an OpenAI or Anthropic provider).
- **Remedy:** Inspect the rejected commit:
  ```powershell
  git log -p -n 1
  ```
  Locate the file containing the secret, replace it with a placeholder in `.env.example`, uncommit using `git reset --soft HEAD~1`, and recommit.

### Problem: `error: failed to push some refs (fetch first)`
This occurs if the remote repository already contains commits (e.g., if you created a README on GitHub).
- **Remedy:** Fetch and reconcile:
  ```powershell
  git pull origin main --rebase
  git push -u origin main
  ```
  *Never use `--force` unless you are certain no collaborator's work will be overwritten.*
