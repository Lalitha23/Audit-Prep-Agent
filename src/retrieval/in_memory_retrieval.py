import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from .retrieval_interface import RetrievalEngine


def _load_env() -> None:
    """Walk up from this file looking for .env; also resolves git worktree roots."""
    search = Path(__file__).resolve().parent
    for _ in range(8):
        if (search / ".env").exists():
            load_dotenv(search / ".env", override=False)
            return
        git = search / ".git"
        if git.is_file():
            # worktree: .git is a file like "gitdir: /repo/.git/worktrees/name"
            # Three .parent calls: worktrees/name -> worktrees -> .git -> repo root
            gitdir = Path(git.read_text().split("gitdir:")[1].strip())
            real_root = gitdir.parent.parent.parent
            if (real_root / ".env").exists():
                load_dotenv(real_root / ".env", override=False)
            return
        if git.is_dir():
            if (search / ".env").exists():
                load_dotenv(search / ".env", override=False)
            return
        search = search.parent


_load_env()

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_EMBEDDINGS = _BASE_DIR / "data" / "embeddings" / "policy_embeddings.json"


def cosine_similarity(matrix: np.ndarray, query_vec: np.ndarray) -> np.ndarray:
    """Cosine similarity between *query_vec* and every row of *matrix*.

    Args:
        matrix:    (N, D) float32 array of stored embedding vectors.
        query_vec: (D,)   float32 query embedding.

    Returns:
        (N,) array of similarity scores in [-1, 1].
    """
    row_norms   = np.linalg.norm(matrix, axis=1)           # (N,)
    query_norm  = np.linalg.norm(query_vec)                 # scalar
    dot_products = matrix @ query_vec                       # (N,)
    return dot_products / (row_norms * query_norm + 1e-9)


class InMemoryRetrieval(RetrievalEngine):
    """Retrieval engine that holds all embeddings in RAM.

    Loads pre-computed embeddings from *embeddings_path* on construction,
    then answers queries by embedding the query string with OpenAI and
    ranking stored chunks by cosine similarity.

    Args:
        embeddings_path: Path to policy_embeddings.json produced by
                         scripts/generate_embeddings.py.  Defaults to
                         data/embeddings/policy_embeddings.json.
        model:           OpenAI embedding model for query embedding.
                         Must match the model used to generate stored vectors.

    Examples:
        >>> engine = InMemoryRetrieval()
        >>> results = engine.retrieve("multifactor authentication", top_k=3)
        >>> results[0]["score"] > 0.5
        True
        >>> "source" in results[0]
        True
    """

    def __init__(
        self,
        embeddings_path: Optional[Path] = None,
        model: str = "text-embedding-3-small",
    ) -> None:
        path = Path(embeddings_path) if embeddings_path else _DEFAULT_EMBEDDINGS
        if not path.exists():
            raise FileNotFoundError(
                f"Embeddings file not found: {path}\n"
                "Run scripts/generate_embeddings.py first."
            )

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Add it to your .env file."
            )

        self._client = OpenAI(api_key=api_key)
        self._model  = model

        raw = json.loads(path.read_text())
        # Support both envelope format {"metadata":…, "chunks":[…]} and legacy flat list
        chunks: List[Dict] = raw["chunks"] if isinstance(raw, dict) and "chunks" in raw else raw

        self._chunks: List[Dict] = chunks
        self._matrix = np.array(
            [c["embedding"] for c in chunks], dtype=np.float32
        )  # (N, 1536)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        context: Optional[Dict] = None,
    ) -> List[Dict]:
        """Embed *query* and return the top_k most similar policy chunks.

        Args:
            query:   Natural-language question or keyword string.
            top_k:   Number of results to return.
            context: Reserved for future filter/re-rank extensions.

        Returns:
            List of result dicts sorted by cosine similarity descending.
            Each dict has: chunk_id, text, score, source, entities.
        """
        response = self._client.embeddings.create(input=query, model=self._model)
        query_vec = np.array(response.data[0].embedding, dtype=np.float32)

        scores = cosine_similarity(self._matrix, query_vec)  # (N,)
        top_indices = np.argsort(scores)[::-1][:top_k]

        return [
            {
                "chunk_id": self._chunks[i].get("chunk_id", ""),
                "text":     self._chunks[i].get("text", ""),
                "score":    round(float(scores[i]), 6),
                "source":   self._chunks[i].get("source", ""),
                "entities": self._chunks[i].get("entities", {}),
            }
            for i in top_indices
        ]
