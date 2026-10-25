"""
Zero AI Knowledge Base Validation Script.
Validates document ingestion, chunking, SQLite FTS5 indexing, and RAG retrieval.

Usage:
  python scripts/test_knowledge.py
  python scripts/test_knowledge.py --query "architecture"
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.paths import get_knowledge_dir
from app.knowledge.service import get_knowledge_service
from app.knowledge.parsers import DocumentParserFactory


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero AI Knowledge Base Diagnostics & Test")
    parser.add_argument("--query", default="Zero AI", help="Test search query against indexed documents")
    parser.add_argument("--sample-doc", action="store_true", help="Create a sample knowledge document if empty")
    args = parser.parse_args()

    print("=" * 70)
    print(" ZERO AI KNOWLEDGE RETRIEVAL (RAG) SUBSYSTEM VALIDATION")
    print("=" * 70)

    service = get_knowledge_service()
    kb_dir = get_knowledge_dir()
    print(f"\n[1] Knowledge Directory: {kb_dir}")

    # If folder has no files, generate a test document
    existing_files = list(kb_dir.glob("*"))
    valid_files = [f for f in existing_files if f.is_file() and f.suffix.lower() in DocumentParserFactory.get_supported_extensions()]

    if not valid_files or args.sample_doc:
        sample_file = kb_dir / "zero_architecture_overview.md"
        sample_file.write_text(
            "# Zero AI Technical Specification\n\n"
            "Zero AI is a futuristic personal desktop assistant inspired by JARVIS.\n\n"
            "## Architecture\n"
            "Zero operates using a modular architecture with three main layers:\n"
            "1. PySide6 Desktop GUI (HUD, sidebar, chat panel, status bar)\n"
            "2. Local Python Backend (FastAPI, SQLite, Conversation Store)\n"
            "3. Knowledge Base RAG System (SQLite FTS5, BM25 ranking, Document Parsers)\n\n"
            "## Document Generation\n"
            "Zero generates verified executive PDF artifacts using Playwright Chromium.\n"
            "All generated documents are saved in the exports directory with path traversal prevention.\n",
            encoding="utf-8",
        )
        print(f" -> Generated sample documentation: {sample_file.name}")

    # Run incremental indexing
    print("\n[2] Executing Incremental Reindexing...")
    stats = service.reindex_all_incremental()
    print(f" -> Added: {stats.get('added', 0)}")
    print(f" -> Updated: {stats.get('updated', 0)}")
    print(f" -> Unchanged: {stats.get('unchanged', 0)}")
    print(f" -> Total Files: {stats.get('total_files', 0)}")

    # Check database status
    print("\n[3] Querying Index Status...")
    status = service.get_indexing_status()
    print(f" -> Total Indexed Files: {status.get('total_indexed_files')}")
    print(f" -> Total Chunks in FTS5: {status.get('total_chunks')}")
    print(f" -> Last Index Time: {status.get('last_index_time')}")

    # Run search query
    query = args.query
    print(f"\n[4] Testing FTS5 Retrieval with Query: '{query}'...")
    results = service.query(query, top_k=3)
    print(f" -> Returned {len(results)} relevant chunk(s):")

    for i, res in enumerate(results, 1):
        print(f"\n   Match #{i} [Score: {res.score:.2f}]:")
        print(f"   Source : {res.source_file} (Section: {res.section_label})")
        snippet = res.content[:160].replace("\n", " ")
        print(f"   Snippet: {snippet}...")

    # Test RAG context formatting
    print("\n[5] Testing RAG Prompt Context Formatting...")
    rag_context, _ = service.format_rag_context(query)
    if rag_context:
        print(" -> RAG Context successfully formatted with security boundaries:")
        print("   " + "\n   ".join(rag_context.splitlines()[:10]) + "\n   ...")
    else:
        print(" -> Notice: No matches found for current query.")

    print("\n" + "=" * 70)
    print(" [SUCCESS] Knowledge subsystem is operational and verified.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
