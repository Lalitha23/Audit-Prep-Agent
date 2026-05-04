from abc import ABC, abstractmethod
from typing import Any


class AgentBase(ABC):
    def __init__(self, name: str, model: str = "claude-sonnet-4-6"):
        self.name = name
        self.model = model

    @abstractmethod
    def run(self, input_data: Any) -> Any:
        """Execute the agent's primary task."""
        ...
