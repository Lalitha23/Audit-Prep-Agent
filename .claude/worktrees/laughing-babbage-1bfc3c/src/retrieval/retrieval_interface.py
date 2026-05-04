from abc import ABC, abstractmethod


class RetrievalInterface(ABC):
    @abstractmethod
    def add_documents(self, documents: list[dict]) -> None:
        """Ingest documents into the store. Each dict must have 'text' and 'metadata'."""
        ...

    @abstractmethod
    def query(self, query: str, top_k: int = 5) -> list[dict]:
        """Return the top_k most relevant chunks for the query."""
        ...
