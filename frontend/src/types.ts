/* ── TypeScript types matching the Pydantic models ── */

export interface Region {
  region_id: string;
  name: string;
  type: string;
  neighbors: string[];
  resource_tags: string[];
  stability: number;
  controller: string | null;
}

export interface Capabilities {
  military: number;
  economy: number;
  intel: number;
  influence: number;
}

export interface Resources {
  treasury: number;
  energy: number;
  food: number;
  domestic_stability: number;
}

export interface Doctrine {
  risk_tolerance: number;
  cooperation_bias: number;
  escalation_bias: number;
}

export interface Actor {
  actor_id: string;
  name: string;
  actor_type: 'state' | 'non_state';
  archetype: string;
  capabilities: Capabilities;
  resources: Resources;
  doctrine: Doctrine;
  visible_objectives: string[];
  hidden_objectives: string[];
  relations: Record<string, number>;
}

export interface Event {
  event_id: string;
  turn: number;
  event_type: string;
  public_text: string;
  hidden_implications: Record<string, string>;
}

export interface World {
  world_id: string;
  name: string;
  turn_limit: number;
  regions: Region[];
  actors: Actor[];
  institutions: { institution_id: string; name: string; functions: string[] }[];
  initial_events: Event[];
  private_briefs: Record<string, string[]>;
  global_rules: {
    max_messages_per_turn: number;
    max_actions_per_turn: number;
    covert_exposure_chance: number;
    treaty_break_reputation_penalty: number;
  };
}

export interface ActionRecord {
  actor_id: string;
  actor_name: string;
  action_type: string;
  target: string | null;
  target_name: string | null;
  parameters: Record<string, unknown>;
  rationale: string;
}

export interface Message {
  from: string;
  to: string;
  text: string;
}

export interface ScoreRecord {
  actor_id: string;
  turn: number;
  economy_score: number;
  stability_score: number;
  influence_score: number;
  alliance_score: number;
  objective_score: number;
  war_cost: number;
  total: number;
}

export interface ActorState {
  actor_id: string;
  military_readiness: number;
  treasury: number;
  domestic_stability: number;
  energy: number;
  food: number;
  influence: number;
  insurgent_strength: number;
  reputation: number;
  relations: Record<string, number>;
}

export interface TurnRecord {
  turn: number;
  public_news: string[];
  private_briefs: Record<string, string[]>;
  messages: Message[];
  public_statements: Record<string, string>;
  actions: ActionRecord[];
  resolutions: string[];
  state_snapshot: Record<string, ActorState>;
  scores: ScoreRecord[];
}

export interface FinalScore {
  actor_id: string;
  name: string;
  rank: number;
  final_score: number;
}

export interface ReplayLog {
  world: World;
  turns: TurnRecord[];
  final_scores: FinalScore[];
  metadata: {
    seed?: number;
    agent_type: string;
    total_turns: number;
  };
}

export interface ReplaySummary {
  id: string;
  filename: string;
  name: string;
  world_id: string;
  turns: number;
  actor_count: number;
  agent_type: string;
}

export interface ScenarioSummary {
  id: string;
  name: string;
  world_id: string;
  turn_limit: number;
  actor_count: number;
  region_count: number;
}

/* ── Backtest types ── */

export interface ActorMatch {
  actor_id: string;
  real_action: string;
  real_description: string;
  sim_action: string;
  sim_target: string;
  sim_rationale: string;
  score: number;
  match: 'EXACT' | 'PARTIAL' | 'MISS';
}

export interface TurnComparison {
  turn: number;
  label: string;
  date_range: string;
  actor_matches: ActorMatch[];
  turn_accuracy: number;
}

export interface BacktestReport {
  scenario: string;
  baseline_date: string;
  agent_type: string;
  llm_model: string;
  disclaimer: string;
  turn_comparisons: TurnComparison[];
  overall_accuracy: number;
  actor_accuracy: Record<string, number>;
  divergences: string[];
  correct_predictions: string[];
}

export interface VariantResult {
  variant: string;
  description: string;
  accuracy_vs_reality: number;
  final_leaderboard: FinalScore[];
}

/* ── Geo coordinates for regions ── */

