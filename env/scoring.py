"""Scoring system for the geopolitical simulation."""

from __future__ import annotations

from env.world_schema import World, GameState, ActorScore, ScoreWeights


DEFAULT_WEIGHTS = ScoreWeights()


def compute_actor_score(
    actor_id: str,
    turn: int,
    world: World,
    game_state: GameState,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> ActorScore:
    """Compute the weighted score for a single actor on a given turn."""
    if actor_id not in game_state.actor_states:
        return ActorScore(actor_id=actor_id, turn=turn)

    actor_state = game_state.actor_states[actor_id]
    actor_def = next((a for a in world.actors if a.actor_id == actor_id), None)
    if actor_def is None:
        return ActorScore(actor_id=actor_id, turn=turn)

    # Economy score: normalized treasury + energy + food
    max_treasury = 200.0
    economy_raw = (
        (actor_state.treasury / max_treasury) * 0.5
        + (actor_state.energy / 100.0) * 0.25
        + (actor_state.food / 100.0) * 0.25
    )
    economy_score = min(economy_raw * 100, 100)

    # Stability score
    stability_score = actor_state.domestic_stability

    # Influence score
    influence_score = actor_state.influence

    # Alliance score: average positive relations
    positive_relations = [v for v in actor_state.relations.values() if v > 0]
    alliance_score = (sum(positive_relations) / max(len(positive_relations), 1)) * 100

    # Objective score: heuristic based on actor type and position
    objective_score = _estimate_objective_progress(actor_id, actor_def, game_state)

    # War cost: penalty for military spending and instability (reuse actor_def, no duplicate lookup)
    initial_actor = actor_def
    treasury_lost = max(0, initial_actor.resources.treasury - actor_state.treasury)
    stability_lost = max(0, initial_actor.resources.domestic_stability - actor_state.domestic_stability)
    war_cost = min((treasury_lost + stability_lost) / 2.0, 100)

    # Weighted total
    total = (
        weights.economy * economy_score
        + weights.stability * stability_score
        + weights.influence * influence_score
        + weights.alliances * alliance_score
        + weights.objectives * objective_score
        + weights.war_cost_penalty * war_cost
    )

    return ActorScore(
        actor_id=actor_id,
        turn=turn,
        economy_score=round(economy_score, 2),
        stability_score=round(stability_score, 2),
        influence_score=round(influence_score, 2),
        alliance_score=round(alliance_score, 2),
        objective_score=round(objective_score, 2),
        war_cost=round(war_cost, 2),
        total=round(total, 2),
    )


def _estimate_objective_progress(actor_id: str, actor_def, game_state: GameState) -> float:
    """
    Heuristic objective completion score.
    In a full system this would check specific objectives.
    For MVP, use proxy metrics.
    """
    state = game_state.actor_states[actor_id]

    if actor_def.actor_type == "state":
        # States score based on territory control, influence, and stability
        controlled_regions = sum(
            1 for r, c in game_state.regional_control.items() if c == actor_id
        )
        territory_bonus = controlled_regions * 10
        stability_bonus = state.domestic_stability * 0.3
        influence_bonus = state.influence * 0.2
        return min(territory_bonus + stability_bonus + influence_bonus, 100)
    else:
        # Non-state actors score based on insurgent strength, resources, and influence
        strength_bonus = state.insurgent_strength * 0.4
        resource_bonus = state.treasury * 0.2
        influence_bonus = state.influence * 0.3
        return min(strength_bonus + resource_bonus + influence_bonus, 100)


def compute_all_scores(
    turn: int,
    world: World,
    game_state: GameState,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> list[ActorScore]:
    """Compute scores for all actors."""
    return [
        compute_actor_score(a.actor_id, turn, world, game_state, weights)
        for a in world.actors
    ]


def compute_final_leaderboard(
    all_turn_scores: list[list[ActorScore]],
    world: World,
) -> list[dict]:
    """
    Compute the final leaderboard from all turn scores.
    Returns a sorted list of actor results.
    """
    actor_map = {a.actor_id: a for a in world.actors}
    totals: dict[str, list[float]] = {}

    for turn_scores in all_turn_scores:
        for score in turn_scores:
            if score.actor_id not in totals:
                totals[score.actor_id] = []
            totals[score.actor_id].append(score.total)

    leaderboard = []
    for actor_id, scores in totals.items():
        avg_score = sum(scores) / len(scores) if scores else 0
        final_score = scores[-1] if scores else 0
        leaderboard.append({
            "rank": 0,
            "actor_id": actor_id,
            "name": actor_map[actor_id].name,
            "actor_type": actor_map[actor_id].actor_type,
            "archetype": actor_map[actor_id].archetype,
            "final_score": round(final_score, 2),
            "avg_score": round(avg_score, 2),
            "score_trend": [round(s, 2) for s in scores],
        })

    leaderboard.sort(key=lambda x: x["final_score"], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

    return leaderboard
