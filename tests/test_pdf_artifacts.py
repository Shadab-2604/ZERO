"""
Automated unit and integration tests for Zero AI PDF Artifact Generation subsystem.
Validates HTML compilation, Playwright rendering, %PDF- magic headers,
path traversal security, table/code styling, and download safety.
"""

import tempfile
from pathlib import Path
import pytest
from app.exports.pdf_generator import PDFGenerator


@pytest.fixture
def temp_exports_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_filename_sanitization():
    """Verify filename sanitization removes illegal characters and path traversals."""
    assert PDFGenerator.sanitize_filename("Normal Report") == "Normal_Report.pdf"
    assert PDFGenerator.sanitize_filename("Report.pdf") == "Report.pdf"
    # Path traversal attempts
    assert ".." not in PDFGenerator.sanitize_filename("../../etc/passwd")
    assert "/" not in PDFGenerator.sanitize_filename("dir/subdir/report.pdf")
    assert "\\" not in PDFGenerator.sanitize_filename("dir\\subdir\\report.pdf")
    assert ":" not in PDFGenerator.sanitize_filename("C:report.pdf")
    # Empty string fallback
    clean_empty = PDFGenerator.sanitize_filename("")
    assert clean_empty.startswith("zero_report_")
    assert clean_empty.endswith(".pdf")


def test_html_report_compilation():
    """Verify Markdown is transformed into structured HTML with executive CSS."""
    markdown_content = """# Executive Report
This is a test document with **bold text** and `inline code`.

## Telemetry Table
| Core | Load |
| :--- | :--- |
| CPU  | 12%  |
| GPU  | 4%   |

```python
def active():
    return True
```
"""
    html = PDFGenerator.create_html_report(
        title="System Verification",
        body_markdown=markdown_content,
        subtitle="Test Run",
        author="Zero AI Tester",
    )

    assert "<!DOCTYPE html>" in html
    assert "<title>System Verification</title>" in html
    assert "<h1>System Verification</h1>" in html
    assert "Telemetry Table" in html
    assert "<table" in html
    assert "<pre><code" in html
    assert "ZERO // ARTIFACT" in html
    assert "@page" in html  # CSS verified


def test_pdf_generation_and_signature(temp_exports_dir):
    """Verify Playwright Chromium compiles HTML to verified, non-empty PDF artifact."""
    html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Test Doc</title></head>
<body>
<h1>Zero AI Automated Test PDF</h1>
<p>This is a headless browser verification artifact.</p>
</body>
</html>"""

    pdf_path = PDFGenerator.generate_pdf(
        html_content=html,
        filename="test_output.pdf",
        exports_dir=temp_exports_dir,
    )

    assert pdf_path.exists()
    assert pdf_path.name == "test_output.pdf"
    size = pdf_path.stat().st_size
    assert size > 1000  # Valid PDF is several kilobytes

    # Verify %PDF- signature
    with pdf_path.open("rb") as f:
        header = f.read(5)
        assert header.startswith(b"%PDF-")


def test_pdf_with_tables_and_code(temp_exports_dir):
    """Verify document with complex Markdown structures compiles properly."""
    content = """## Benchmark Matrix
| Index | Operation | Status |
| :--- | :--- | :--- |
| 1 | Database Sync | Complete |
| 2 | Speech Engine | Online |

```bash
# Terminal execution
python main.py --voice
```
"""
    html = PDFGenerator.create_html_report(
        title="Benchmark Summary",
        body_markdown=content,
    )

    pdf_path = PDFGenerator.generate_pdf(
        html_content=html,
        filename="benchmark_summary.pdf",
        exports_dir=temp_exports_dir,
    )

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def test_path_traversal_rejection(temp_exports_dir):
    """Verify path traversal attempts are rejected when generating PDF."""
    html = "<html><body>Test</body></html>"
    # Even if an un-sanitized traversal string were passed, sanitize_filename strips it
    safe_name = PDFGenerator.sanitize_filename("../../../malicious.pdf")
    pdf_path = PDFGenerator.generate_pdf(
        html_content=html,
        filename=safe_name,
        exports_dir=temp_exports_dir,
    )
    # Target must reside strictly in temp_exports_dir
    assert pdf_path.parent.resolve() == temp_exports_dir.resolve()
