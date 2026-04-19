"""
Turn runner: orchestrates the full simulation loop.

Turn protocol:
  Phase 0: World update (inject events, publish bulletin, generate briefs)
  Phase 1: Diplomacy (collect messages + public statements)
  Phase 2: Decision (collect structured actions)
  Phase 3: Adjudication (engine resolves all actions)
  Phase 4: Summary (score, state diff, memory)
"""

from __future__ import annotations

import json
import random
import time
import datetime
import platform
import hashlib
from pathlib import Path
from typing import Optional

from env.world_schema import (
    World, GameState, Actor, AgentTurnOutput, DiplomaticMessage,
    TurnRecord, ReplayLog, ActorScore,
)
from env.engine import initialize_game_state, resolve_actions
from env.observations import build_actor_observation
from env.scoring import compute_all_scores, compute_final_leaderboard
from agents.base_agent import BaseAgent
from agents.mock_agent import MockAgent


def _create_agent(
    actor: Actor,
    agent_type: str = "mock",
    seed: int = 42,
    llm_model: str = "big-pickle",
    llm_api_key: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_temperature: float = 0.7,
) -> BaseAgent:
    """Factory function to create the right agent type."""
    if agent_type == "llm":
        from agents.llm_agent import LLMAgent
        return LLMAgent(
            actor=actor,
            model=llm_model,
            api_key=llm_api_key,
            provider=llm_provider,
            temperature=llm_temperature,
        )
    else:
        return MockAgent(actor, seed=seed)


