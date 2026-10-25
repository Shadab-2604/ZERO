"""
Modular Document Ingestion and Text Extraction Engine for Zero AI.
Extracts structured text and metadata from PDFs, Office documents,
spreadsheets, data formats, source code, and plain text.
Explicitly rejects executable and audio/video files.
"""

from dataclasses import dataclass, field
import csv
import json
import logging
import os
from pathlib import Path
import re
import shutil
from typing import Any

logger = logging.getLogger(__name__)

# Extensions that must be rejected immediately from knowledge ingestion
AUDIO_VIDEO_EXTENSIONS = {
    ".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma", ".m4a", ".opus",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm", ".flv", ".m4v",
}

# Image extensions (indexed only if OCR is configured)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}

# Source code extensions
CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".php", ".cs",
    ".cpp", ".c", ".h", ".hpp", ".sql", ".sh", ".bat", ".ps1",
    ".css", ".scss", ".sass", ".less", ".go", ".rs", ".rb", ".swift",
    ".kt", ".scala", ".lua", ".r", ".m",
}

# Plain text, notes, and documentation extensions
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".log"}

# Structured data formats
DATA_EXTENSIONS = {".csv", ".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg"}

# Web documents
WEB_EXTENSIONS = {".html", ".htm", ".xml", ".xhtml", ".svg"}


# Binary and executable extensions that should not be indexed as text
UNSUPPORTED_BINARY_EXTENSIONS = {
    ".db", ".sqlite", ".sqlite3", ".exe", ".dll", ".so", ".bin", ".dat",
    ".iso", ".img", ".dmg", ".pkg", ".deb", ".rpm", ".msi", ".pyc", ".pyd",
    ".class", ".jar", ".zip", ".tar", ".gz", ".7z", ".rar",
}


@dataclass
class DocumentSection:
    """A distinct logical section or page within a document."""
    label: str  # e.g., "Page 1", "Slide 3", "Sheet: Sales", "Function: main"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Result of extracting text and metadata from a file."""
    file_path: Path
    file_type: str
    sections: list[DocumentSection] = field(default_factory=list)
    total_chars: int = 0
    error: str | None = None
    is_rejected: bool = False
    rejection_reason: str | None = None

    @property
    def full_text(self) -> str:
        """Combine all section texts."""
        return "\n\n".join(s.content for s in self.sections if s.content.strip())

    @property
    def text(self) -> str:
        """Alias for full_text."""
        return self.full_text

    @property
    def success(self) -> bool:
        """True if extraction completed without error and was not rejected."""
        return self.error is None and not self.is_rejected


