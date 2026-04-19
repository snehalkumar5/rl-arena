"""Configuration for Geo-Arena simulations."""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "scenarios"
SEED_WORLDS_DIR = SCENARIOS_DIR / "seed_worlds"
GENERATED_WORLDS_DIR = SCENARIOS_DIR / "generated_worlds"
REPLAYS_DIR = PROJECT_ROOT / "logs" / "replays"
METRICS_DIR = PROJECT_ROOT / "logs" / "metrics"

# Simulation defaults
DEFAULT_SEED = 42
DEFAULT_TURN_LIMIT = 5

# Scoring weights
SCORE_WEIGHTS = {
    "economy": 0.20,
    "stability": 0.20,
    "influence": 0.20,
    "alliances": 0.15,
    "objectives": 0.20,
    "war_cost_penalty": -0.15,
}

# ── Agent Configuration ─────────────────────────────────────────────────────
#
# Agent type: "mock" for rule-based agents, "llm" for LLM-backed agents
DEFAULT_AGENT_TYPE = os.environ.get("GEO_AGENT_TYPE", "mock")

# ── OpenCode Zen Configuration ──────────────────────────────────────────────
#
# OpenCode Zen is a curated AI gateway: https://opencode.ai/docs/zen/
# Sign up at https://opencode.ai/auth and copy your API key.
#
# Set your key via environment variable or paste it here (not recommended for git):
#   export OPENCODE_ZEN_API_KEY="your-key-here"
#
ZEN_API_KEY = os.environ.get("OPENCODE_ZEN_API_KEY", "")

# Default model to use via Zen.
# Free models:  big-pickle, nemotron-3-super-free, minimax-m2.5-free, gpt-5-nano
# Cheap models: qwen3.5-plus ($0.20/$1.20 per 1M tokens), claude-haiku-3.5 ($0.80/$4.00)
# Best models:  claude-sonnet-4 ($3/$15), gpt-5.1 ($1.07/$8.50)
DEFAULT_LLM_MODEL = os.environ.get("GEO_LLM_MODEL", "big-pickle")

# Temperature for LLM calls (0.0 = deterministic, 1.0 = creative)
LLM_TEMPERATURE = float(os.environ.get("GEO_LLM_TEMP", "0.7"))

# Max retries for invalid LLM output
LLM_MAX_RETRIES = 3

# ── Direct Provider Keys (fallback if not using Zen) ────────────────────────
# These are only needed if you want to bypass Zen and call providers directly.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Engine Rules ────────────────────────────────────────────────────────────
COVERT_EXPOSURE_CHANCE = 0.3
TREATY_BREAK_REPUTATION_PENALTY = 0.15
MAX_MESSAGES_PER_TURN = 2
MAX_ACTIONS_PER_TURN = 1

# ── Utilities ───────────────────────────────────────────────────────────────
import hashlib


def hash_file(path: str) -> str:
    """SHA256 hash of a file's contents for reproducibility tracking."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

