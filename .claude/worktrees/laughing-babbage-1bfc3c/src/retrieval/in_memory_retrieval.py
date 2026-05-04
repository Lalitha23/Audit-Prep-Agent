import numpy as np
from .retrieval_interface import RetrievalInterface
from ..utils.embedding_generator import EmbeddingGenerator


class InMemoryRetrieval(RetrievalInterface):
    def __init__(self, embedding_generator: EmbeddingGenerator):
        self.embedding_generator = embedding_generator
        self._documents: list[dict] = []
        self._embeddings: np.ndarray | None = None

    def add_documents(self, documents: list[dict]) -> None:
        texts = [d["text"] for d in documents]
        embeddings = self.embedding_generator.embed_batch(texts)
        self._documents.extend(documents)
        new_matrix = np.array(embeddings)
        self._embeddings = (
            new_matrix
            if self._embeddings is None
            else np.vstack([self._embeddings, new_matrix])
        )

    def query(self, query: str, top_k: int = 5) -> list[dict]:
        if self._embeddings is None or len(self._documents) == 0:
            return []
        query_vec = np.array(self.embedding_generator.embed(query))
        scores = self._embeddings @ query_vec / (
            np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_vec) + 1e-9
        )
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            {**self._documents[i], "score": float(scores[i])}
            for i in top_indices
        ]
