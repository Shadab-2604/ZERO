"""
Zero AI PDF Export Pipeline Validation Script.
Validates HTML-to-PDF compilation via Playwright Chromium,
verifies %PDF- signature and non-empty artifact creation in exports/.

Usage:
  python scripts/test_pdf_export.py
  python scripts/test_pdf_export.py --title "Custom Report"
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.paths import get_exports_dir
from app.exports.pdf_generator import get_pdf_generator, PDFGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero AI PDF Generation Test")
    parser.add_argument("--title", default="Zero AI System & Knowledge Report", help="Document title")
    args = parser.parse_args()

    print("=" * 70)
    print(" ZERO AI // PDF ARTIFACT GENERATION & VERIFICATION PIPELINE")
    print("=" * 70)

    exports_dir = get_exports_dir()
    print(f"Exports Directory: {exports_dir}")

    # Build rich markdown content with tables, code blocks, lists, and unicode
    sample_content = """## Executive Summary
This document was compiled automatically by **ZERO AI Assistant** using the Playwright headless browser PDF generation pipeline.

### Verified Architecture & Capabilities
* **Knowledge Retrieval:** SQLite FTS5 Full-Text Search with BM25 ranking.
* **Document Parsers:** Modular multi-format ingestion (PDF, Word, PPTX, Excel, Code, Text).
* **Voice Subsystem:** Non-blocking TTS synthesis and microphone speech recognition.
* **PDF Artifacts:** High-fidelity executive HTML styling converted to verified PDF documents.

### System Telemetry & Benchmark Data

| Subsystem | Status | Latency | Redundancy |
| :--- | :--- | :--- | :--- |
| **FTS5 Index** | Operational | < 5 ms | Persistent Disk |
| **Playwright Engine** | Active | ~ 450 ms | Chromium Headless |
| **Audio Synthesis** | Standing By | Real-time | SAPI5 / pyttsx3 |
| **FastAPI REST API** | 127.0.0.1:8765 | < 2 ms | Loopback Isolated |

### Code Implementation Reference
```python
def query_knowledge(prompt: str) -> list[str]:
    # Non-blocking SQLite FTS5 BM25 retrieval
    results = knowledge_service.search(prompt, limit=5)
    return [r.content for r in results]
```

> **Security Notice:** All document contents are isolated and treated strictly as untrusted reference material. System prompt instructions cannot be overridden by document text.
"""

    print("\n[1] Compiling styled HTML document...")
    generator = get_pdf_generator()
    html = generator.create_html_report(
        title=args.title,
        body_markdown=sample_content,
        subtitle="Automated Verification Artifact",
        author="Zero AI Test Runner",
    )
    print(f" -> HTML length: {len(html)} characters")

    print("\n[2] Rendering PDF via Playwright Chromium...")
    try:
        pdf_path = generator.generate_pdf(html, filename=generator.sanitize_filename(args.title))
        print(f" -> Artifact created: {pdf_path.name}")
    except Exception as e:
        print(f"\n[FATAL ERROR] PDF rendering failed: {e}")
        return 1

    print("\n[3] Validating PDF Artifact Integrity...")
    if not pdf_path.exists():
        print(" [FAIL] Output file does not exist.")
        return 1

    file_size = pdf_path.stat().st_size
    print(f" -> File Size: {file_size:,} bytes")
    if file_size == 0:
        print(" [FAIL] Output file is empty (0 bytes).")
        return 1

    # Check %PDF- magic signature
    with pdf_path.open("rb") as f:
        header = f.read(5)
        print(f" -> Header Signature: {header}")
        if not header.startswith(b"%PDF-"):
            print(" [FAIL] Invalid file signature; missing '%PDF-'.")
            return 1

    print("\n" + "=" * 70)
    print(f" [SUCCESS] PDF artifact verified and ready for download:")
    print(f" Location: {pdf_path}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