class SimulationRunner:
    """Runs a full geopolitical simulation."""

    def __init__(
        self,
        world: World,
        seed: int = 42,
        output_dir: Optional[str] = None,
        agent_type: str = "mock",
        llm_model: str = "big-pickle",
        llm_api_key: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_temperature: float = 0.7,
        # NEW parameters
        actor_agent_configs: Optional[dict] = None,
        run_id: Optional[str] = None,
        world_path: Optional[str] = None,
        on_turn_complete=None,  # callback(turn_number, turn_record_dict)
        llm_call_delay: float = 5.0,  # seconds between LLM calls to avoid free-tier rate limits
    ):
        self.world = world
        self.world_path = world_path
        self.on_turn_complete = on_turn_complete
        self.llm_call_delay = llm_call_delay
        self.original_seed = seed  # FIXED: store before consumption
        self.rng = random.Random(seed)
        self.game_state = initialize_game_state(world)
        self.output_dir = output_dir or "logs/replays"
        self.agent_type = agent_type
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.llm_provider = llm_provider
        self.llm_temperature = llm_temperature
        self.actor_agent_configs = actor_agent_configs or {}
        self.run_id = run_id or self._generate_run_id()
        self._start_time = datetime.datetime.utcnow().isoformat() + "Z"

        # Initialize agents — per-actor config overrides global defaults
        self.agents: dict[str, BaseAgent] = {}
        for actor in world.actors:
            override = self.actor_agent_configs.get(actor.actor_id, {})
            self.agents[actor.actor_id] = _create_agent(
                actor=actor,
                agent_type=override.get("agent_type", agent_type),
                seed=seed,
                llm_model=override.get("model", llm_model),
                llm_api_key=override.get("api_key", llm_api_key),
                llm_provider=override.get("provider", llm_provider),
                llm_temperature=override.get("temperature", llm_temperature),
            )

        # Track state
        self.actor_map: dict[str, Actor] = {a.actor_id: a for a in world.actors}
        self.memory: dict[str, list[str]] = {a.actor_id: [] for a in world.actors}
        self.all_turn_scores: list[list[ActorScore]] = []
        self.turn_records: list[TurnRecord] = []
        self.inbox: dict[str, list[DiplomaticMessage]] = {
            a.actor_id: [] for a in world.actors
        }

    def _generate_run_id(self) -> str:
        """Generate a unique run identifier."""
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{self.world.world_id}_{self.agent_type}_{self.original_seed}_{ts}"

    def _hash_scenario(self) -> str:
        """Hash the scenario file for reproducibility tracking."""
        if self.world_path:
            try:
                with open(self.world_path, "rb") as f:
                    return hashlib.sha256(f.read()).hexdigest()[:16]
            except Exception:
                pass
        return ""

    def _build_run_config(self) -> dict:
        """Build structured run configuration for replay metadata."""
        config = {
            "run_id": self.run_id,
            "scenario_path": self.world_path or "unknown",
            "scenario_hash": self._hash_scenario(),
            "seed": self.original_seed,
            "turn_limit": self.world.turn_limit,
            "agent_configs": [],
            "global_agent_type": self.agent_type,
            "global_model": self.llm_model if self.agent_type == "llm" else None,
            "global_temperature": self.llm_temperature if self.agent_type == "llm" else None,
            "started_at": self._start_time,
            "finished_at": datetime.datetime.utcnow().isoformat() + "Z",
            "engine_version": "1.0.0",
            "platform": platform.platform(),
        }
        for actor in self.world.actors:
            agent = self.agents[actor.actor_id]
            config["agent_configs"].append({
                "actor_id": actor.actor_id,
                "agent_type": getattr(agent, "agent_type", self.agent_type),
                "model": getattr(agent, "model", None),
                "provider": getattr(agent, "_provider_name", None),
                "temperature": getattr(agent, "temperature", None),
            })
        return config

    def run(self) -> ReplayLog:
        """Run the full simulation and return a replay log."""
        print(f"\n{'='*60}")
        print(f"  SIMULATION: {self.world.name}")
        print(f"  Run ID: {self.run_id}")
        print(f"  Actors: {len(self.world.actors)} | Regions: {len(self.world.regions)} | Turns: {self.world.turn_limit}")
        print(f"{'='*60}\n")

        for turn in range(1, self.world.turn_limit + 1):
            self.game_state.current_turn = turn
            record = self._run_turn(turn)
            self.turn_records.append(record)

            # Notify callback with completed turn data
            if self.on_turn_complete:
                try:
                    turn_data = record.model_dump() if hasattr(record, 'model_dump') else record
                    self.on_turn_complete(turn, turn_data)
                except Exception as e:
                    print(f"  [callback error] {e}")

        # Final leaderboard
        leaderboard = compute_final_leaderboard(self.all_turn_scores, self.world)

        print(f"\n{'='*60}")
        print("  FINAL LEADERBOARD")
        print(f"{'='*60}")
        for entry in leaderboard:
            medal = {1: ">>", 2: "> ", 3: "  "}.get(entry["rank"], "  ")
            print(f"  {medal} #{entry['rank']} {entry['name']:.<30} {entry['final_score']:.1f}")
        print()

        # Build replay
        replay = ReplayLog(
            world=self.world.model_dump(),
            turns=self.turn_records,
            final_scores=[s for s in leaderboard],
            metadata={
                "seed": self.original_seed,  # FIXED: was self.rng.getstate()[1][0]
                "agent_type": self.agent_type,
                "total_turns": self.world.turn_limit,
                "model": self.llm_model if self.agent_type == "llm" else None,
                "run_id": self.run_id,
            },
            run_config=self._build_run_config(),
        )

        # Save replay
        self._save_replay(replay)
        return replay

    def _run_turn(self, turn: int) -> TurnRecord:
        """Execute one full turn."""
        print(f"\n--- Turn {turn} ---")

        # ── Phase 0: World Update ───────────────────────────────────────
        public_news = self._inject_events(turn)
        self.game_state.public_news = public_news
        private_briefs = self._generate_briefs(turn)

        for news in public_news:
            print(f"  [NEWS] {news}")

        # ── Phase 1+2: Collect Agent Decisions ──────────────────────────
        turn_outputs: list[AgentTurnOutput] = []
        all_messages: list[dict] = []
        public_statements: dict[str, str] = {}
        turn_traces: list[dict] = []

        for actor in self.world.actors:
            actor_id = actor.actor_id
            agent = self.agents[actor_id]

            # Build observation
            obs = build_actor_observation(
                actor=actor,
                turn=turn,
                game_state=self.game_state,
                private_briefs=private_briefs.get(actor_id, []),
                inbox=self.inbox.get(actor_id, []),
                memory_summary=self.memory.get(actor_id, []),
            )

            # Get agent decision — try new signature first, fall back to old
            try:
                output = agent.decide(obs, turn=turn, run_id=self.run_id)
            except TypeError:
                output = agent.decide(obs)
            turn_outputs.append(output)

            # Collect traces (if the agent exposes them)
            if hasattr(agent, "get_last_traces"):
                try:
                    traces = agent.get_last_traces() or []
                    for tr in traces:
                        if hasattr(tr, "model_dump"):
                            turn_traces.append(tr.model_dump())
                        elif isinstance(tr, dict):
                            turn_traces.append(tr)
                except Exception:
                    pass

            # Rate-limit delay for LLM agents (only for free models)
            if self.agent_type == "llm" or actor_id in self.actor_agent_configs:
                FREE_MODELS = {"big-pickle", "gpt-5-nano", "nemotron-3-super-free", "minimax-m2.5-free"}
                model_used = self.actor_agent_configs.get(actor_id, {}).get("model", self.llm_model)
                if model_used in FREE_MODELS:
                    time.sleep(self.llm_call_delay)  # 5s for free tier
                else:
                    time.sleep(0.5)  # minimal delay for paid models

            # Collect messages for next turn's inboxes
            for msg in output.private_messages:
                all_messages.append({
                    "from": actor_id,
                    "to": msg.to,
                    "text": msg.text,
                })

            public_statements[actor_id] = output.public_statement

            print(f"  [{self.actor_map[actor_id].name}] Action: {output.action.action_type}"
                  f"{' -> ' + str(output.action.target) if output.action.target else ''}")

        # Route messages to inboxes for next turn
        self.inbox = {a.actor_id: [] for a in self.world.actors}
        for msg in all_messages:
            if msg["to"] in self.inbox:
                self.inbox[msg["to"]].append(
                    DiplomaticMessage(to=msg["from"], text=msg["text"])
                )

        # ── Phase 3: Adjudication ──────────────────────────────────────
        # Handle both old (list) and new (tuple) return formats from resolve_actions
        try:
            result = resolve_actions(
                self.world, self.game_state, turn_outputs, self.rng, turn=turn
            )
        except TypeError:
            result = resolve_actions(
                self.world, self.game_state, turn_outputs, self.rng
            )
        if isinstance(result, tuple):
            resolutions, resolution_events = result
        else:
            resolutions = result
            resolution_events = []

        for res in resolutions:
            print(f"  >> {res}")

        # Normalize resolution_events to list of dicts for schema compatibility
        normalized_events: list[dict] = []
        for ev in resolution_events:
            if hasattr(ev, "model_dump"):
                normalized_events.append(ev.model_dump())
            elif isinstance(ev, dict):
                normalized_events.append(ev)

        # ── Phase 4: Scoring & Summary ─────────────────────────────────
        scores = compute_all_scores(turn, self.world, self.game_state)
        self.all_turn_scores.append(scores)

        # Update memory
        for actor in self.world.actors:
            self.memory[actor.actor_id] = self._summarize_turn(
                actor.actor_id, turn, resolutions, scores
            )

        # Build state snapshot
        state_snapshot = {}
        for actor_id, actor_state in self.game_state.actor_states.items():
            state_snapshot[actor_id] = actor_state.model_dump()

        # Build turn record
        return TurnRecord(
            turn=turn,
            public_news=public_news,
            private_briefs=private_briefs,
            messages=all_messages,
            public_statements=public_statements,
            actions=[
                {
                    "actor_id": o.actor_id,
                    "actor_name": self.actor_map[o.actor_id].name,
                    "action_type": o.action.action_type,
                    "target": o.action.target,
                    "target_name": self.actor_map[o.action.target].name if o.action.target and o.action.target in self.actor_map else o.action.target,
                    "parameters": o.action.parameters,
                    "rationale": o.rationale,
                }
                for o in turn_outputs
            ],
            resolutions=resolutions,
            resolution_events=normalized_events,
            state_snapshot=state_snapshot,
            scores=[s.model_dump() for s in scores],
            traces=turn_traces,
            decision_scores=[],
        )

    def _inject_events(self, turn: int) -> list[str]:
        """Get public news for this turn from initial events + generated events."""
        news = []
        for event in self.world.initial_events:
            if event.turn == turn:
                news.append(event.public_text)

        # Generate dynamic news based on game state for turns without scripted events
        if not news and turn > 1:
            news.extend(self._generate_dynamic_news(turn))

        return news

    def _generate_dynamic_news(self, turn: int) -> list[str]:
        """Generate contextual news based on current game state."""
        news = []

        # Check for active sanctions
        if self.game_state.active_sanctions:
            s = self.game_state.active_sanctions[0]
            sender_name = self.actor_map[s["sender"]].name
            target_name = self.actor_map[s["target"]].name
            news.append(f"Ongoing sanctions by {sender_name} continue to strain {target_name}'s economy.")

        # Check for stability crises
        for actor_id, state in self.game_state.actor_states.items():
            if state.domestic_stability < 40:
                news.append(f"Reports of civil unrest in {self.actor_map[actor_id].name} as stability deteriorates.")
                break

        # Check for military buildups
        high_military = [
            aid for aid, s in self.game_state.actor_states.items()
            if s.military_readiness > 80
        ]
        if high_military:
            name = self.actor_map[high_military[0]].name
            news.append(f"Satellite imagery reveals significant military buildup by {name}.")

        # Check for treaties
        if self.game_state.active_treaties:
            t = self.game_state.active_treaties[-1]
            names = [self.actor_map[p].name for p in t.parties if p in self.actor_map]
            if len(names) >= 2:
                news.append(f"The {t.treaty_type} agreement between {names[0]} and {names[1]} remains in effect.")

        if not news:
            news.append(f"Tensions remain elevated across the region as turn {turn} begins.")

        return news[:2]  # max 2 news items per turn

    def _generate_briefs(self, turn: int) -> dict[str, list[str]]:
        """Generate private briefs for each actor."""
        if turn == 1:
            return dict(self.world.private_briefs)

        # For subsequent turns, generate contextual briefs
        briefs: dict[str, list[str]] = {}
        for actor in self.world.actors:
            actor_id = actor.actor_id
            state = self.game_state.actor_states[actor_id]
            actor_briefs = []

            # Resource status
            if state.treasury < 50:
                actor_briefs.append("Treasury reserves are critically low. Economic action needed.")
            if state.domestic_stability < 50:
                actor_briefs.append("Domestic unrest is growing. Consider stabilization measures.")
            if state.military_readiness > 80:
                actor_briefs.append("Military readiness is high. Your forces are prepared for action.")

            # Relationship changes
            for other_id, rel in state.relations.items():
                if other_id in self.actor_map:
                    if rel < -0.6:
                        actor_briefs.append(
                            f"Relations with {self.actor_map[other_id].name} have deteriorated to hostile levels."
                        )
                    elif rel > 0.7:
                        actor_briefs.append(
                            f"Strong alliance with {self.actor_map[other_id].name} presents cooperation opportunities."
                        )

            if not actor_briefs:
                actor_briefs.append("Situation remains stable. Continue current strategy.")

            briefs[actor_id] = actor_briefs[:3]

        return briefs

    def _summarize_turn(
        self,
        actor_id: str,
        turn: int,
        resolutions: list[str],
        scores: list[ActorScore],
    ) -> list[str]:
        """Create a memory summary for the actor."""
        summary = [f"Turn {turn} summary:"]
        actor_name = self.actor_map[actor_id].name

        # Add relevant resolutions
        for res in resolutions:
            if actor_name in res or actor_id in res:
                summary.append(f"- {res}")

        # Add score info
        my_score = next((s for s in scores if s.actor_id == actor_id), None)
        if my_score:
            summary.append(f"- Current score: {my_score.total:.1f}")

        return summary[:8]

    def _save_replay(self, replay) -> None:
        """Save the replay log to disk — both a unique run file and a 'latest' alias."""
        out_dir = Path(self.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Serialize once
        if hasattr(replay, "model_dump"):
            payload = replay.model_dump()
        else:
            payload = replay

        # Save to unique path (keyed by run_id)
        unique_path = out_dir / f"{self.run_id}_replay.json"
        with open(unique_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        print(f"  Replay saved: {unique_path}")

        # Also save as "latest" for backward compat
        latest_path = out_dir / f"{self.world.world_id}_replay.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)


def load_world(path: str) -> World:
    """Load a world definition from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return World(**data)


def run_simulation(
    world_path: str,
    seed: int = 42,
    output_dir: str = "logs/replays",
    agent_type: str = "mock",
    llm_model: str = "big-pickle",
    llm_api_key: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_temperature: float = 0.7,
    on_turn_complete=None,
    llm_call_delay: float = 2.0,
) -> ReplayLog:
    """Load a world and run a full simulation."""
    world = load_world(world_path)
    runner = SimulationRunner(
        world=world,
        seed=seed,
        output_dir=output_dir,
        agent_type=agent_type,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_provider=llm_provider,
        llm_temperature=llm_temperature,
        world_path=world_path,
        on_turn_complete=on_turn_complete,
        llm_call_delay=llm_call_delay,
    )
    return runner.run()
