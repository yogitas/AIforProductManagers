"""
STEP 4: Vector Database (ChromaDB)
Stores chunks and their vector embeddings locally on disk, and runs fast cosine similarity searches.
"""

import os
from typing import List, Dict, Any
import chromadb

try:
    from v1_scratch.ingestion.chunker import TextChunk
except ImportError:
    from ingestion.chunker import TextChunk


class VectorStore:
    """Manages local ChromaDB collection storage and vector queries."""

    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "jira_docs"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: List[TextChunk], embeddings: List[List[float]]) -> None:
        """Saves text chunks, their vector embeddings, and metadata into ChromaDB."""
        if not chunks:
            return

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        try:
            self.collection.delete(ids=ids)
        except Exception:
            pass

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    def query(self, query_embedding: List[float], top_k: int = 4) -> Dict[str, Any]:
        """Finds top_k nearest chunks matching the query embedding."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        return results

    def reset_collection(self) -> None:
        """Clears the collection for fresh re-indexing."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception:
            pass
