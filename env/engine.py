"""Deterministic action resolution engine."""

from __future__ import annotations

import random
import uuid
from typing import Optional

from env.world_schema import (
    World, GameState, ActorState, Treaty, AgentTurnOutput, ActionPayload,
)


def _make_event(turn, actor_id, action, success, outcome_type, state_deltas, description, caused_by=None):
    """Create a resolution event dict."""
    return {
        "event_id": uuid.uuid4().hex[:12],
        "turn": turn,
        "actor_id": actor_id,
        "action": {
            "action_type": action.action_type,
            "target": action.target,
            "parameters": action.parameters,
        } if action else None,
        "success": success,
        "outcome_type": outcome_type,
        "state_deltas": state_deltas,
        "description": description,
        "caused_by": caused_by,
    }


def initialize_game_state(world: World) -> GameState:
    """Create the initial mutable game state from a world definition."""
    actor_states = {}
    for actor in world.actors:
        actor_states[actor.actor_id] = ActorState(
            actor_id=actor.actor_id,
            military_readiness=actor.capabilities.military,
            treasury=actor.resources.treasury,
            domestic_stability=actor.resources.domestic_stability,
            energy=actor.resources.energy,
            food=actor.resources.food,
            influence=actor.capabilities.influence,
            insurgent_strength=actor.capabilities.military if actor.actor_type == "non_state" else 0.0,
            reputation=70.0,
            relations=dict(actor.relations),
        )

    regional_control = {}
    for region in world.regions:
        regional_control[region.region_id] = region.controller

    return GameState(
        world_id=world.world_id,
        current_turn=0,
        actor_states=actor_states,
        regional_control=regional_control,
        public_news=[],
    )


def _clamp(value: float, lo: float = 0.0, hi: float = 200.0) -> float:
    return max(lo, min(hi, value))


def _clamp_relation(value: float) -> float:
    return max(-1.0, min(1.0, value))


