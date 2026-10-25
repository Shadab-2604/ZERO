#!/usr/bin/env bash
set -e

echo "==================================================="
echo "            ZERO AI - JARVIS DESKTOP CORE"
echo "==================================================="

# 1. Check for Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found. Please install Python 3.11 or 3.12."
    exit 1
fi

# 2. Virtual Environment
if [ ! -f ".venv/bin/python" ]; then
    echo "[SETUP] Creating Python virtual environment in .venv..."
    python3 -m venv .venv
fi

# 3. Seed .env
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "[SETUP] Initializing .env from .env.example..."
    cp .env.example .env
fi

# 4. Install / Verify Dependencies
echo "[SETUP] Verifying dependencies..."
.venv/bin/pip install -r requirements.txt --quiet

# 5. Launch Zero AI
echo "[LAUNCH] Starting Zero AI Desktop Assistant..."
.venv/bin/python run.py "$@"
