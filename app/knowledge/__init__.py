"""
Knowledge Base and Document Ingestion Package for Zero AI.
"""

from app.knowledge.parsers import DocumentParserFactory, ParsedDocument
from app.knowledge.service import KnowledgeService, get_knowledge_service

__all__ = [
    "DocumentParserFactory",
    "ParsedDocument",
    "KnowledgeService",
    "get_knowledge_service",
]
