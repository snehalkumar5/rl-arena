"""
CLI entry point for the geopolitical simulation.

Usage:
    # Run with mock agents (default)
    python -m app.main

    # Run with LLM agents via OpenCode Zen
    python -m app.main --agent llm --model big-pickle --key YOUR_ZEN_KEY

    # Run with a specific scenario
    python -m app.main --world scenarios/seed_worlds/saffron_sea_crisis.json

    # Run with specific seed
    python -m app.main --seed 99

Environment variables (alternative to --key):
    OPENCODE_ZEN_API_KEY   - Your OpenCode Zen API key
    OPENAI_API_KEY         - Direct OpenAI API key
    ANTHROPIC_API_KEY      - Direct Anthropic API key

DISCLAIMER: Simulation outputs are speculative and not intelligence products.
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.runner import run_simulation


def main():
    parser = argparse.ArgumentParser(
        description="Geo-Arena: Geopolitical Multi-Agent Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.main                                          # Mock agents
  python -m app.main --agent llm --model big-pickle           # Free LLM via Zen
  python -m app.main --agent llm --model claude-sonnet-4      # Claude via Zen
  python -m app.main --agent llm --model gpt-5-nano           # Free GPT via Zen

Free models (no cost): big-pickle, nemotron-3-super-free, minimax-m2.5-free, gpt-5-nano
        """,
    )
    parser.add_argument(
        "--world", "-w",
        default="scenarios/seed_worlds/saffron_sea_crisis.json",
        help="Path to world JSON file",
    )
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--agent", "-a",
        choices=["mock", "llm"],
        default=os.environ.get("GEO_AGENT_TYPE", "mock"),
        help="Agent type: mock (rule-based) or llm (LLM-backed)",
    )
    parser.add_argument(
        "--model", "-m",
        default=os.environ.get("GEO_LLM_MODEL", "big-pickle"),
        help="LLM model ID (see OpenCode Zen docs for available models)",
    )
    parser.add_argument(
        "--key", "-k",
        default=None,
        help="API key (Zen, OpenAI, or Anthropic). Can also use env vars.",
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["zen", "openai", "anthropic"],
        default=None,
        help="Provider (auto-detected if not specified)",
    )
    parser.add_argument(
        "--temp", "-t",
        type=float,
        default=0.7,
        help="LLM temperature (0.0-1.0)",
    )

    args = parser.parse_args()

    if args.agent == "llm":
        print(f"\n  Agent: LLM ({args.model})")
        print(f"  Provider: {args.provider or 'auto-detect'}")
        api_key = args.key or os.environ.get("OPENCODE_ZEN_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("\n  ERROR: No API key found. Set OPENCODE_ZEN_API_KEY env var or use --key flag.")
            print("  Get a key at: https://opencode.ai/auth")
            sys.exit(1)
    else:
        api_key = None
        print(f"\n  Agent: Mock (rule-based)")

    replay = run_simulation(
        world_path=args.world,
        seed=args.seed,
        agent_type=args.agent,
        llm_model=args.model,
        llm_api_key=api_key,
        llm_provider=args.provider,
        llm_temperature=args.temp,
    )

    print(f"\nSimulation complete. {len(replay.turns)} turns played.")
    print(f"Final leaderboard:")
    for entry in replay.final_scores:
        print(f"  #{entry['rank']} {entry['name']}: {entry['final_score']:.1f}")


if __name__ == "__main__":
    main()
