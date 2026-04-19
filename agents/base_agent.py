"""Base agent interface for the geopolitical simulation."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

# Import with fallback since schema may be getting updated simultaneously
try:
    from env.world_schema import ActorObservation, AgentTurnOutput, LLMTrace
except ImportError:
    from env.world_schema import ActorObservation, AgentTurnOutput
    LLMTrace = None


class BaseAgent(ABC):
    """Abstract base class for all agent types."""

    def __init__(self, actor_id: str, actor_name: str):
        self.actor_id = actor_id
        self.actor_name = actor_name
        self._last_traces: list = []

    @abstractmethod
    def decide(self, observation: ActorObservation,
               turn: int = 0, run_id: str = "") -> AgentTurnOutput:
        """Given an observation, produce an action for this turn."""
        ...

    @property
    def agent_type(self) -> str:
        return self.__class__.__name__

    def get_last_traces(self) -> list:
        """Return LLMTrace objects from the most recent decide() call."""
        return self._last_traces

    def get_agent_metadata(self) -> dict:
        """Return agent config metadata for run registry."""
        return {
            "agent_type": self.agent_type,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
        }
