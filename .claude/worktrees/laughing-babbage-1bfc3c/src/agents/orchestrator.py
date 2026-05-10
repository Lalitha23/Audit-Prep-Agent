from .agent_base import AgentBase
from .coverage_agent import CoverageAgent
from ..retrieval.retrieval_interface import RetrievalInterface


class Orchestrator(AgentBase):
    def __init__(self, retrieval: RetrievalInterface):
        super().__init__(name="Orchestrator")
        self.coverage_agent = CoverageAgent(retrieval=retrieval)

    def run(self, query: str) -> dict:
        """Route the query and coordinate sub-agents."""
        coverage_result = self.coverage_agent.run(query)
        return {
            "orchestrator": self.name,
            "query": query,
            "coverage_analysis": coverage_result,
        }
