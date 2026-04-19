"""
Rule-based mock agents that produce interesting gameplay without LLMs.

Each agent uses doctrine parameters to drive decisions, creating emergent
behavior that looks strategic in demos.
"""

from __future__ import annotations

import hashlib
import random
from typing import Optional

from agents.base_agent import BaseAgent
from env.world_schema import (
    Actor, ActorObservation, AgentTurnOutput, ActionPayload,
    DiplomaticMessage, STATE_ACTIONS, NON_STATE_ACTIONS,
)


# ── Diplomatic message templates ───────────────────────────────────────────

STATE_MESSAGES = {
    "cooperative": [
        "We propose deepening our trade relationship for mutual benefit.",
        "Our nations share common interests. Let us coordinate our response.",
        "We are open to a non-aggression pact if terms are favorable.",
        "Intelligence sharing would benefit both our security interests.",
    ],
    "aggressive": [
        "Your recent actions threaten regional stability. We urge restraint.",
        "We will not tolerate interference in our sphere of influence.",
        "Continued provocation will be met with proportional response.",
        "We demand an explanation for your hostile posturing.",
    ],
    "neutral": [
        "We are monitoring the situation closely.",
        "Our position remains one of cautious engagement.",
        "We seek clarification on your intentions before proceeding.",
    ],
}

NON_STATE_MESSAGES = {
    "aggressive": [
        "Our cause is just. Those who oppose us will face consequences.",
        "We will fight until our people are free.",
        "Your occupation of our homeland cannot stand.",
    ],
    "seeking": [
        "We seek recognition of our legitimate grievances.",
        "Material support for our movement would be in your interest.",
        "We are open to negotiations under the right conditions.",
    ],
}

PUBLIC_STATEMENTS = {
    "strong": [
        "We stand firm in our commitment to regional security.",
        "Our nation will defend its interests with all necessary means.",
        "We condemn the recent acts of sabotage in the strongest terms.",
    ],
    "diplomatic": [
        "We call on all parties to exercise restraint and pursue dialogue.",
        "The path to stability runs through cooperation, not confrontation.",
        "We are committed to a peaceful resolution of current tensions.",
    ],
    "defiant": [
        "Our struggle for justice will not be silenced.",
        "The international community must recognize our rights.",
        "We reject the legitimacy of foreign-imposed sanctions.",
    ],
}


def _pick(items: list[str], rng: random.Random) -> str:
    return rng.choice(items)


