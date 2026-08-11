"""
STEP 3: Vector Embeddings
Converts human text into 384-dimensional numbers using SentenceTransformers so similar meanings land close together.
"""

from typing import List
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """Generates local vector embeddings using open-source SentenceTransformers (all-MiniLM-L6-v2)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Loads the model only when first needed."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Converts a single text string into a 1D vector (list of 384 floats)."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Converts a list of text chunks into a list of vector embeddings."""
        if not texts:
            return []
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
