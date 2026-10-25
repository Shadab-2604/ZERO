"""
Zero AI — Document Generation & PDF Artifact Export.

Responsibilities:
- Beautiful HTML report compilation with styled typography, tables, and code syntax blocks.
- Headless Chromium rendering and verified PDF artifact export via Playwright.
- Path traversal prevention for file downloads.
"""

from app.exports.pdf_generator import PDFGenerator

__all__ = ["PDFGenerator"]