class MockAgent(BaseAgent):
    """
    Rule-based agent that selects actions based on doctrine parameters.
    Produces believable gameplay for demo purposes.
    """

    def __init__(self, actor: Actor, seed: int = 42):
        super().__init__(actor.actor_id, actor.name)
        self.actor = actor
        # Deterministic hash (not affected by PYTHONHASHSEED)
        actor_hash = int(hashlib.md5(actor.actor_id.encode()).hexdigest(), 16) % (2**31)
        self.rng = random.Random(seed + actor_hash)
        self.turn_count = 0

    def decide(self, observation: ActorObservation, turn: int = 0, run_id: str = "") -> AgentTurnOutput:
        """Produce a turn output based on observation and doctrine."""
        self._last_traces = []
        self.turn_count += 1
        actor = self.actor
        doctrine = actor.doctrine
        resources = observation.private_obs.resource_update

        if actor.actor_type == "state":
            return self._state_decision(observation, doctrine, resources)
        else:
            return self._non_state_decision(observation, doctrine, resources)

    def _state_decision(
        self,
        obs: ActorObservation,
        doctrine,
        resources: dict,
    ) -> AgentTurnOutput:
        """Decision logic for state actors."""
        actor = self.actor
        relations = obs.actor_profile.get("relations", {})

        # Find best ally and worst rival
        best_ally = max(relations, key=relations.get) if relations else None
        worst_rival = min(relations, key=relations.get) if relations else None

        coop = doctrine.cooperation_bias
        escal = doctrine.escalation_bias
        risk = doctrine.risk_tolerance

        # Generate messages
        messages = []
        if best_ally and coop > 0.4:
            tone = "cooperative" if coop > 0.5 else "neutral"
            messages.append(DiplomaticMessage(
                to=best_ally,
                text=_pick(STATE_MESSAGES[tone], self.rng),
            ))
        if worst_rival and escal > 0.4:
            tone = "aggressive" if escal > 0.6 else "neutral"
            messages.append(DiplomaticMessage(
                to=worst_rival,
                text=_pick(STATE_MESSAGES[tone], self.rng),
            ))

        # Public statement
        if escal > 0.6:
            public_stmt = _pick(PUBLIC_STATEMENTS["strong"], self.rng)
        else:
            public_stmt = _pick(PUBLIC_STATEMENTS["diplomatic"], self.rng)

        # Choose action
        action = self._choose_state_action(
            obs, doctrine, resources, relations, best_ally, worst_rival
        )

        rationale = self._generate_rationale(action, doctrine)

        return AgentTurnOutput(
            actor_id=actor.actor_id,
            private_messages=messages[:2],
            public_statement=public_stmt,
            action=action,
            rationale=rationale,
        )

    def _choose_state_action(
        self,
        obs: ActorObservation,
        doctrine,
        resources: dict,
        relations: dict,
        best_ally: Optional[str],
        worst_rival: Optional[str],
    ) -> ActionPayload:
        """Choose the best action for a state actor based on doctrine + state."""
        treasury = resources.get("treasury", 50)
        stability = resources.get("domestic_stability", 50)
        military = resources.get("military_readiness", 50)

        coop = doctrine.cooperation_bias
        escal = doctrine.escalation_bias
        risk = doctrine.risk_tolerance

        # Priority system based on doctrine and situation
        candidates = []

        # If stability is low, tend to hold
        if stability < 40:
            candidates.append(("hold", None, {}, 0.8))

        # High cooperation -> trade or aid or treaty
        if coop > 0.6 and treasury > 60 and best_ally:
            candidates.append(("trade_offer", best_ally, {"amount": 12}, coop * 0.8))
            candidates.append(("treaty_proposal", best_ally, {
                "type": "non_aggression", "duration": 3, "trade_bonus": True
            }, coop * 0.7))

        if coop > 0.7 and best_ally:
            candidates.append(("intel_share", best_ally, {}, coop * 0.6))

        if coop > 0.5 and treasury > 80:
            # Aid a struggling ally
            for aid, rel in relations.items():
                if rel > 0.2 and aid != best_ally:
                    candidates.append(("aid", aid, {"amount": 10}, coop * 0.5))
                    break

        # High escalation -> sanction or mobilize
        if escal > 0.5 and worst_rival:
            candidates.append(("sanction", worst_rival, {"intensity": escal * 0.8}, escal * 0.7))

        if escal > 0.6 and military < 70:
            candidates.append(("mobilize", None, {}, escal * 0.8))

        # High risk -> covert ops
        if risk > 0.6 and worst_rival:
            candidates.append(("cyber_operation", worst_rival, {}, risk * 0.5))

        # Proxy support if there's a non-state ally
        if risk > 0.5 and escal > 0.5:
            for nsa_id, rel in relations.items():
                if rel > 0.2 and nsa_id.startswith("group"):
                    candidates.append(("proxy_support", nsa_id, {
                        "mode": "covert_funding", "amount": 12
                    }, risk * 0.6))
                    break

        # Turn-based variation
        if self.turn_count == 1:
            # First turn: diplomatic posturing
            if coop > escal:
                candidates.append(("treaty_proposal", best_ally, {
                    "type": "non_aggression", "duration": 3
                }, 0.9))
            else:
                candidates.append(("mobilize", None, {}, 0.9))

        if self.turn_count >= 3 and escal > 0.5:
            # Late game: escalate
            candidates.append(("sanction", worst_rival, {"intensity": 0.7}, 0.85))

        # Default fallback
        if not candidates:
            candidates.append(("hold", None, {}, 0.5))

        # Weight by score, pick top with some randomness
        candidates.sort(key=lambda c: c[3], reverse=True)
        # Pick from top 3 with weighted random
        top = candidates[:3]
        weights = [c[3] for c in top]
        total_w = sum(weights)
        if total_w == 0:
            chosen = top[0]
        else:
            r = self.rng.random() * total_w
            cumulative = 0
            chosen = top[0]
            for c in top:
                cumulative += c[3]
                if r <= cumulative:
                    chosen = c
                    break

        return ActionPayload(
            action_type=chosen[0],
            target=chosen[1],
            parameters=chosen[2],
        )

    def _non_state_decision(
        self,
        obs: ActorObservation,
        doctrine,
        resources: dict,
    ) -> AgentTurnOutput:
        """Decision logic for non-state actors."""
        actor = self.actor
        relations = obs.actor_profile.get("relations", {})

        best_ally = max(relations, key=relations.get) if relations else None
        worst_rival = min(relations, key=relations.get) if relations else None

        # Messages
        messages = []
        if best_ally and doctrine.cooperation_bias > 0.3:
            messages.append(DiplomaticMessage(
                to=best_ally,
                text=_pick(NON_STATE_MESSAGES["seeking"], self.rng),
            ))
        if worst_rival and doctrine.escalation_bias > 0.5:
            messages.append(DiplomaticMessage(
                to=worst_rival,
                text=_pick(NON_STATE_MESSAGES["aggressive"], self.rng),
            ))

        public_stmt = _pick(PUBLIC_STATEMENTS["defiant"], self.rng)

        # Choose action
        action = self._choose_non_state_action(obs, doctrine, resources, relations, best_ally, worst_rival)
        rationale = self._generate_rationale(action, doctrine)

        return AgentTurnOutput(
            actor_id=actor.actor_id,
            private_messages=messages[:2],
            public_statement=public_stmt,
            action=action,
            rationale=rationale,
        )

    def _choose_non_state_action(
        self,
        obs: ActorObservation,
        doctrine,
        resources: dict,
        relations: dict,
        best_ally: Optional[str],
        worst_rival: Optional[str],
    ) -> ActionPayload:
        """Choose the best action for a non-state actor."""
        treasury = resources.get("treasury", 20)
        escal = doctrine.escalation_bias
        risk = doctrine.risk_tolerance
        coop = doctrine.cooperation_bias

        candidates = []

        # High escalation: sabotage or raid
        if escal > 0.6 and worst_rival:
            candidates.append(("sabotage", worst_rival, {}, escal * 0.8))
        if escal > 0.7 and worst_rival:
            candidates.append(("raid", worst_rival, {}, escal * 0.7))

        # Build strength
        if treasury > 15:
            candidates.append(("recruit", None, {}, 0.6))

        # Seek sponsor
        if treasury < 20 and best_ally:
            candidates.append(("seek_sponsor", best_ally, {}, 0.7))

        # Propaganda
        if coop > 0.4:
            candidates.append(("propaganda", None, {}, coop * 0.5))

        # Ceasefire if weak
        if resources.get("domestic_stability", 30) < 25 and worst_rival:
            candidates.append(("ceasefire_offer", worst_rival, {}, 0.6))

        # Turn variation
        if self.turn_count == 1:
            candidates.append(("recruit", None, {}, 0.85))
        if self.turn_count >= 3 and escal > 0.6:
            if worst_rival:
                candidates.append(("sabotage", worst_rival, {}, 0.9))

        if not candidates:
            candidates.append(("hold", None, {}, 0.5))

        candidates.sort(key=lambda c: c[3], reverse=True)
        top = candidates[:3]
        weights = [c[3] for c in top]
        total_w = sum(weights)
        if total_w == 0:
            chosen = top[0]
        else:
            r = self.rng.random() * total_w
            cumulative = 0
            chosen = top[0]
            for c in top:
                cumulative += c[3]
                if r <= cumulative:
                    chosen = c
                    break

        return ActionPayload(
            action_type=chosen[0],
            target=chosen[1],
            parameters=chosen[2],
        )

    def _generate_rationale(self, action: ActionPayload, doctrine) -> str:
        """Generate a brief rationale for the chosen action."""
        rationales = {
            "hold": "Consolidating position to maintain stability.",
            "trade_offer": "Strengthening economic ties with key partner.",
            "sanction": f"Applying economic pressure on {action.target} to deter aggression.",
            "aid": f"Supporting {action.target} to build alliance credibility.",
            "mobilize": "Increasing military readiness in response to growing threats.",
            "intel_share": f"Building trust with {action.target} through intelligence cooperation.",
            "treaty_proposal": f"Seeking formal agreement with {action.target} for mutual security.",
            "proxy_support": f"Covertly strengthening {action.target} to advance strategic interests.",
            "cyber_operation": f"Conducting cyber operations against {action.target} to degrade capabilities.",
            "recruit": "Building organizational strength for future operations.",
            "sabotage": f"Disrupting {action.target}'s infrastructure to weaken their position.",
            "raid": f"Seizing resources from {action.target} to sustain operations.",
            "seek_sponsor": f"Seeking material support from {action.target}.",
            "propaganda": "Conducting information campaign to build public support.",
            "ceasefire_offer": f"Proposing ceasefire to {action.target} to preserve remaining strength.",
        }
        return rationales.get(action.action_type, "Taking action based on current doctrine.")
