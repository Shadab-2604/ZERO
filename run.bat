@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo             ZERO AI - JARVIS DESKTOP CORE
echo ===================================================

:: 1. Check for Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found in PATH. Please install Python 3.11 or 3.12.
    pause
    exit /b 1
)

:: 2. Check / Create Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [SETUP] Creating Python virtual environment in .venv...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Seed .env from .env.example if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [SETUP] Initializing .env from .env.example...
        copy .env.example .env >nul
    )
)

:: 4. Install / Verify Dependencies
echo [SETUP] Verifying dependencies...
.venv\Scripts\pip.exe install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Dependency installation returned an alert. Checking runtime...
)

:: 5. Launch Zero AI
echo [LAUNCH] Starting Zero AI Desktop Assistant...
.venv\Scripts\python.exe run.py %*
if %ERRORLEVEL% neq 0 (
    echo [NOTICE] Zero exited with code %ERRORLEVEL%.
)

endlocal
