from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class Agent(ABC):
    """Abstract base class for all agents in the audit-prep pipeline.

    Provides a shared decision log so every message processed by a subclass
    is traceable, and enforces a uniform process_message interface.

    Args:
        name:  Human-readable agent name used in log entries.
        role:  Short description of the agent's responsibility.
        tools: List of tool names the agent is authorised to use.
    """

    def __init__(self, name: str, role: str, tools: Optional[List[str]] = None) -> None:
        self.name  = name
        self.role  = role
        self.tools = tools or []
        self._log: List[Dict] = []

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def process_message(self, message: Dict) -> Dict:
        """Process an incoming message and return a structured response.

        Args:
            message: Dict containing at minimum a "content" key with the
                     natural-language or structured payload to process.

        Returns:
            A response dict whose shape is defined by each subclass.
        """
        ...

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def log_message(
        self,
        event: str,
        payload: Any,
        level: str = "info",
    ) -> None:
        """Append an entry to the agent's decision trail.

        Args:
            event:   Short label describing what happened (e.g. "retrieve",
                     "assess", "requery").
            payload: Arbitrary data to store alongside the event.
            level:   Severity level — "info", "warning", or "error".
        """
        self._log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent":     self.name,
            "level":     level,
            "event":     event,
            "payload":   payload,
        })

    def get_message_log(self) -> List[Dict]:
        """Return a copy of the agent's full decision log."""
        return list(self._log)