export const REGION_COORDS: Record<string, [number, number]> = {
  hormuz: [56.3, 26.6],
  persian_gulf: [51.5, 27.5],
  gulf_of_oman: [58.5, 24.5],
  kharg_island: [50.3, 29.2],
  red_sea: [42.5, 15.5],
  lebanon: [35.5, 33.9],
  yemen: [44.2, 15.4],
  islamabad: [73.0, 33.7],
  // Saffron Sea fallbacks
  narrows: [45.0, 25.0],
  saffron_basin: [47.0, 26.0],
  outer_reach: [49.0, 24.0],
  jade_coast: [43.0, 27.0],
  iron_highlands: [46.0, 28.0],
  amber_delta: [48.0, 25.5],
  obsidian_strait: [44.5, 24.5],
  coral_archipelago: [50.0, 23.5],
};

/* ── Actor color assignments ── */

export const ACTOR_COLORS: Record<number, string> = {
  0: '#00d2ff', // Cyan
  1: '#ff6b35', // Orange
  2: '#00e676', // Green
  3: '#ffd740', // Amber
  4: '#ff5252', // Red
  5: '#b388ff', // Purple
  6: '#ffa726', // Deep Orange
  7: '#4db6ac', // Teal
  8: '#e91e63', // Pink
  9: '#8d6e63', // Brown
};

export function getActorColor(index: number): string {
  return ACTOR_COLORS[index] ?? '#ffffff';
}

export function getActorColorById(actorId: string, actors: Actor[]): string {
  const idx = actors.findIndex(a => a.actor_id === actorId);
  return getActorColor(idx >= 0 ? idx : 0);
}

// ── Observability Types ─────────────────────────────────

export interface LLMTrace {
  trace_id: string;
  run_id: string;
  turn: number;
  actor_id: string;
  model: string;
  provider: string;
  temperature: number;
  system_prompt: string;
  user_prompt: string;
  prompt_tokens: number | null;
  raw_completion: string;
  completion_tokens: number | null;
  finish_reason: string | null;
  parse_success: boolean;
  parse_error: string | null;
  repair_attempted: boolean;
  repair_completion: string | null;
  latency_ms: number;
  total_latency_ms: number;
  attempt_number: number;
  parsed_action: { action_type: string; target: string | null; parameters: Record<string, unknown> } | null;
  was_coerced: boolean;
  coercion_reason: string | null;
  timestamp: string;
}

export interface ResolutionEvent {
  event_id: string;
  turn: number;
  actor_id: string;
  action: { action_type: string; target: string | null; parameters: Record<string, unknown> } | null;
  success: boolean;
  outcome_type: string;
  state_deltas: Record<string, Record<string, number>>;
  description: string;
  caused_by: string | null;
}

export interface DecisionScore {
  actor_id: string;
  turn: number;
  action_type: string;
  target: string | null;
  score_before: number;
  score_after: number;
  score_delta: number;
  economy_delta: number;
  stability_delta: number;
  influence_delta: number;
  alliance_delta: number;
  objective_delta: number;
  war_cost_delta: number;
  rationale: string;
  was_coerced: boolean;
  coercion_reason: string | null;
}

export interface AgentConfig {
  actor_id: string;
  agent_type: string;
  model: string | null;
  provider: string | null;
  temperature: number | null;
}

export interface RunConfig {
  run_id: string;
  scenario_path: string;
  scenario_hash: string;
  seed: number;
  turn_limit: number;
  agent_configs: AgentConfig[];
  global_agent_type: string | null;
  global_model: string | null;
  global_temperature: number | null;
  started_at: string;
  finished_at: string | null;
  engine_version: string;
  platform: string | null;
}

export interface RunSummary {
  run_id: string;
  scenario: string;
  model: string | null;
  seed: number | null;
  agent_type: string | null;
  turns: number;
  started_at: string | null;
  filename: string;
}

export interface TraceStats {
  run_id: string;
  total_traces: number;
  total_tokens: number;
  total_latency_ms: number;
  coercion_count: number;
  coercion_rate: number;
  traces: LLMTrace[];
}

export interface RunComparison {
  run_ids: string[];
  configs: Record<string, { model: string | null; agent_type: string | null; seed: number | null }>;
  score_comparison: Record<string, Record<string, number>>;
  action_comparison: Record<string, Array<{ turn: number; actions: Record<string, { action_type: string; target: string | null; rationale: string }> }>>;
  trace_stats: Record<string, { total_traces: number; total_tokens: number; total_latency_ms: number; coercion_count: number }>;
  score_diffs?: Record<string, { run_a: number; run_b: number; delta: number }>;
  action_diffs?: Array<{ turn: number; diffs: Record<string, { run_a: string; run_b: string }> }>;
}
