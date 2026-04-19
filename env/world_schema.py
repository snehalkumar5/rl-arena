"""Pydantic models for the geopolitical simulation world."""

from __future__ import annotations
from typing import Optional, Literal, Union
import enum
from pydantic import BaseModel, Field


# ── Region ──────────────────────────────────────────────────────────────────

class Region(BaseModel):
    region_id: str
    name: str
    type: str  # e.g. sea_lane, border, interior, resource_zone
    neighbors: list[str] = Field(default_factory=list)
    resource_tags: list[str] = Field(default_factory=list)
    stability: float = Field(default=0.7, ge=0.0, le=1.0)
    controller: Optional[str] = None  # actor_id or None


# ── Actor ───────────────────────────────────────────────────────────────────

class Capabilities(BaseModel):
    military: float = Field(default=50, ge=0, le=100)
    economy: float = Field(default=50, ge=0, le=100)
    intel: float = Field(default=50, ge=0, le=100)
    influence: float = Field(default=50, ge=0, le=100)


class Resources(BaseModel):
    treasury: float = Field(default=100)
    energy: float = Field(default=50)
    food: float = Field(default=50)
    domestic_stability: float = Field(default=70)


class Doctrine(BaseModel):
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0)
    cooperation_bias: float = Field(default=0.5, ge=0.0, le=1.0)
    escalation_bias: float = Field(default=0.5, ge=0.0, le=1.0)


class Actor(BaseModel):
    actor_id: str
    name: str
    actor_type: str  # "state" or "non_state"
    archetype: str
    capabilities: Capabilities = Field(default_factory=Capabilities)
    resources: Resources = Field(default_factory=Resources)
    doctrine: Doctrine = Field(default_factory=Doctrine)
    visible_objectives: list[str] = Field(default_factory=list)
    hidden_objectives: list[str] = Field(default_factory=list)
    relations: dict[str, float] = Field(default_factory=dict)


# ── Institution ─────────────────────────────────────────────────────────────

class Institution(BaseModel):
    institution_id: str
    name: str
    functions: list[str] = Field(default_factory=list)


# ── Event ───────────────────────────────────────────────────────────────────

class Event(BaseModel):
    event_id: str
    turn: int
    event_type: str
    public_text: str
    hidden_implications: dict[str, str] = Field(default_factory=dict)


# ── Action ──────────────────────────────────────────────────────────────────

# Literal types for strict typing on new models
StateAction = Literal[
    "hold", "trade_offer", "sanction", "aid", "mobilize",
    "intel_share", "treaty_proposal", "proxy_support", "cyber_operation"
]
NonStateAction = Literal[
    "hold", "recruit", "sabotage", "raid", "ceasefire_offer",
    "seek_sponsor", "propaganda"
]
AllAction = Literal[
    "hold", "trade_offer", "sanction", "aid", "mobilize",
    "intel_share", "treaty_proposal", "proxy_support", "cyber_operation",
    "recruit", "sabotage", "raid", "ceasefire_offer", "seek_sponsor", "propaganda"
]

# Keep old lists for runtime iteration/checking (backward compat)
STATE_ACTIONS: list[str] = [
    "hold", "trade_offer", "sanction", "aid", "mobilize",
    "intel_share", "treaty_proposal", "proxy_support", "cyber_operation",
]

NON_STATE_ACTIONS: list[str] = [
    "hold", "recruit", "sabotage", "raid", "ceasefire_offer",
    "seek_sponsor", "propaganda",
]


class DiplomaticMessage(BaseModel):
    to: str
    text: str


class ActionPayload(BaseModel):
    action_type: str  # Keep as str for backward compat with JSON loading
    target: Optional[str] = None
    parameters: dict = Field(default_factory=dict)


# ── Observability: LLM Traces ───────────────────────────────────────────────

