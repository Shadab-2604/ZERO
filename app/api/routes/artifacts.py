"""
Artifacts and PDF generation REST API endpoints for Zero AI.
Enforces strict path traversal prevention, verified PDF headers, and safe downloads.
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.utils.paths import get_exports_dir
from app.exports.pdf_generator import get_pdf_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])


class GeneratePDFRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Document title")
    html_content: str = Field(..., min_length=1, description="Document HTML body content")
    category: str = Field(default="Report", max_length=50, description="Document category or subtitle")


@router.post("/generate-pdf")
async def generate_pdf_artifact(req: GeneratePDFRequest):
    """Generate a verified PDF document using headless browser rendering."""
    try:
        generator = get_pdf_generator()
        doc = await generator.generate_document(
            title=req.title,
            body_html=req.html_content,
            doc_type=req.category,
        )
        return {
            "status": "success",
            "pdf_filename": doc["filename"],
            "pdf_path": doc["filepath"],
            "file_size": doc["size_bytes"],
            "download_url": f"/api/artifacts/download/{doc['filename']}",
        }
    except Exception as e:
        logger.error("PDF artifact generation error: %s", e)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


@router.get("/download/{filename}")
def download_artifact(filename: str):
    """
    Safely download a generated artifact file from the exports directory.
    Rejects any path traversal attempts.
    """
    # Path traversal validation
    if ".." in filename or "/" in filename or "\\" in filename:
        logger.warning("Rejected suspicious artifact download path: %s", filename)
        raise HTTPException(status_code=400, detail="Invalid filename format.")

    exports_dir = get_exports_dir().resolve()
    target_path = (exports_dir / filename).resolve()

    # Verify target stays inside exports directory
    if not str(target_path).startswith(str(exports_dir)):
        raise HTTPException(status_code=403, detail="Access denied.")

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found.")

    # Media type detection
    media_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"

    return FileResponse(
        path=target_path,
        media_type=media_type,
        filename=target_path.name,
    )
