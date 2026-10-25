# Zero AI — Cleanup Candidates & Repository Inventory

This report details the audit of potential cleanup candidates across the Zero AI codebase in accordance with Section 6 of the cleanup specification.

In accordance with architectural safety rules, **no ambiguous files or user data have been deleted automatically**. Each item below is categorized as either **Confirmed Safe to Keep**, **Generated Runtime Artifact**, or **Candidate for User Review**.

---

## 1. Inventory of Candidates

| Item | Location | Type | Status | Action / Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| `stitch_z.e.r.o._desktop_ai_interface.zip` | Root (`/`) | Binary Zip Archive (1.24 MB) | **Requires User Review** | Contains HTML & PNG design mockups exported from Google Stitch. Not referenced or imported at runtime. Keep for UI design reference or move to an `archive/` folder if reducing repo size is desired. **Do not delete automatically.** |
| `exports/*.pdf` | `exports/` | Generated Artifacts (~170 KB) | **Generated Artifacts** | Verified PDF artifacts produced during automated test runs (`Zero_AI_System_&_Knowledge_Report.pdf`, `diagnostic_report_network___system_diagnost.pdf`). Safe to retain for verification or clear via `clean` script. `.gitignore` preserves directory via `.gitkeep`. |
| `reports/evaluation_results.json` | `reports/` | Test Evaluation Data (34 KB) | **Historical Benchmark** | Benchmark result output from `scripts/evaluate_zero.py`. Safe to keep as evaluation baseline. |
| `logs/zero.log` | `logs/` | Runtime Logs | **Ephemeral Log** | Rotating application log. Ignored by Git. |
| `logs/ai_connection_report.json` | `logs/` | Diagnostic Telemetry (<1 KB) | **Diagnostic Cache** | Last recorded latency and connection status for Ollama models. Automatically regenerated at startup. |
| `data/zero.db` | `data/` | SQLite Database (~1.8 MB) | **CRITICAL USER DATA** | **DO NOT DELETE.** Stores persistent chat conversations, session timelines, user preferences, and activity events. |
| `Knowledge/*.pdf` | `Knowledge/` | Reference Documents (50+ files) | **CRITICAL KNOWLEDGE SOURCE** | **DO NOT DELETE OR MOVE.** Contains user technical documentation ingested and indexed into the SQLite FTS5 RAG store. |

---

## 2. Source Code & Module Audit Findings

### A. Dead / Obsolete Modules
- **Result:** **0 Dead Modules Detected.**
- All Python modules in `app/` are actively imported, coordinated by the central assistant engine (`app/core/assistant.py`), or exercised by the 187 automated unit and integration tests.

### B. Unused Dependencies
- **Result:** **0 Unused Dependencies.**
- All 22 packages listed in `requirements.txt` and `pyproject.toml` correspond directly to active features:
  - **PySide6**: Native desktop GUI, vector AI Orb, chat bubbles, sidebar, and HUD.
  - **fastapi & uvicorn**: Isolated loopback REST API server on `127.0.0.1:8765`.
  - **pydantic & pydantic-settings**: Environment variable schema parsing and validation.
  - **sqlalchemy**: SQLite database ORM, connection pooling, and transactional scopes.
  - **httpx**: Ollama REST API streaming inference and model health checks.
  - **psutil & pywin32**: Windows process enumeration, window management, and hardware telemetry.
  - **pyttsx3, SpeechRecognition, PyAudio**: Windows SAPI5 TTS and real-time streaming VAD.
  - **pypdf, python-docx, python-pptx, openpyxl, markdown**: Multi-format Knowledge ingestion.
  - **playwright**: Headless Chromium HTML-to-PDF rendering and verified artifact generation.
  - **pytest & pytest-asyncio**: Test suite execution.

---

## 3. Recommended Actions for the User

1. **`stitch_z.e.r.o._desktop_ai_interface.zip`**:
   - If you want to keep the offline UI mockups for future design reference, keep it as is.
   - If you prefer a lighter Git clone size, you may extract it to a local design folder outside the Git tree and delete the zip file from Git.

2. **`exports/` Directory**:
   - The test PDFs are safe to delete at any time if you wish to start with a fresh exports folder:
     ```powershell
     Remove-Item exports\*.pdf
     ```
   - The `.gitkeep` file ensures the folder structure is maintained.