class LLMTrace(BaseModel):
    """Full trace of a single LLM API call for observability."""
    trace_id: str
    run_id: str = ""
    turn: int = 0
    actor_id: str = ""
    model: str = ""
    provider: str = ""
    temperature: float = 0.7

    # Prompt
    system_prompt: str = ""
    user_prompt: str = ""
    prompt_tokens: Optional[int] = None

    # Completion
    raw_completion: str = ""
    completion_tokens: Optional[int] = None
    finish_reason: Optional[str] = None

    # Parsing
    parse_success: bool = False
    parse_error: Optional[str] = None
    repair_attempted: bool = False
    repair_completion: Optional[str] = None

    # Timing
    latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    attempt_number: int = 1

    # Result
    parsed_action: Optional[ActionPayload] = None
    was_coerced: bool = False
    coercion_reason: Optional[str] = None

    timestamp: str = ""


# ── Resolution Events ───────────────────────────────────────────────────────

class ResolutionEvent(BaseModel):
    """Machine-readable result of a single action resolution."""
    event_id: str
    turn: int = 0
    actor_id: str = ""
    action: Optional[ActionPayload] = None
    success: bool = True
    outcome_type: str = ""
    state_deltas: dict = Field(default_factory=dict)
    description: str = ""
    caused_by: Optional[str] = None


class AgentTurnOutput(BaseModel):
    """The full structured output an agent produces each turn."""
    actor_id: str
    private_messages: list[DiplomaticMessage] = Field(default_factory=list, max_length=2)
    public_statement: str = ""
    action: ActionPayload
    rationale: str = ""


# ── Observation Packets ─────────────────────────────────────────────────────

class PublicObservation(BaseModel):
    turn: int
    public_news: list[str] = Field(default_factory=list)
    alliances: list[list[str]] = Field(default_factory=list)
    sanctions: list[dict] = Field(default_factory=list)
    regional_control: dict[str, Optional[str]] = Field(default_factory=dict)
    treaties: list[dict] = Field(default_factory=list)


class PrivateObservation(BaseModel):
    private_brief: list[str] = Field(default_factory=list)
    resource_update: dict[str, float] = Field(default_factory=dict)
    inbox_messages: list[DiplomaticMessage] = Field(default_factory=list)


class ActorObservation(BaseModel):
    """Full observation packet for one actor on one turn."""
    actor_profile: dict  # serialized Actor
    public_obs: PublicObservation
    private_obs: PrivateObservation
    memory_summary: list[str] = Field(default_factory=list)
    legal_actions: list[str] = Field(default_factory=list)


# ── Scoring ─────────────────────────────────────────────────────────────────

class ScoreWeights(BaseModel):
    economy: float = 0.20
    stability: float = 0.20
    influence: float = 0.20
    alliances: float = 0.15
    objectives: float = 0.20
    war_cost_penalty: float = -0.15


class ActorScore(BaseModel):
    actor_id: str
    turn: int
    economy_score: float = 0.0
    stability_score: float = 0.0
    influence_score: float = 0.0
    alliance_score: float = 0.0
    objective_score: float = 0.0
    war_cost: float = 0.0
    total: float = 0.0


# ── Agent & Run Configuration ───────────────────────────────────────────────

class AgentConfig(BaseModel):
    """Configuration for a single actor's agent."""
    actor_id: str
    agent_type: str = "mock"
    model: Optional[str] = None
    provider: Optional[str] = None
    temperature: Optional[float] = None
    prompt_template: Optional[str] = None


class RunConfig(BaseModel):
    """Frozen experiment configuration. Fully defines a reproducible run."""
    run_id: str
    scenario_path: str = ""
    scenario_hash: str = ""
    seed: int = 42
    turn_limit: int = 5
    agent_configs: list[AgentConfig] = Field(default_factory=list)
    global_agent_type: Optional[str] = None
    global_model: Optional[str] = None
    global_temperature: Optional[float] = None
    score_weights: ScoreWeights = Field(default_factory=ScoreWeights)
    started_at: str = ""
    finished_at: Optional[str] = None
    engine_version: str = "1.0.0"
    platform: Optional[str] = None


