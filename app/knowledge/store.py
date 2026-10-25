"""
Persistent Knowledge Storage & SQLite FTS5 Search Index.
Guarantees fast, offline, local BM25 full-text retrieval across indexed documents
with source citations (filename, page/section, excerpt, score).
"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import re
import sqlite3
from typing import Any, Generator
from app.memory.database import get_db_path
from app.knowledge.chunker import DocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A scored chunk match from knowledge search."""
    source_file: str
    section_label: str
    content: str
    score: float
    chunk_index: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "section_label": self.section_label,
            "content": self.content,
            "score": self.score,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
        }


class KnowledgeStore:
    """Manages SQLite tables and full-text index for Knowledge/ documents."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())
        self._init_schema()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Create tables and FTS5 search index if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Tracked Files Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_files (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    status TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    indexed_at TIMESTAMP NOT NULL
                )
                """
            )

            # 2. Document Chunks Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    section_label TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    metadata_json TEXT,
                    FOREIGN KEY(file_id) REFERENCES knowledge_files(id) ON DELETE CASCADE
                )
                """
            )

            # 3. Full-Text Search Virtual Table (FTS5)
            try:
                cursor.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                        chunk_id UNINDEXED,
                        file_id UNINDEXED,
                        section_label,
                        content,
                        tokenize='porter unicode61'
                    )
                    """
                )
                conn.commit()
            except sqlite3.OperationalError as e:
                logger.warning("FTS5 table initialization notice: %s", e)

    def record_file_status(
        self,
        file_id: str,
        file_path: str,
        file_hash: str,
        file_size: int,
        mtime: float,
        status: str,
        chunk_count: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Insert or update tracked file record."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_files
                (id, file_path, file_hash, file_size, mtime, status, chunk_count, error_message, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (file_id, file_path, file_hash, file_size, mtime, status, chunk_count, error_message, now),
            )
            conn.commit()

    def index_document(
        self,
        file_id: str,
        file_path: str,
        file_hash: str,
        file_size: int,
        mtime: float,
        chunks: list[DocumentChunk],
    ) -> None:
        """Helper to record file status and replace document chunks in a single call."""
        self.record_file_status(
            file_id=file_id,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            mtime=mtime,
            status="INDEXED",
            chunk_count=len(chunks),
        )
        self.replace_document_chunks(file_id=file_id, chunks=chunks)

    def replace_document_chunks(
        self,
        file_id: str,
        chunks: list[DocumentChunk],
    ) -> None:
        """Remove old chunks for file and insert new chunks into storage & FTS index."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Delete old chunks
            cursor.execute("DELETE FROM knowledge_chunks WHERE file_id = ?", (file_id,))
            try:
                cursor.execute("DELETE FROM knowledge_fts WHERE file_id = ?", (file_id,))
            except sqlite3.OperationalError:
                pass

            # Insert new chunks
            for c in chunks:
                chunk_id = f"{file_id}#{c.chunk_index}"
                meta_str = json.dumps(c.metadata)
                cursor.execute(
                    """
                    INSERT INTO knowledge_chunks (id, file_id, chunk_index, section_label, content, content_hash, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (chunk_id, file_id, c.chunk_index, c.section_label, c.content, c.content_hash, meta_str),
                )
                try:
                    cursor.execute(
                        """
                        INSERT INTO knowledge_fts (chunk_id, file_id, section_label, content)
                        VALUES (?, ?, ?, ?)
                        """,
                        (chunk_id, file_id, c.section_label, c.content),
                    )
                except sqlite3.OperationalError:
                    pass

            conn.commit()

    def delete_file(self, file_id: str) -> bool:
        """Delete file and its associated chunks from index."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_chunks WHERE file_id = ?", (file_id,))
            try:
                cursor.execute("DELETE FROM knowledge_fts WHERE file_id = ?", (file_id,))
            except sqlite3.OperationalError:
                pass
            cursor.execute("DELETE FROM knowledge_files WHERE id = ?", (file_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_file(self, file_id: str) -> dict[str, Any] | None:
        """Retrieve tracking metadata for a specific file."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_files(self) -> list[dict[str, Any]]:
        """List all tracked knowledge files."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_files ORDER BY id ASC")
            return [dict(r) for r in cursor.fetchall()]

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """
        Execute full-text search against indexed chunks using BM25 ranking.
        Falls back to LIKE queries if FTS5 query encounters syntax constraints.
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        # Sanitize query for FTS5: wrap alphanumeric tokens in quotes
        tokens = [re.sub(r"[^\w\-]", "", t) for t in clean_q.split()]
        fts_query = " OR ".join(f'"{t}"' for t in tokens if t)
        if not fts_query:
            return []

        results: list[SearchResult] = []

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    SELECT f.chunk_id, f.file_id, f.section_label, f.content, bm25(knowledge_fts) as rank, c.chunk_index, c.metadata_json
                    FROM knowledge_fts f
                    JOIN knowledge_chunks c ON f.chunk_id = c.id
                    WHERE knowledge_fts MATCH ?
                    ORDER BY rank ASC
                    LIMIT ?
                """
                cursor.execute(sql, (fts_query, limit))
                rows = cursor.fetchall()

                for r in rows:
                    meta = {}
                    if r["metadata_json"]:
                        try:
                            meta = json.loads(r["metadata_json"])
                        except Exception:
                            pass
                    # Convert negative BM25 score to positive relevance representation
                    score = round(abs(float(r["rank"])), 2)
                    results.append(
                        SearchResult(
                            source_file=r["file_id"],
                            section_label=r["section_label"],
                            content=r["content"],
                            score=score,
                            chunk_index=r["chunk_index"],
                            metadata=meta,
                        )
                    )
                return results

            except sqlite3.OperationalError as e:
                logger.warning("FTS MATCH error (%s), falling back to LIKE search", e)

            # Fallback search using LIKE
            like_pattern = f"%{clean_q}%"
            cursor.execute(
                """
                SELECT id, file_id, chunk_index, section_label, content, metadata_json
                FROM knowledge_chunks
                WHERE content LIKE ?
                LIMIT ?
                """,
                (like_pattern, limit),
            )
            for r in cursor.fetchall():
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                results.append(
                    SearchResult(
                        source_file=r["file_id"],
                        section_label=r["section_label"],
                        content=r["content"],
                        score=1.0,
                        chunk_index=r["chunk_index"],
                        metadata=meta,
                    )
                )

        return results

    def get_stats(self) -> dict[str, Any]:
        """Return index statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM knowledge_files")
            total_files = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM knowledge_files WHERE status = 'INDEXED'")
            indexed_files = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM knowledge_chunks")
            total_chunks = cursor.fetchone()[0]

            cursor.execute("SELECT MAX(indexed_at) FROM knowledge_files")
            last_indexed = cursor.fetchone()[0]

            return {
                "total_files": total_files,
                "indexed_files": indexed_files,
                "total_chunks": total_chunks,
                "last_indexed_at": last_indexed,
            }
