"""
Knowledge Base REST API endpoints for Zero AI.
Exposes file listing, status, semantic/keyword search, incremental reindexing,
and file removal with path safety.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.knowledge.service import get_knowledge_service
from app.knowledge.parsers import DocumentParserFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Search query string")
    top_k: int = Field(default=5, ge=1, le=50, description="Max results to return")


class ReindexFileRequest(BaseModel):
    filename: str = Field(..., min_length=1, description="Document filename to reindex")


@router.get("/status")
def get_knowledge_status():
    """Return knowledge base index statistics and parser capabilities."""
    service = get_knowledge_service()
    status = service.get_indexing_status()
    status["supported_extensions"] = DocumentParserFactory.get_supported_extensions()
    status["ocr_available"] = DocumentParserFactory.is_ocr_available()
    status["libreoffice_available"] = DocumentParserFactory.is_libreoffice_available()
    return status


@router.get("/files")
def list_knowledge_files():
    """Return list of all indexed files and extraction metadata."""
    service = get_knowledge_service()
    files = service.list_files()
    return {
        "count": len(files),
        "files": files,
    }


@router.post("/search")
def search_knowledge(req: KnowledgeSearchRequest):
    """Query knowledge base using local SQLite FTS5 index."""
    service = get_knowledge_service()
    results = service.query(query=req.query, top_k=req.top_k)
    return {
        "query": req.query,
        "count": len(results),
        "results": [r.to_dict() for r in results],
    }


@router.post("/reindex")
def reindex_all():
    """Perform incremental rescan and reindex of the Knowledge/ directory."""
    service = get_knowledge_service()
    try:
        stats = service.reindex_all_incremental()
        return {
            "status": "success",
            "stats": stats,
        }
    except Exception as e:
        logger.error("Knowledge reindexing failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {e}")


@router.post("/reindex-file")
def reindex_file(req: ReindexFileRequest):
    """Reindex an individual document by filename."""
    service = get_knowledge_service()
    doc_path = service.knowledge_dir / req.filename
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{req.filename}' not found in Knowledge folder.")
    try:
        res = service.index_file(doc_path)
        return {
            "status": "success",
            "file": req.filename,
            "result": res,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reindex file: {e}")


@router.delete("/files/{file_id}")
def delete_indexed_file(file_id: int):
    """Remove a file from the knowledge index."""
    service = get_knowledge_service()
    success = service.store.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File ID not found in knowledge index.")
    return {"status": "deleted", "file_id": file_id}
