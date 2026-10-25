# Contributing to Zero AI

Welcome! Zero AI is a personal desktop assistant project built for collaboration between trusted friends and peers. This guide provides standards for contributing features, bug fixes, and documentation safely.

---

## 1. Core Principles

1. **Local-First Architecture:** Zero relies on local Ollama models (`llama3.2`, `qwen2.5-coder`). Do not introduce mandatory cloud subscriptions, remote analytics, or paid API requirements into core workflows.
2. **Strict Security Boundaries:** Never create tools that allow the AI to execute arbitrary shell commands, modify the Windows Registry, or delete user files.
3. **No Secrets in Commits:** Never commit `.env`, actual API keys, private documents, or downloaded model weights to Git.
4. **Verified Testing:** Every feature or fix must be accompanied by unit tests and verified before submitting a pull request.

---

## 2. Quick Workflow for Collaborators

1. **Clone the Repository:**
   ```powershell
   git clone <YOUR_PRIVATE_REPO_URL>
   cd ZERO
   ```
2. **Follow Setup Instructions:**
   Read and follow [`GitHub/SETUP_FROM_SCRATCH_WINDOWS.md`](file:///c:/D-drive/code/ZERO/GitHub/SETUP_FROM_SCRATCH_WINDOWS.md) to initialize your Python 3.12 virtual environment and local Ollama setup.
3. **Create a Topic Branch:**
   Never commit directly to `main`. Use descriptive branch names:
   ```powershell
   git checkout -b feature/voice-captions
   # or: git checkout -b fix/tts-recovery
   # or: git checkout -b docs/update-readme
   ```
4. **Run Tests Before Committing:**
   ```powershell
   .\.venv\Scripts\pytest.exe -v
   ```
5. **Stage and Review Only Intended Files:**
   ```powershell
   git status
   git diff
   git add app/specific_file.py tests/test_specific.py
   git commit -m "feat(voice): implement streaming caption buffer"
   ```
6. **Push to Your Branch & Open a PR:**
   ```powershell
   git push -u origin feature/voice-captions
   ```
   Open a Pull Request on GitHub and request a review from your collaborator.

For the full step-by-step collaboration guide, see [`GitHub/COLLABORATION_WORKFLOW.md`](file:///c:/D-drive/code/ZERO/GitHub/COLLABORATION_WORKFLOW.md).