class DocumentParserFactory:
    """Factory and dispatcher for file parsers."""

    @classmethod
    def can_parse(cls, path: Path) -> bool:
        """Return True if file extension is supported and not audio/video or unsupported binary."""
        ext = path.suffix.lower()
        if cls.is_audio_video(path) or ext in UNSUPPORTED_BINARY_EXTENSIONS:
            return False
        return ext in cls.get_supported_extensions()

    @classmethod
    def parse(cls, path: Path) -> ParsedDocument:
        """Dispatch parsing of file."""
        return cls.parse_file(path)

    @staticmethod
    def is_audio_video(path: Path) -> bool:
        """Check if file is audio or video."""
        return path.suffix.lower() in AUDIO_VIDEO_EXTENSIONS

    @staticmethod
    def is_ocr_available() -> bool:
        """Check if Tesseract OCR is available on the host system."""
        try:
            import pytesseract
            # Check if tesseract binary is in path
            return bool(shutil.which("tesseract"))
        except Exception:
            return False

    @staticmethod
    def is_libreoffice_available() -> bool:
        """Check if LibreOffice soffice binary is installed for legacy doc conversion."""
        return bool(shutil.which("soffice") or shutil.which("libreoffice"))

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Return list of supported file extensions."""
        exts = [
            ".pdf", ".docx", ".pptx", ".xlsx",
            *sorted(TEXT_EXTENSIONS),
            *sorted(DATA_EXTENSIONS),
            *sorted(WEB_EXTENSIONS),
            *sorted(CODE_EXTENSIONS),
        ]
        if cls.is_libreoffice_available():
            exts.extend([".doc", ".ppt", ".xls", ".odt", ".ods", ".odp"])
        if cls.is_ocr_available():
            exts.extend(sorted(IMAGE_EXTENSIONS))
        return sorted(list(set(exts)))

    @classmethod
    def parse_file(cls, path: Path) -> ParsedDocument:
        """Parse file content and return structured sections."""
        ext = path.suffix.lower()

        # 1. Reject audio/video files
        if cls.is_audio_video(path):
            return ParsedDocument(
                file_path=path,
                file_type=ext,
                is_rejected=True,
                rejection_reason="Audio and video files cannot be indexed into text knowledge base.",
            )

        # 2. Reject unsupported binary and database files
        if ext in UNSUPPORTED_BINARY_EXTENSIONS:
            return ParsedDocument(
                file_path=path,
                file_type=ext,
                is_rejected=True,
                rejection_reason=f"Binary file type '{ext}' is unsupported for text knowledge indexing. Convert to PDF, Word, or plain text.",
            )

        # 3. Check existence
        if not path.is_file():
            return ParsedDocument(
                file_path=path,
                file_type=ext,
                error="File does not exist on disk.",
            )

        # 4. Handle empty files
        if path.stat().st_size == 0:
            return ParsedDocument(
                file_path=path,
                file_type=ext,
                sections=[],
                total_chars=0,
                error="File is empty (0 bytes).",
            )

        try:
            if ext == ".pdf":
                return cls._parse_pdf(path)
            elif ext == ".docx":
                return cls._parse_docx(path)
            elif ext == ".pptx":
                return cls._parse_pptx(path)
            elif ext == ".xlsx":
                return cls._parse_xlsx(path)
            elif ext == ".csv":
                return cls._parse_csv(path)
            elif ext in DATA_EXTENSIONS:
                return cls._parse_data_file(path)
            elif ext in WEB_EXTENSIONS:
                return cls._parse_web_file(path)
            elif ext in CODE_EXTENSIONS:
                return cls._parse_code_file(path)
            elif ext in TEXT_EXTENSIONS:
                return cls._parse_text_file(path)
            elif ext in (".doc", ".ppt", ".xls", ".odt", ".ods", ".odp"):
                return cls._parse_legacy_office(path)
            elif ext in IMAGE_EXTENSIONS:
                return cls._parse_image(path)
            else:
                # Try generic text extraction fallback
                return cls._parse_text_file(path)
        except Exception as e:
            logger.error("Failed to parse file %s: %s", path.name, e)
            return ParsedDocument(
                file_path=path,
                file_type=ext,
                error=f"Parsing error: {type(e).__name__} ({str(e)})",
            )

    # -------------------------------------------------------------------------
    # Format-Specific Parsers
    # -------------------------------------------------------------------------

    @classmethod
    def _read_text_with_fallback(cls, path: Path) -> str:
        """Attempt reading file using multiple common encodings."""
        encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1", "iso-8859-1"]
        raw = path.read_bytes()
        for enc in encodings:
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        # Fallback with replacement characters
        return raw.decode("utf-8", errors="replace")

    @classmethod
    def _parse_pdf(cls, path: Path) -> ParsedDocument:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        sections: list[DocumentSection] = []
        total_chars = 0

        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                sections.append(
                    DocumentSection(
                        label=f"Page {i}",
                        content=text,
                        metadata={"page": i, "total_pages": len(reader.pages)},
                    )
                )
                total_chars += len(text)

        return ParsedDocument(
            file_path=path,
            file_type=".pdf",
            sections=sections,
            total_chars=total_chars,
        )

    @classmethod
    def _parse_docx(cls, path: Path) -> ParsedDocument:
        import docx
        doc = docx.Document(str(path))
        paragraphs = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                paragraphs.append(text)

        # Include table contents
        for table in doc.tables:
            table_lines = []
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                if any(cells):
                    table_lines.append(" | ".join(cells))
            if table_lines:
                paragraphs.append("\n".join(table_lines))

        full_content = "\n\n".join(paragraphs)
        sections = [
            DocumentSection(
                label="Document Content",
                content=full_content,
                metadata={"paragraphs": len(paragraphs)},
            )
        ] if full_content else []

        return ParsedDocument(
            file_path=path,
            file_type=".docx",
            sections=sections,
            total_chars=len(full_content),
        )

    @classmethod
    def _parse_pptx(cls, path: Path) -> ParsedDocument:
        import pptx
        prs = pptx.Presentation(str(path))
        sections: list[DocumentSection] = []
        total_chars = 0

        for i, slide in enumerate(prs.slides, start=1):
            slide_texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = para.text.strip()
                        if text:
                            slide_texts.append(text)
            content = "\n".join(slide_texts)
            if content:
                sections.append(
                    DocumentSection(
                        label=f"Slide {i}",
                        content=content,
                        metadata={"slide": i, "total_slides": len(prs.slides)},
                    )
                )
                total_chars += len(content)

        return ParsedDocument(
            file_path=path,
            file_type=".pptx",
            sections=sections,
            total_chars=total_chars,
        )

    @classmethod
    def _parse_xlsx(cls, path: Path) -> ParsedDocument:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
        sections: list[DocumentSection] = []
        total_chars = 0

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            rows_text = []
            for row in sheet.iter_rows(values_only=True):
                if not row or not any(row):
                    continue
                row_vals = [str(v).strip() if v is not None else "" for v in row]
                rows_text.append(", ".join(row_vals))

            content = "\n".join(rows_text)
            if content:
                sections.append(
                    DocumentSection(
                        label=f"Sheet: {sheet_name}",
                        content=content,
                        metadata={"sheet": sheet_name},
                    )
                )
                total_chars += len(content)

        wb.close()
        return ParsedDocument(
            file_path=path,
            file_type=".xlsx",
            sections=sections,
            total_chars=total_chars,
        )

    @classmethod
    def _parse_csv(cls, path: Path) -> ParsedDocument:
        text = cls._read_text_with_fallback(path)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content = "\n".join(lines[:2000])  # Cap very large CSVs
        sections = [
            DocumentSection(
                label="CSV Records",
                content=content,
                metadata={"rows": len(lines)},
            )
        ] if content else []
        return ParsedDocument(
            file_path=path,
            file_type=".csv",
            sections=sections,
            total_chars=len(content),
        )

    @classmethod
    def _parse_data_file(cls, path: Path) -> ParsedDocument:
        text = cls._read_text_with_fallback(path)
        ext = path.suffix.lower()
        # Prettify json if possible
        if ext == ".json":
            try:
                data = json.loads(text)
                text = json.dumps(data, indent=2)
            except Exception:
                pass

        sections = [
            DocumentSection(
                label=f"Data ({ext.upper()})",
                content=text,
                metadata={"format": ext},
            )
        ] if text.strip() else []

        return ParsedDocument(
            file_path=path,
            file_type=ext,
            sections=sections,
            total_chars=len(text),
        )

    @classmethod
    def _parse_web_file(cls, path: Path) -> ParsedDocument:
        text = cls._read_text_with_fallback(path)
        # Strip script and style blocks
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Strip tags and normalize entities
        clean_text = re.sub(r"<[^>]+>", " ", text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        sections = [
            DocumentSection(
                label="Web Document",
                content=clean_text,
                metadata={"format": path.suffix.lower()},
            )
        ] if clean_text else []

        return ParsedDocument(
            file_path=path,
            file_type=path.suffix.lower(),
            sections=sections,
            total_chars=len(clean_text),
        )

    @classmethod
    def _parse_code_file(cls, path: Path) -> ParsedDocument:
        text = cls._read_text_with_fallback(path)
        ext = path.suffix.lower()
        sections = [
            DocumentSection(
                label=f"Source Code ({ext})",
                content=text,
                metadata={"language": ext.lstrip(".")},
            )
        ] if text.strip() else []

        return ParsedDocument(
            file_path=path,
            file_type=ext,
            sections=sections,
            total_chars=len(text),
        )

    @classmethod
    def _parse_text_file(cls, path: Path) -> ParsedDocument:
        text = cls._read_text_with_fallback(path)
        ext = path.suffix.lower()
        sections = [
            DocumentSection(
                label="Document Text",
                content=text,
                metadata={"format": ext},
            )
        ] if text.strip() else []

        return ParsedDocument(
            file_path=path,
            file_type=ext,
            sections=sections,
            total_chars=len(text),
        )

    @classmethod
    def _parse_legacy_office(cls, path: Path) -> ParsedDocument:
        if not cls.is_libreoffice_available():
            return ParsedDocument(
                file_path=path,
                file_type=path.suffix.lower(),
                error=(
                    f"Legacy Office format '{path.suffix}' requires LibreOffice for conversion. "
                    "Install LibreOffice and ensure 'soffice' is on PATH, or save as modern .docx/.xlsx."
                ),
            )
        # If libreoffice is available, convert to pdf and extract
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = ["soffice", "--headless", "--convert-to", "pdf", str(path), "--outdir", tmpdir]
            res = subprocess.run(cmd, capture_output=True, timeout=30)
            converted_pdf = Path(tmpdir) / f"{path.stem}.pdf"
            if converted_pdf.exists():
                parsed = cls._parse_pdf(converted_pdf)
                parsed.file_path = path
                parsed.file_type = path.suffix.lower()
                return parsed

        return ParsedDocument(
            file_path=path,
            file_type=path.suffix.lower(),
            error=f"Failed to convert '{path.name}' via LibreOffice.",
        )

    @classmethod
    def _parse_image(cls, path: Path) -> ParsedDocument:
        if not cls.is_ocr_available():
            return ParsedDocument(
                file_path=path,
                file_type=path.suffix.lower(),
                error=(
                    f"Image text extraction requires Tesseract OCR. "
                    "Install Tesseract and pytesseract to index images."
                ),
            )
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(path)
            text = pytesseract.image_to_string(img).strip()
            sections = [
                DocumentSection(
                    label="OCR Text",
                    content=text,
                    metadata={"engine": "Tesseract"},
                )
            ] if text else []
            return ParsedDocument(
                file_path=path,
                file_type=path.suffix.lower(),
                sections=sections,
                total_chars=len(text),
            )
        except Exception as e:
            return ParsedDocument(
                file_path=path,
                file_type=path.suffix.lower(),
                error=f"OCR extraction failed: {e}",
            )
