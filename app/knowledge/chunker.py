"""
Text chunking engine with sliding windows, overlap, and metadata preservation.
"""

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any
from app.knowledge.parsers import ParsedDocument


@dataclass
class DocumentChunk:
    """A searchable chunk of text extracted from a source document."""
    source_file: str  # Relative filename within Knowledge/
    chunk_index: int
    section_label: str  # "Page 1", "Sheet: Financials", etc.
    content: str
    content_hash: str
    char_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


class TextChunker:
    """Splits structured document sections into overlapping chunks."""

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.chunk_size = max(100, chunk_size)
        self.chunk_overlap = min(chunk_overlap, self.chunk_size // 2)

    def chunk_document(
        self,
        doc: ParsedDocument,
        relative_path: str,
    ) -> list[DocumentChunk]:
        """Convert a ParsedDocument into a list of DocumentChunks."""
        chunks: list[DocumentChunk] = []
        global_index = 0

        for section in doc.sections:
            text = section.content.strip()
            if not text:
                continue

            section_chunks = self._split_text(text)
            for chunk_text in section_chunks:
                h = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                chunks.append(
                    DocumentChunk(
                        source_file=relative_path,
                        chunk_index=global_index,
                        section_label=section.label,
                        content=chunk_text,
                        content_hash=h,
                        char_count=len(chunk_text),
                        metadata=section.metadata,
                    )
                )
                global_index += 1

        return chunks

    def chunk_text(
        self,
        text: str,
        source_file: str,
        section_label: str = "General",
        metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """Split a raw text string directly into DocumentChunks."""
        chunks: list[DocumentChunk] = []
        raw_chunks = self._split_text(text)
        for idx, ct in enumerate(raw_chunks):
            h = hashlib.sha256(ct.encode("utf-8")).hexdigest()
            chunks.append(
                DocumentChunk(
                    source_file=source_file,
                    chunk_index=idx,
                    section_label=section_label,
                    content=ct,
                    content_hash=h,
                    char_count=len(ct),
                    metadata=metadata or {},
                )
            )
        return chunks

    def _split_text(self, text: str) -> list[str]:
        """Split text cleanly respecting paragraph or sentence boundaries."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            if end >= text_len:
                chunks.append(text[start:].strip())
                break

            # Look for paragraph break
            cut = text.rfind("\n\n", start, end)
            if cut != -1 and cut > start + (self.chunk_size // 2):
                end = cut + 2
            else:
                # Look for sentence break
                cut = text.rfind(". ", start, end)
                if cut != -1 and cut > start + (self.chunk_size // 2):
                    end = cut + 2
                else:
                    # Look for newline
                    cut = text.rfind("\n", start, end)
                    if cut != -1 and cut > start + (self.chunk_size // 2):
                        end = cut + 1
                    else:
                        # Look for space
                        cut = text.rfind(" ", start, end)
                        if cut != -1 and cut > start + (self.chunk_size // 2):
                            end = cut + 1

            chunk_candidate = text[start:end].strip()
            if chunk_candidate:
                chunks.append(chunk_candidate)

            # Advance by chunk_size - overlap
            start = max(start + 1, end - self.chunk_overlap)

        return [c for c in chunks if c]
