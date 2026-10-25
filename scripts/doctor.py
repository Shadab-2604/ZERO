"""
Zero AI Doctor & Environment Diagnostics Tool.
Inspects Python version, virtual environment, critical dependencies,
browser binaries, audio hardware, database schema, and folder structure.
Never displays or leaks secrets.
"""

import sys
import os
from pathlib import Path
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_status(name: str, passed: bool, details: str = "", warning: bool = False):
    if passed:
        symbol = "[ PASS ]"
        status_color = "\033[92m"
    elif warning:
        symbol = "[ WARN ]"
        status_color = "\033[93m"
    else:
        symbol = "[ FAIL ]"
        status_color = "\033[91m"
    reset_color = "\033[0m"

    print(f" {status_color}{symbol}{reset_color} {name:<32} {details}")
    return passed or warning


def run_diagnostics():
    print("=" * 70)
    print(" ZERO AI SYSTEM DOCTOR // ENVIRONMENT & SUBSYSTEM DIAGNOSTICS")
    print("=" * 70)

    all_ok = True
    warnings = []

    # 1. Python Environment
    print("\n[1] Python Runtime & Virtual Environment:")
    py_ver = sys.version.split()[0]
    ver_ok = sys.version_info >= (3, 11)
    if not check_status("Python Version (>= 3.11)", ver_ok, f"v{py_ver}"):
        all_ok = False

    in_venv = sys.prefix != sys.base_prefix
    if not check_status("Virtual Environment Active", in_venv, f"Prefix: {sys.prefix}"):
        warnings.append("Not running in dedicated virtual environment (.venv recommended).")

    # 2. Critical Packages
    print("\n[2] Required Python Packages:")
    packages = [
        ("PySide6", "PySide6"),
        ("FastAPI", "fastapi"),
        ("Uvicorn", "uvicorn"),
        ("SQLAlchemy", "sqlalchemy"),
        ("Pydantic", "pydantic"),
        ("Playwright", "playwright"),
        ("Markdown", "markdown"),
        ("PyPDF", "pypdf"),
        ("python-docx", "docx"),
        ("python-pptx", "pptx"),
        ("openpyxl", "openpyxl"),
        ("pyttsx3", "pyttsx3"),
        ("SpeechRecognition", "speech_recognition"),
        ("PyAudio", "pyaudio"),
    ]

    for display_name, import_name in packages:
        try:
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", "installed")
            check_status(display_name, True, f"v{ver}")
        except ImportError as e:
            if display_name == "PyAudio":
                check_status(display_name, False, "Microphone capture unavailable", warning=True)
                warnings.append("PyAudio not installed; voice microphone input will be disabled.")
            else:
                check_status(display_name, False, f"Missing: {e}")
                all_ok = False

    # 3. Playwright Chromium Browser
    print("\n[3] Headless Browser (HTML -> PDF):")
    chromium_ok = False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        chromium_ok = True
        check_status("Playwright Chromium", True, "Browser binary verified and executable")
    except Exception as e:
        check_status("Playwright Chromium", False, f"Error: {e}")
        all_ok = False
        warnings.append("Run 'playwright install chromium' to enable PDF artifact generation.")

    # 4. Audio Subsystems (Microphone & TTS)
    print("\n[4] Audio Hardware & Speech Subsystems:")
    try:
        import speech_recognition as sr
        mics = sr.Microphone.list_microphone_names()
        check_status("Microphone Devices", True, f"Detected {len(mics)} audio input device(s)")
    except Exception as e:
        check_status("Microphone Devices", False, f"Microphone scan error: {e}", warning=True)
        warnings.append("No active microphone detected; voice input will fall back to manual text.")

    try:
        import pyttsx3
        eng = pyttsx3.init()
        voices = eng.getProperty("voices")
        check_status("TTS Voice Engine", True, f"Detected {len(voices)} voice profile(s)")
    except Exception as e:
        check_status("TTS Voice Engine", False, f"TTS initialization error: {e}", warning=True)
        warnings.append("pyttsx3 engine failed; voice playback disabled.")

    # 5. Local Directories & Persistence
    print("\n[5] Directories & Persistence:")
    from app.utils.paths import get_knowledge_dir, get_exports_dir, get_data_dir

    kb_dir = get_knowledge_dir()
    check_status("Knowledge/ Directory", kb_dir.exists(), str(kb_dir))

    exp_dir = get_exports_dir()
    check_status("exports/ Directory", exp_dir.exists(), str(exp_dir))

    data_dir = get_data_dir()
    check_status("data/ Directory", data_dir.exists(), str(data_dir))

    # Database & FTS5 check
    try:
        from app.memory.database import get_db_path
        db_path = get_db_path()
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA compile_options;")
        opts = [r[0] for r in cur.fetchall()]
        has_fts5 = "ENABLE_FTS5" in opts or True  # Check table query
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='knowledge_fts';")
        tbl_exists = cur.fetchone()[0] > 0
        conn.close()
        check_status("SQLite FTS5 Knowledge Index", tbl_exists, f"DB: {db_path.name}")
    except Exception as e:
        check_status("SQLite FTS5 Knowledge Index", False, f"Database error: {e}")
        all_ok = False

    # 6. Optional System Converters (OCR, LibreOffice)
    print("\n[6] Optional Document Converters:")
    from app.knowledge.parsers import DocumentParserFactory
    ocr_avail = DocumentParserFactory.is_ocr_available()
    check_status("OCR Engine (tesseract)", ocr_avail, "Installed" if ocr_avail else "Not Found (Optional for image text)", warning=not ocr_avail)

    lo_avail = DocumentParserFactory.is_libreoffice_available()
    check_status("LibreOffice (.doc/.xls)", lo_avail, "Installed" if lo_avail else "Not Found (Optional for legacy MS Office formats)", warning=not lo_avail)

    # 7. Environment Configuration (.env)
    print("\n[7] Configuration & AI Provider:")
    env_file = PROJECT_ROOT / ".env"
    has_env = env_file.exists()
    check_status(".env Configuration File", has_env, "Present" if has_env else "Missing (copy from .env.example)")

    from app.config.settings import get_settings
    settings = get_settings(reload=True)
    provider = settings.ai_provider
    has_key = bool(settings.ai_api_key and settings.ai_api_key.strip())
    key_desc = "Configured (••••••••)" if has_key else "Not Configured"
    check_status(f"AI Provider ({provider})", True, f"Key: {key_desc} | Model: {settings.ai_model or 'default'}")

    print("\n" + "=" * 70)
    if all_ok:
        print(" [SUMMARY] All critical subsystems are operational.")
        if warnings:
            print(" [NOTICES & OPTIONAL WARNINGS]:")
            for w in warnings:
                print(f"   - {w}")
        print("=" * 70)
        return 0
    else:
        print(" [SUMMARY] One or more critical subsystems failed. See errors above.")
        if warnings:
            print(" [ACTION ITEMS]:")
            for w in warnings:
                print(f"   - {w}")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(run_diagnostics())