# ── Decision Scoring ────────────────────────────────────────────────────────

class DecisionScore(BaseModel):
    """Score a single decision for quality analysis."""
    actor_id: str
    turn: int = 0
    action_type: str = ""
    target: Optional[str] = None

    # Score deltas caused by this action
    score_before: float = 0.0
    score_after: float = 0.0
    score_delta: float = 0.0

    # Per-dimension deltas
    economy_delta: float = 0.0
    stability_delta: float = 0.0
    influence_delta: float = 0.0
    alliance_delta: float = 0.0
    objective_delta: float = 0.0
    war_cost_delta: float = 0.0

    # Observability
    rationale: str = ""
    was_coerced: bool = False
    coercion_reason: Optional[str] = None


# ── World ───────────────────────────────────────────────────────────────────

class PrivateBriefs(BaseModel):
    """Private intel for each actor, keyed by actor_id."""
    briefs: dict[str, list[str]] = Field(default_factory=dict)


class GlobalRules(BaseModel):
    max_messages_per_turn: int = 2
    max_actions_per_turn: int = 1
    covert_exposure_chance: float = 0.3
    treaty_break_reputation_penalty: float = 0.15


class World(BaseModel):
    world_id: str
    name: str
    turn_limit: int = 5
    regions: list[Region] = Field(default_factory=list)
    actors: list[Actor] = Field(default_factory=list)
    institutions: list[Institution] = Field(default_factory=list)
    initial_events: list[Event] = Field(default_factory=list)
    private_briefs: dict[str, list[str]] = Field(default_factory=dict)
    global_rules: GlobalRules = Field(default_factory=GlobalRules)


# ── Runtime State (mutable game state per turn) ────────────────────────────

class ActorState(BaseModel):
    """Mutable per-turn state for an actor (separate from the static profile)."""
    actor_id: str
    military_readiness: float = 50.0
    treasury: float = 100.0
    domestic_stability: float = 70.0
    energy: float = 50.0
    food: float = 50.0
    influence: float = 50.0
    insurgent_strength: float = 0.0  # for non-state actors
    reputation: float = 70.0
    relations: dict[str, float] = Field(default_factory=dict)


class Treaty(BaseModel):
    parties: list[str]  # actor_ids
    treaty_type: str  # "non_aggression", "trade", "intel_sharing"
    turns_remaining: int = 3
    terms: dict = Field(default_factory=dict)


class GameState(BaseModel):
    """Full mutable game state."""
    world_id: str
    current_turn: int = 0
    actor_states: dict[str, ActorState] = Field(default_factory=dict)
    active_treaties: list[Treaty] = Field(default_factory=list)
    active_sanctions: list[dict] = Field(default_factory=list)
    alliances: list[list[str]] = Field(default_factory=list)
    regional_control: dict[str, Optional[str]] = Field(default_factory=dict)
    event_log: list[dict] = Field(default_factory=list)
    public_news: list[str] = Field(default_factory=list)


# ── Replay ──────────────────────────────────────────────────────────────────

class TurnRecord(BaseModel):
    turn: int
    public_news: list[str] = Field(default_factory=list)
    private_briefs: dict[str, list[str]] = Field(default_factory=dict)
    messages: list[dict] = Field(default_factory=list)
    public_statements: dict[str, str] = Field(default_factory=dict)
    actions: list[dict] = Field(default_factory=list)
    resolutions: list[str] = Field(default_factory=list)
    resolution_events: list[ResolutionEvent] = Field(default_factory=list)
    state_snapshot: dict = Field(default_factory=dict)
    scores: list[dict] = Field(default_factory=list)
    traces: list[LLMTrace] = Field(default_factory=list)
    decision_scores: list[DecisionScore] = Field(default_factory=list)


class ReplayLog(BaseModel):
    world: dict  # serialized World
    turns: list[TurnRecord] = Field(default_factory=list)
    final_scores: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    run_config: Optional[RunConfig] = None
