"""Memory management for agents across turns."""

from __future__ import annotations

from env.world_schema import ActorScore


class AgentMemory:
    """
    Manages turn-by-turn memory summaries for an agent.
    Keeps a rolling window to control token usage.
    """

    def __init__(self, actor_id: str, max_turns: int = 5):
        self.actor_id = actor_id
        self.max_turns = max_turns
        self.turn_summaries: list[list[str]] = []

    def add_summary(self, summary: list[str]) -> None:
        """Add a turn summary."""
        self.turn_summaries.append(summary)
        if len(self.turn_summaries) > self.max_turns:
            self.turn_summaries.pop(0)

    def get_context(self) -> list[str]:
        """Get flattened memory context for the agent."""
        context = []
        for summary in self.turn_summaries:
            context.extend(summary)
        return context

    def get_latest(self) -> list[str]:
        """Get the most recent turn summary."""
        if self.turn_summaries:
            return self.turn_summaries[-1]
        return []

    def clear(self) -> None:
        """Clear all memory."""
        self.turn_summaries = []
