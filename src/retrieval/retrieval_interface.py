from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class RetrievalEngine(ABC):
    """Abstract base class for retrieval backends.

    All implementations must accept a natural-language query and return
    ranked chunks from the policy document corpus.
    """

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        context: Optional[Dict] = None,
    ) -> List[Dict]:
        """Return the top_k most relevant chunks for *query*.

        Args:
            query:   Natural-language search string.
            top_k:   Maximum number of results to return.
            context: Optional caller-supplied metadata (e.g. active control
                     IDs) that implementations may use to filter or re-rank.

        Returns:
            List of result dicts, each containing at minimum:
                chunk_id  – unique chunk identifier
                text      – chunk text content
                score     – cosine similarity in [0, 1]
                source    – originating PDF filename
                entities  – entity metadata dict
            Sorted by score descending.
        """
        ...
