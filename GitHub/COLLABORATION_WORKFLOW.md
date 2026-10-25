# Zero AI — Collaboration & Peer Workflow Guide

This guide describes how to collaborate safely with a friend on Zero AI. It covers repository invitations, local setup, branching standards, pull requests, merge conflict resolution, and credential isolation.

---

## 1. Golden Rules of Collaboration

1. **Independent Authentication:** Never share passwords, personal access tokens (PATs), or SSH keys. Each collaborator signs into GitHub using their own GitHub account.
2. **Independent Local Environments:** Each collaborator runs their own local Python virtual environment, local SQLite database, and local Ollama instance with their own downloaded models.
3. **No Direct Commits to `main`:** All modifications must be developed on a dedicated feature or bugfix branch and reviewed via a GitHub Pull Request.
4. **Never Force-Push (`--force`):** Force-pushing overwrites Git history on remote branches, which can erase your collaborator's work.
5. **No Secrets in Git:** Never commit `.env` or personal files in `Knowledge/`.

---

## 2. Inviting a Collaborator on GitHub

As the repository owner:
1. Open your repository on GitHub: `https://github.com/<your-username>/zero-ai`.
2. Go to **Settings** → **Collaborators** (under Access).
3. Click **Add people**.
4. Enter your friend's GitHub username or email address.
5. Select their account and click **Add <username> to this repository**.
6. GitHub will send an email invitation. Your friend must click **Accept invitation** before they can push.

---

## 3. Recommended Branch Protection on GitHub

To prevent accidental overwrites on `main`:
1. On GitHub, navigate to **Settings** → **Branches**.
2. Click **Add branch protection rule** (or edit rule for `main`).
3. Set **Branch name pattern** to `main`.
4. Check:
   - `[X] Require a pull request before merging`
   - `[X] Require approvals` (Set to 1)
   - `[X] Do not allow force pushes`
5. Click **Create** or **Save changes**.

---

## 4. Daily Developer Workflow

```
   [main] (Production-ready, tested code)
     │
     ├── git checkout -b feature/streaming-captions
     │     │ (Make changes, run tests, commit)
     │     ▼
     │   [git push -u origin feature/streaming-captions]
     │     │ (Open Pull Request on GitHub)
     │     ▼
     │   [Peer Review & Approval]
     │     │ (Merge Pull Request into main)
     ▼     ▼
   [main] (Updated with new feature)
```

### Step 1: Sync Your Local `main` Branch
Before starting new work, pull the latest changes from GitHub:
```powershell
git checkout main
git pull origin main
```

### Step 2: Create a Feature or Fix Branch
Use clear, descriptive branch names:
```powershell
# For new capabilities:
git checkout -b feature/voice-captions

# For bug fixes:
git checkout -b fix/tts-com-threading

# For documentation updates:
git checkout -b docs/collaboration-guide
```

### Step 3: Make Changes & Test Locally
Implement your feature or fix. Then run the test suite to ensure zero regressions:
```powershell
.\.venv\Scripts\pytest.exe -v
```

### Step 4: Review Changes Before Staging
Inspect exactly what files were modified:
```powershell
git status
git diff
```

Stage only the files you intentionally modified:
```powershell
git add app/voice/stream_listener.py tests/test_voice_interruption_and_captions.py
git commit -m "feat(voice): implement streaming VAD pause continuation"
```

### Step 5: Push the Feature Branch to GitHub
```powershell
git push -u origin feature/voice-captions
```

### Step 6: Open a Pull Request (PR)
1. Go to your repository on GitHub.
2. You will see a banner: **"feature/voice-captions had recent pushes. Compare & pull request"**.
3. Click **Compare & pull request**.
4. Title the PR clearly (e.g. `feat: Add pause continuation window to streaming voice listener`).
5. Describe:
   - What problem was solved.
   - What files were modified.
   - What tests were run and passed.
6. Click **Create pull request**.
7. Assign your friend as a **Reviewer**.

### Step 7: Review and Merge
- The reviewer inspects the code diff in the **Files changed** tab.
- If everything looks good, the reviewer clicks **Review changes** → **Approve**.
- The PR author clicks **Merge pull request** → **Confirm merge**.
- Delete the feature branch on GitHub after merging.

---

## 5. Resolving Merge Conflicts

If you and your friend edited the same lines in the same file:

1. Switch to your feature branch and attempt to merge the latest `main`:
   ```powershell
   git checkout main
   git pull origin main
   git checkout feature/your-branch
   git merge main
   ```
2. Git will flag conflicting files:
   `CONFLICT (content): Merge conflict in app/services/desktop_control.py`
3. Open the file in your code editor (e.g., VS Code). You will see conflict markers:
   ```python
   <<<<<<< HEAD
   # Your changes
   =======
   # Your friend's changes from main
   >>>>>>> main
   ```
4. Decide which lines to keep or combine them, then remove the `<<<<<<<`, `=======`, and `>>>>>>>` markers.
5. Re-run tests:
   ```powershell
   .\.venv\Scripts\pytest.exe -v
   ```
6. Stage the resolved files and finish the merge commit:
   ```powershell
   git add app/services/desktop_control.py
   git commit -m "merge: resolve conflict in desktop_control with main"
   git push origin feature/your-branch
   ```
7. Your GitHub Pull Request will automatically update and indicate that conflicts are resolved!
