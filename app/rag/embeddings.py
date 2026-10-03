"""Embedding service supporting SentenceTransformers with resilient fallbacks."""

from typing import List
import numpy as np
from app.utils.config import settings
from app.utils.logging import logger


class EmbeddingService:
    """Manages text embedding generation using SentenceTransformers with fallback."""

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None
        self._dimension = 384  # default all-MiniLM-L6-v2 dimension

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading SentenceTransformer model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}). Using scikit-learn/hash vector fallback.")
                self._model = "fallback"
        return self._model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a list of strings."""
        if not texts:
            return []

        model = self._get_model()
        if model != "fallback":
            try:
                embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception as e:
                logger.warning(f"SentenceTransformer encoding failed: {e}. Falling back.")

        # Resilient fallback: normalized deterministic frequency vectors
        return [self._fallback_embed(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding vector for a single query string."""
        return self.embed_texts([query])[0]

    def _fallback_embed(self, text: str) -> List[float]:
        """Deterministic 384-dimensional hashing embedding for zero-dependency test scenarios."""
        vec = np.zeros(self._dimension, dtype=np.float32)
        words = text.lower().split()
        if not words:
            return vec.tolist()

        for word in words:
            h = hash(word) % self._dimension
            vec[h] += 1.0

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


embedding_service = EmbeddingService()
