"""
STEP 5: Vector Retrieval & Safeguards
Embeds user questions, queries ChromaDB, and discards weak matches to prevent hallucinations.
"""

from dataclasses import dataclass
from typing import List, Dict, Any

try:
    from v1_scratch.embeddings.embedder import EmbeddingModel
    from v1_scratch.retrieval.vector_store import VectorStore
except ImportError:
    from embeddings.embedder import EmbeddingModel
    from retrieval.vector_store import VectorStore


@dataclass
class RetrievalResult:
    """A retrieved document chunk with its source metadata and cosine distance score."""
    content: str
    metadata: Dict[str, Any]
    distance: float


class Retriever:
    """Embeds questions, searches ChromaDB, and applies distance threshold safeguards."""

    def __init__(
        self,
        embedder: EmbeddingModel,
        vector_store: VectorStore,
        top_k: int = 4,
        distance_threshold: float = 0.75
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.top_k = top_k
        self.distance_threshold = distance_threshold

    def retrieve(self, query: str) -> List[RetrievalResult]:
        """Embeds question and returns chunks that pass the relevance threshold."""
        query_embedding = self.embedder.embed_text(query)
        raw_results = self.vector_store.query(query_embedding, top_k=self.top_k)

        retrieved: List[RetrievalResult] = []
        if not raw_results or not raw_results.get("documents") or not raw_results["documents"][0]:
            return retrieved

        docs = raw_results["documents"][0]
        metas = raw_results["metadatas"][0]
        dists = raw_results["distances"][0]

        # Keep only chunks within acceptable distance threshold
        for doc, meta, dist in zip(docs, metas, dists):
            if dist <= self.distance_threshold:
                retrieved.append(RetrievalResult(content=doc, metadata=meta, distance=dist))

        return retrieved