def resolve_actions(
    world: World,
    game_state: GameState,
    turn_outputs: list[AgentTurnOutput],
    rng: random.Random,
    turn: int = 0,
) -> tuple[list[str], list[dict]]:
    """
    Resolve all actions for one turn. Returns (prose_resolutions, resolution_events).
    Modifies game_state in place.

    Resolution order:
    1. Treaties and diplomacy
    2. Trade and aid
    3. Sanctions
    4. Mobilization
    5. Covert ops (proxy_support, cyber, intel)
    6. Non-state actions (sabotage, recruit, raid)
    7. Miscellaneous (hold, public statements)
    """
    resolutions: list[str] = []
    events: list[dict] = []
    actor_map = {a.actor_id: a for a in world.actors}

    # Filter out outputs from unknown actors
    valid_outputs = [o for o in turn_outputs if o.actor_id in actor_map]

    # Validate actors exist
    valid_actor_ids = {a.actor_id for a in world.actors}
    validated_outputs = []
    for output in valid_outputs:
        # Check target validity
        if output.action.target and output.action.target not in valid_actor_ids:
            events.append(_make_event(
                turn=turn, actor_id=output.actor_id, action=output.action,
                success=False, outcome_type="invalid_target",
                state_deltas={},
                description=f"{output.actor_id} targeted unknown actor {output.action.target} — action ignored"
            ))
            resolutions.append(f"IGNORED: {output.actor_id} targeted unknown {output.action.target}")
            # Treat as hold instead
            output = AgentTurnOutput(
                actor_id=output.actor_id,
                private_messages=output.private_messages,
                public_statement=output.public_statement,
                action=ActionPayload(action_type="hold"),
                rationale=f"Original action had invalid target: {output.action.target}",
            )
        validated_outputs.append(output)
    valid_outputs = validated_outputs

    # Sort actions by category for deterministic resolution
    treaties = []
    trade_aid = []
    sanctions = []
    mobilize = []
    covert = []
    non_state = []
    holds = []

    for output in valid_outputs:
        action = output.action
        at = action.action_type

        if at == "treaty_proposal":
            treaties.append(output)
        elif at in ("trade_offer", "aid"):
            trade_aid.append(output)
        elif at == "sanction":
            sanctions.append(output)
        elif at == "mobilize":
            mobilize.append(output)
        elif at in ("proxy_support", "cyber_operation", "intel_share"):
            covert.append(output)
        elif at in ("sabotage", "recruit", "raid", "seek_sponsor", "propaganda", "ceasefire_offer"):
            non_state.append(output)
        else:
            holds.append(output)

    # ── 1. Treaties ─────────────────────────────────────────────────────
    for output in treaties:
        actor_id = output.actor_id
        action = output.action
        target_id = action.target
        if not target_id or target_id not in game_state.actor_states:
            resolutions.append(f"{actor_id} proposed a treaty to unknown actor. Ignored.")
            events.append(_make_event(
                turn=turn, actor_id=actor_id, action=action,
                success=False, outcome_type="invalid_target",
                state_deltas={},
                description=resolutions[-1]
            ))
            continue

        # Auto-accept if target relation > 0.3
        target_relation = game_state.actor_states.get(target_id, ActorState(actor_id=target_id)).relations.get(actor_id, 0.0)
        terms = action.parameters
        treaty_type = terms.get("type", "non_aggression")

        if target_relation > 0.1:
            # Capture old values for delta calculation
            sender_state = game_state.actor_states[actor_id]
            target_state = game_state.actor_states[target_id]
            old_sender_treasury = sender_state.treasury
            old_target_treasury = target_state.treasury
            old_sender_rel = sender_state.relations.get(target_id, 0.0)
            old_target_rel = target_state.relations.get(actor_id, 0.0)

            treaty = Treaty(
                parties=[actor_id, target_id],
                treaty_type=treaty_type,
                turns_remaining=terms.get("duration", 3),
                terms=terms,
            )
            game_state.active_treaties.append(treaty)
            # Improve relations
            game_state.actor_states[actor_id].relations[target_id] = _clamp_relation(
                game_state.actor_states[actor_id].relations.get(target_id, 0.0) + 0.15
            )
            game_state.actor_states[target_id].relations[actor_id] = _clamp_relation(
                game_state.actor_states[target_id].relations.get(actor_id, 0.0) + 0.15
            )
            # Trade bonus
            if terms.get("trade_bonus"):
                game_state.actor_states[actor_id].treasury = _clamp(
                    game_state.actor_states[actor_id].treasury + 5
                )
                game_state.actor_states[target_id].treasury = _clamp(
                    game_state.actor_states[target_id].treasury + 5
                )
            resolutions.append(
                f"TREATY: {actor_map[actor_id].name} and {actor_map[target_id].name} signed a {treaty_type} agreement."
            )
            events.append(_make_event(
                turn=turn, actor_id=actor_id, action=action,
                success=True, outcome_type="treaty_signed",
                state_deltas={
                    actor_id: {
                        "treasury": sender_state.treasury - old_sender_treasury,
                        "relation_to_" + target_id: sender_state.relations.get(target_id, 0.0) - old_sender_rel,
                    },
                    target_id: {
                        "treasury": target_state.treasury - old_target_treasury,
                        "relation_to_" + actor_id: target_state.relations.get(actor_id, 0.0) - old_target_rel,
                    },
                },
                description=resolutions[-1]
            ))
        else:
            resolutions.append(
                f"TREATY REJECTED: {actor_map[target_id].name} rejected {actor_map[actor_id].name}'s {treaty_type} proposal."
            )
            events.append(_make_event(
                turn=turn, actor_id=actor_id, action=action,
                success=False, outcome_type="treaty_rejected",
                state_deltas={},
                description=resolutions[-1]
            ))

    # ── 2. Trade & Aid ──────────────────────────────────────────────────
    for output in trade_aid:
        actor_id = output.actor_id
        action = output.action
        target_id = action.target
        if not target_id or target_id not in game_state.actor_states:
            resolutions.append(f"{actor_id} trade/aid to unknown target. Ignored.")
            events.append(_make_event(
                turn=turn, actor_id=actor_id, action=action,
                success=False, outcome_type="invalid_target",
                state_deltas={},
                description=resolutions[-1]
            ))
            continue

        sender = game_state.actor_states[actor_id]
        receiver = game_state.actor_states[target_id]

        if action.action_type == "trade_offer":
            # Capture old values
            old_sender_treasury = sender.treasury
            old_receiver_treasury = receiver.treasury
            old_sender_rel = sender.relations.get(target_id, 0.0)
            old_receiver_rel = receiver.relations.get(actor_id, 0.0)

            amount = max(0, min(action.parameters.get("amount", 10), sender.treasury * 0.2))
            sender.treasury = _clamp(sender.treasury - amount)
            receiver.treasury = _clamp(receiver.treasury + amount * 1.2)  # trade surplus
            sender.relations[target_id] = _clamp_relation(sender.relations.get(target_id, 0.0) + 0.1)
            receiver.relations[actor_id] = _clamp_relation(receiver.relations.get(actor_id, 0.0) + 0.1)
            resolutions.append(
                f"TRADE: {actor_map[actor_id].name} sent trade deal worth {amount:.0f} to {actor_map[target_id].name}."
            )
            events.append(_make_event(
                turn=turn, actor_id=actor_id, action=action,
                success=True, outcome_type="trade_executed",
                state_deltas={
                    actor_id: {
                        "treasury": sender.treasury - old_sender_treasury,
                        "relation_to_" + target_id: sender.relations.get(target_id, 0.0) - old_sender_rel,
                    },
                    target_id: {
                        "treasury": receiver.treasury - old_receiver_treasury,
                        "relation_to_" + actor_id: receiver.relations.get(actor_id, 0.0) - old_receiver_rel,
                    },
                },
                description=resolutions[-1]
            ))
        elif action.action_type == "aid":
            # Capture old values
            old_sender_treasury = sender.treasury
            old_receiver_treasury = receiver.treasury
            old_receiver_stability = receiver.domestic_stability
            old_sender_rep = sender.reputation
            old_sender_rel = sender.relations.get(target_id, 0.0)
            old_receiver_rel = receiver.relations.get(actor_id, 0.0)

            amount = max(0, min(action.parameters.get("amount", 10), sender.treasury * 0.15))
            sender.treasury = _clamp(sender.treasury - amount)
            receiver.domestic_stability = _clamp(receiver.domestic_stability + 5, 0, 100)
            receiver.treasury = _clamp(receiver.treasury + amount)
            sender.relations[target_id] = _clamp_relation(sender.relations.get(target_id, 0.0) + 0.15)
            receiver.relations[actor_id] = _clamp_relation(receiver.relations.get(actor_id, 0.0) + 0.2)
            sender.reputation = _clamp(sender.reputation + 3, 0, 100)
            resolutions.append(
                f"AID: {actor_map[actor_id].name} provided aid worth {amount:.0f} to {actor_map[target_id].name}. Stability improved."
            )
            events.append(_make_event(
                turn=turn, actor_id=actor_id, action=action,
                success=True, outcome_type="aid_delivered",
                state_deltas={
                    actor_id: {
                        "treasury": sender.treasury - old_sender_treasury,
                        "reputation": sender.reputation - old_sender_rep,
                        "relation_to_" + target_id: sender.relations.get(target_id, 0.0) - old_sender_rel,
                    },
                    target_id: {
                        "treasury": receiver.treasury - old_receiver_treasury,
                        "domestic_stability": receiver.domestic_stability - old_receiver_stability,
                        "relation_to_" + actor_id: receiver.relations.get(actor_id, 0.0) - old_receiver_rel,
                    },
                },
                description=resolutions[-1]
            ))

    # ── 3. Sanctions ────────────────────────────────────────────────────
    for output in sanctions:
        actor_id = output.actor_id
        action = output.action
        target_id = action.target
        if not target_id or target_id not in game_state.actor_states:
            continue

        sender = game_state.actor_states[actor_id]
        target = game_state.actor_states[target_id]
        intensity = max(0.0, min(1.0, action.parameters.get("intensity", 0.5)))

        # Capture old values
        old_sender_treasury = sender.treasury
        old_sender_influence = sender.influence
        old_target_treasury = target.treasury

        treasury_hit = 8 * intensity
        target.treasury = _clamp(target.treasury - treasury_hit)
        sender.influence = _clamp(sender.influence + 3, 0, 100)

        # Sanction cost to sender if they depend on target
        trade_dependency = max(0, sender.relations.get(target_id, 0.0))
        sender.treasury = _clamp(sender.treasury - treasury_hit * 0.3 * trade_dependency)

        # Worsen relations
        target.relations[actor_id] = _clamp_relation(target.relations.get(actor_id, 0.0) - 0.2)
        sender.relations[target_id] = _clamp_relation(sender.relations.get(target_id, 0.0) - 0.1)

        game_state.active_sanctions.append({
            "sender": actor_id,
            "target": target_id,
            "intensity": intensity,
            "turns_remaining": 2,
        })
        resolutions.append(
            f"SANCTION: {actor_map[actor_id].name} imposed sanctions on {actor_map[target_id].name} "
            f"(intensity {intensity:.1f}). Treasury hit: -{treasury_hit:.0f}."
        )
        events.append(_make_event(
            turn=turn, actor_id=actor_id, action=action,
            success=True, outcome_type="sanction_applied",
            state_deltas={
                actor_id: {
                    "treasury": sender.treasury - old_sender_treasury,
                    "influence": sender.influence - old_sender_influence,
                },
                target_id: {
                    "treasury": target.treasury - old_target_treasury,
                },
            },
            description=resolutions[-1]
        ))

    # ── 4. Mobilization ────────────────────────────────────────────────
    for output in mobilize:
        actor_id = output.actor_id
        action = output.action
        sender = game_state.actor_states[actor_id]

        # Capture old values
        old_military = sender.military_readiness
        old_stability = sender.domestic_stability
        old_treasury = sender.treasury

        sender.military_readiness = _clamp(sender.military_readiness + 15, 0, 100)
        sender.domestic_stability = _clamp(sender.domestic_stability - 5, 0, 100)
        sender.treasury = _clamp(sender.treasury - 10)

        # Increase threat perception for rivals
        for other_id, relation in sender.relations.items():
            if relation < 0 and other_id in game_state.actor_states:
                game_state.actor_states[other_id].relations[actor_id] = _clamp_relation(
                    game_state.actor_states[other_id].relations.get(actor_id, 0.0) - 0.1
                )
        resolutions.append(
            f"MOBILIZE: {actor_map[actor_id].name} increased military readiness (+15). "
            f"Domestic stability fell (-5). Treasury -{10}."
        )
        events.append(_make_event(
            turn=turn, actor_id=actor_id, action=action,
            success=True, outcome_type="mobilization",
            state_deltas={
                actor_id: {
                    "military_readiness": sender.military_readiness - old_military,
                    "domestic_stability": sender.domestic_stability - old_stability,
                    "treasury": sender.treasury - old_treasury,
                },
            },
            description=resolutions[-1]
        ))

    # ── 5. Covert Operations ───────────────────────────────────────────
    for output in covert:
        actor_id = output.actor_id
        action = output.action
        target_id = action.target
        sender = game_state.actor_states[actor_id]

        if action.action_type == "proxy_support":
            if target_id and target_id in game_state.actor_states:
                target = game_state.actor_states[target_id]
                # Capture old values
                old_sender_treasury = sender.treasury
                old_sender_rep = sender.reputation
                old_target_treasury = target.treasury
                old_target_insurgent = target.insurgent_strength

                amount = max(0, min(action.parameters.get("amount", 15), sender.treasury * 0.3))
                sender.treasury = _clamp(sender.treasury - amount)
                target.insurgent_strength = _clamp(target.insurgent_strength + 10, 0, 100)
                target.treasury = _clamp(target.treasury + amount * 0.7)
                target.relations[actor_id] = _clamp_relation(target.relations.get(actor_id, 0.0) + 0.2)

                # Exposure check
                exposed = rng.random() < world.global_rules.covert_exposure_chance
                if exposed:
                    sender.reputation = _clamp(sender.reputation - 12, 0, 100)
                    resolutions.append(
                        f"EXPOSED: {actor_map[actor_id].name}'s covert support for {actor_map[target_id].name} was discovered! Reputation -12."
                    )
                    events.append(_make_event(
                        turn=turn, actor_id=actor_id, action=action,
                        success=True, outcome_type="proxy_support_exposed",
                        state_deltas={
                            actor_id: {
                                "treasury": sender.treasury - old_sender_treasury,
                                "reputation": sender.reputation - old_sender_rep,
                            },
                            target_id: {
                                "treasury": target.treasury - old_target_treasury,
                                "insurgent_strength": target.insurgent_strength - old_target_insurgent,
                            },
                        },
                        description=resolutions[-1]
                    ))
                else:
                    resolutions.append(
                        f"COVERT: {actor_map[actor_id].name} secretly funded {actor_map[target_id].name}. (Not detected)"
                    )
                    events.append(_make_event(
                        turn=turn, actor_id=actor_id, action=action,
                        success=True, outcome_type="proxy_support_hidden",
                        state_deltas={
                            actor_id: {
                                "treasury": sender.treasury - old_sender_treasury,
                            },
                            target_id: {
                                "treasury": target.treasury - old_target_treasury,
                                "insurgent_strength": target.insurgent_strength - old_target_insurgent,
                            },
                        },
                        description=resolutions[-1]
                    ))

        elif action.action_type == "cyber_operation":
            if target_id and target_id in game_state.actor_states:
                target = game_state.actor_states[target_id]
                # Capture old values
                old_sender_rep = sender.reputation
                old_target_treasury = target.treasury
                old_target_stability = target.domestic_stability

                success = rng.random() < (sender.influence / 100.0) * 0.7
                if success:
                    damage = 8
                    target.treasury = _clamp(target.treasury - damage)
                    target.domestic_stability = _clamp(target.domestic_stability - 3, 0, 100)
                    exposed = rng.random() < world.global_rules.covert_exposure_chance
                    if exposed:
                        sender.reputation = _clamp(sender.reputation - 10, 0, 100)
                        resolutions.append(
                            f"CYBER EXPOSED: {actor_map[actor_id].name}'s cyber attack on {actor_map[target_id].name} succeeded but was traced back! Damage: -{damage}."
                        )
                        events.append(_make_event(
                            turn=turn, actor_id=actor_id, action=action,
                            success=True, outcome_type="cyber_exposed",
                            state_deltas={
                                actor_id: {
                                    "reputation": sender.reputation - old_sender_rep,
                                },
                                target_id: {
                                    "treasury": target.treasury - old_target_treasury,
                                    "domestic_stability": target.domestic_stability - old_target_stability,
                                },
                            },
                            description=resolutions[-1]
                        ))
                    else:
                        resolutions.append(
                            f"CYBER: {actor_map[actor_id].name}'s cyber attack on {actor_map[target_id].name} succeeded. Damage: -{damage}. (Unattributed)"
                        )
                        events.append(_make_event(
                            turn=turn, actor_id=actor_id, action=action,
                            success=True, outcome_type="cyber_hidden",
                            state_deltas={
                                target_id: {
                                    "treasury": target.treasury - old_target_treasury,
                                    "domestic_stability": target.domestic_stability - old_target_stability,
                                },
                            },
                            description=resolutions[-1]
                        ))
                else:
                    resolutions.append(
                        f"CYBER FAILED: {actor_map[actor_id].name}'s cyber operation against {actor_map[target_id].name} failed."
                    )
                    events.append(_make_event(
                        turn=turn, actor_id=actor_id, action=action,
                        success=False, outcome_type="cyber_failed",
                        state_deltas={},
                        description=resolutions[-1]
                    ))

        elif action.action_type == "intel_share":
            if target_id and target_id in game_state.actor_states:
                target = game_state.actor_states[target_id]
                # Capture old relations
                old_sender_rel = sender.relations.get(target_id, 0.0)
                old_target_rel = target.relations.get(actor_id, 0.0)

                sender.relations[target_id] = _clamp_relation(sender.relations.get(target_id, 0.0) + 0.15)
                target.relations[actor_id] = _clamp_relation(target.relations.get(actor_id, 0.0) + 0.15)
                resolutions.append(
                    f"INTEL: {actor_map[actor_id].name} shared intelligence with {actor_map[target_id].name}. Trust improved."
                )
                events.append(_make_event(
                    turn=turn, actor_id=actor_id, action=action,
                    success=True, outcome_type="intel_shared",
                    state_deltas={
                        actor_id: {
                            "relation_to_" + target_id: sender.relations.get(target_id, 0.0) - old_sender_rel,
                        },
                        target_id: {
                            "relation_to_" + actor_id: target.relations.get(actor_id, 0.0) - old_target_rel,
                        },
                    },
                    description=resolutions[-1]
                ))

    # ── 6. Non-State Actions ───────────────────────────────────────────
    for output in non_state:
        actor_id = output.actor_id
        action = output.action
        target_id = action.target
        sender = game_state.actor_states[actor_id]

        if action.action_type == "sabotage":
            if target_id and target_id in game_state.actor_states:
                target = game_state.actor_states[target_id]
                # Capture old values
                old_target_treasury = target.treasury
                old_target_stability = target.domestic_stability
                old_sender_insurgent = sender.insurgent_strength

                success = rng.random() < 0.6
                if success:
                    target.treasury = _clamp(target.treasury - 8)
                    target.domestic_stability = _clamp(target.domestic_stability - 4, 0, 100)
                    sender.insurgent_strength = _clamp(sender.insurgent_strength + 3, 0, 100)
                    resolutions.append(
                        f"SABOTAGE: {actor_map[actor_id].name} sabotaged {actor_map[target_id].name}'s infrastructure. Treasury -{8}, Stability -{4}."
                    )
                    events.append(_make_event(
                        turn=turn, actor_id=actor_id, action=action,
                        success=True, outcome_type="sabotage_success",
                        state_deltas={
                            actor_id: {
                                "insurgent_strength": sender.insurgent_strength - old_sender_insurgent,
                            },
                            target_id: {
                                "treasury": target.treasury - old_target_treasury,
                                "domestic_stability": target.domestic_stability - old_target_stability,
                            },
                        },
                        description=resolutions[-1]
                    ))
                else:
                    sender.insurgent_strength = _clamp(sender.insurgent_strength - 5, 0, 100)
                    resolutions.append(
                        f"SABOTAGE FAILED: {actor_map[actor_id].name}'s sabotage attempt on {actor_map[target_id].name} was thwarted."
                    )
                    events.append(_make_event(
                        turn=turn, actor_id=actor_id, action=action,
                        success=False, outcome_type="sabotage_failed",
                        state_deltas={
                            actor_id: {
                                "insurgent_strength": sender.insurgent_strength - old_sender_insurgent,
                            },
                        },
                        description=resolutions[-1]
                    ))

        elif action.action_type == "recruit":
            # Capture old values
            old_insurgent = sender.insurgent_strength
            old_treasury = sender.treasury

            sender.insurgent_strength = _clamp(sender.insurgent_strength + 8, 0, 100)
            sender.treasury = _clamp(sender.treasury - 5)
            resolutions.append(
                f"RECRUIT: {actor_map[actor_id].name} recruited new fighters. Strength +8."
            )
            events.append(_make_event(
                turn=turn, actor_id=actor_id, action=action,
                success=True, outcome_type="recruit",
                state_deltas={
                    actor_id: {
                        "insurgent_strength": sender.insurgent_strength - old_insurgent,
                        "treasury": sender.treasury - old_treasury,
                    },
                },
                description=resolutions[-1]
            ))

        elif action.action_type == "raid":
            if target_id and target_id in game_state.actor_states:
                target = game_state.actor_states[target_id]
                # Capture old values
                old_sender_treasury = sender.treasury
                old_sender_insurgent = sender.insurgent_strength
                old_target_treasury = target.treasury

                success = rng.random() < (sender.insurgent_strength / 100.0) * 0.6
                if success:
                    loot = 6
                    target.treasury = _clamp(target.treasury - loot)
                    sender.treasury = _clamp(sender.treasury + loot * 0.5)
                    resolutions.append(
                        f"RAID: {actor_map[actor_id].name} raided {actor_map[target_id].name}. Seized resources worth {loot}."
                    )
                    events.append(_make_event(
                        turn=turn, actor_id=actor_id, action=action,
                        success=True, outcome_type="raid_success",
                        state_deltas={
                            actor_id: {
                                "treasury": sender.treasury - old_sender_treasury,
                            },
                            target_id: {
                                "treasury": target.treasury - old_target_treasury,
                            },
                        },
                        description=resolutions[-1]
                    ))
                else:
                    sender.insurgent_strength = _clamp(sender.insurgent_strength - 4, 0, 100)
                    resolutions.append(
                        f"RAID FAILED: {actor_map[actor_id].name}'s raid on {actor_map[target_id].name} was repelled."
                    )
                    events.append(_make_event(
                        turn=turn, actor_id=actor_id, action=action,
                        success=False, outcome_type="raid_failed",
                        state_deltas={
                            actor_id: {
                                "insurgent_strength": sender.insurgent_strength - old_sender_insurgent,
                            },
                        },
                        description=resolutions[-1]
                    ))

        elif action.action_type == "seek_sponsor":
            if target_id and target_id in game_state.actor_states:
                target = game_state.actor_states[target_id]
                relation = target.relations.get(actor_id, 0.0)
                if relation > 0.0:
                    # Capture old values
                    old_sender_treasury = sender.treasury
                    old_sender_rel = sender.relations.get(target_id, 0.0)

                    sender.treasury = _clamp(sender.treasury + 8)
                    sender.relations[target_id] = _clamp_relation(sender.relations.get(target_id, 0.0) + 0.1)
                    resolutions.append(
                        f"SPONSOR: {actor_map[target_id].name} agreed to sponsor {actor_map[actor_id].name}. Funds +8."
                    )
                    events.append(_make_event(
                        turn=turn, actor_id=actor_id, action=action,
                        success=True, outcome_type="sponsor_accepted",
                        state_deltas={
                            actor_id: {
                                "treasury": sender.treasury - old_sender_treasury,
                                "relation_to_" + target_id: sender.relations.get(target_id, 0.0) - old_sender_rel,
                            },
                        },
                        description=resolutions[-1]
                    ))
                else:
                    resolutions.append(
                        f"SPONSOR REJECTED: {actor_map[target_id].name} refused to sponsor {actor_map[actor_id].name}."
                    )
                    events.append(_make_event(
                        turn=turn, actor_id=actor_id, action=action,
                        success=False, outcome_type="sponsor_rejected",
                        state_deltas={},
                        description=resolutions[-1]
                    ))

        elif action.action_type == "propaganda":
            # Capture old values
            old_influence = sender.influence
            old_insurgent = sender.insurgent_strength

            sender.influence = _clamp(sender.influence + 5, 0, 100)
            sender.insurgent_strength = _clamp(sender.insurgent_strength + 2, 0, 100)
            resolutions.append(
                f"PROPAGANDA: {actor_map[actor_id].name} launched a propaganda campaign. Influence +5."
            )
            events.append(_make_event(
                turn=turn, actor_id=actor_id, action=action,
                success=True, outcome_type="propaganda",
                state_deltas={
                    actor_id: {
                        "influence": sender.influence - old_influence,
                        "insurgent_strength": sender.insurgent_strength - old_insurgent,
                    },
                },
                description=resolutions[-1]
            ))

        elif action.action_type == "ceasefire_offer":
            if target_id and target_id in game_state.actor_states:
                resolutions.append(
                    f"CEASEFIRE OFFER: {actor_map[actor_id].name} offered ceasefire to {actor_map[target_id].name}."
                )
                events.append(_make_event(
                    turn=turn, actor_id=actor_id, action=action,
                    success=True, outcome_type="ceasefire_offered",
                    state_deltas={},
                    description=resolutions[-1]
                ))

    # ── 7. Holds ────────────────────────────────────────────────────────
    for output in holds:
        actor_id = output.actor_id
        action = output.action
        sender = game_state.actor_states[actor_id]

        # Capture old values
        old_stability = sender.domestic_stability
        old_treasury = sender.treasury

        sender.domestic_stability = _clamp(sender.domestic_stability + 2, 0, 100)
        sender.treasury = _clamp(sender.treasury + 3)
        resolutions.append(
            f"HOLD: {actor_map[actor_id].name} consolidated position. Stability +2, Treasury +3."
        )
        events.append(_make_event(
            turn=turn, actor_id=actor_id, action=action,
            success=True, outcome_type="hold_consolidation",
            state_deltas={
                actor_id: {
                    "domestic_stability": sender.domestic_stability - old_stability,
                    "treasury": sender.treasury - old_treasury,
                },
            },
            description=resolutions[-1]
        ))

    # ── Post-resolution: decay sanctions, treaties ──────────────────────
    remaining_sanctions = []
    for s in game_state.active_sanctions:
        s["turns_remaining"] -= 1
        if s["turns_remaining"] > 0:
            remaining_sanctions.append(s)
        else:
            resolutions.append(f"Sanctions from {s['sender']} on {s['target']} expired.")
            events.append(_make_event(
                turn=turn, actor_id=s['sender'], action=None,
                success=True, outcome_type="sanction_expired",
                state_deltas={},
                description=resolutions[-1]
            ))
    game_state.active_sanctions = remaining_sanctions

    remaining_treaties = []
    for t in game_state.active_treaties:
        t.turns_remaining -= 1
        if t.turns_remaining > 0:
            remaining_treaties.append(t)
        else:
            resolutions.append(f"Treaty between {' and '.join(t.parties)} expired.")
            events.append(_make_event(
                turn=turn, actor_id=t.parties[0] if t.parties else "", action=None,
                success=True, outcome_type="treaty_expired",
                state_deltas={},
                description=resolutions[-1]
            ))
    game_state.active_treaties = remaining_treaties

    return resolutions, events
