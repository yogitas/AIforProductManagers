"""
STEP 2: Text Chunker
Splits long documents into smaller overlapping chunks so search is precise and fits LLM context limits.
"""

from typing import List, Dict, Any
from dataclasses import dataclass

try:
    from v1_scratch.ingestion.loader import Document
except ImportError:
    from ingestion.loader import Document


@dataclass
class TextChunk:
    """A single piece of text with its unique ID and metadata (source, chunk index)."""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]


class DocumentChunker:
    """Splits full documents into bite-sized overlapping text chunks."""

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: List[Document]) -> List[TextChunk]:
        """Splits a list of Documents into smaller TextChunks."""
        chunks: List[TextChunk] = []

        for doc in documents:
            doc_chunks = self._chunk_text(doc.page_content, doc.metadata)
            chunks.extend(doc_chunks)

        return chunks

    def _chunk_text(self, text: str, base_metadata: Dict[str, Any]) -> List[TextChunk]:
        """Splits text on paragraph boundaries while retaining overlap between chunks."""
        chunks: List[TextChunk] = []
        paragraphs = text.split("\n\n")
        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            else:
                if current_chunk:
                    chunk_id = f"{base_metadata['source']}_chunk_{chunk_index}"
                    meta = {**base_metadata, "chunk_index": chunk_index}
                    chunks.append(TextChunk(chunk_id=chunk_id, content=current_chunk, metadata=meta))
                    chunk_index += 1

                    # Keep last few characters as overlap for context continuity
                    overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                    overlap_text = current_chunk[overlap_start:]
                    current_chunk = f"{overlap_text}\n\n{para}" if overlap_text else para
                else:
                    # Paragraph is longer than chunk_size, split by characters
                    for i in range(0, len(para), self.chunk_size - self.chunk_overlap):
                        sub_para = para[i:i + self.chunk_size]
                        chunk_id = f"{base_metadata['source']}_chunk_{chunk_index}"
                        meta = {**base_metadata, "chunk_index": chunk_index}
                        chunks.append(TextChunk(chunk_id=chunk_id, content=sub_para, metadata=meta))
                        chunk_index += 1
                    current_chunk = ""

        if current_chunk:
            chunk_id = f"{base_metadata['source']}_chunk_{chunk_index}"
            meta = {**base_metadata, "chunk_index": chunk_index}
            chunks.append(TextChunk(chunk_id=chunk_id, content=current_chunk, metadata=meta))

        return chunks
