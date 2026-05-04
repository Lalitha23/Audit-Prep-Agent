from .agent_base import AgentBase
from ..retrieval.retrieval_interface import RetrievalInterface


class CoverageAgent(AgentBase):
    def __init__(self, retrieval: RetrievalInterface):
        super().__init__(name="CoverageAgent")
        self.retrieval = retrieval

    def run(self, query: str) -> dict:
        """Retrieve relevant controls and identify coverage gaps."""
        results = self.retrieval.query(query, top_k=5)
        return {
            "agent": self.name,
            "query": query,
            "retrieved_chunks": results,
            "gaps": [],  # populated by LLM call in subsequent iterations
        }
