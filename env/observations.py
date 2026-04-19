"""Build observation packets for each actor each turn."""

from __future__ import annotations

from env.world_schema import (
    World, GameState, Actor, ActorObservation, PublicObservation,
    PrivateObservation, DiplomaticMessage, STATE_ACTIONS, NON_STATE_ACTIONS,
)


def build_public_observation(turn: int, game_state: GameState) -> PublicObservation:
    """Build the public observation visible to all actors."""
    return PublicObservation(
        turn=turn,
        public_news=list(game_state.public_news),
        alliances=list(game_state.alliances),
        sanctions=list(game_state.active_sanctions),
        regional_control=dict(game_state.regional_control),
        treaties=[
            {"parties": t.parties, "type": t.treaty_type, "turns_remaining": t.turns_remaining}
            for t in game_state.active_treaties
        ],
    )


def build_private_observation(
    actor_id: str,
    game_state: GameState,
    private_briefs: list[str],
    inbox: list[DiplomaticMessage],
) -> PrivateObservation:
    """Build the private observation for a specific actor."""
    actor_state = game_state.actor_states[actor_id]
    return PrivateObservation(
        private_brief=private_briefs,
        resource_update={
            "treasury": actor_state.treasury,
            "energy": actor_state.energy,
            "food": actor_state.food,
            "domestic_stability": actor_state.domestic_stability,
            "military_readiness": actor_state.military_readiness,
            "influence": actor_state.influence,
            "reputation": actor_state.reputation,
        },
        inbox_messages=inbox,
    )


def build_actor_observation(
    actor: Actor,
    turn: int,
    game_state: GameState,
    private_briefs: list[str],
    inbox: list[DiplomaticMessage],
    memory_summary: list[str],
) -> ActorObservation:
    """Build the full observation packet for one actor on one turn."""
    public_obs = build_public_observation(turn, game_state)
    private_obs = build_private_observation(actor.actor_id, game_state, private_briefs, inbox)

    legal_actions = STATE_ACTIONS if actor.actor_type == "state" else NON_STATE_ACTIONS

    return ActorObservation(
        actor_profile=actor.model_dump(),
        public_obs=public_obs,
        private_obs=private_obs,
        memory_summary=memory_summary,
        legal_actions=legal_actions,
    )
