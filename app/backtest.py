"""
Backtesting harness: Run simulation and compare against real-world ground truth.

Usage:
    python -m app.backtest
    python -m app.backtest --agent llm --model big-pickle --key YOUR_KEY
    python -m app.backtest --variants    # Run branching scenario variants

DISCLAIMER: Simulation outputs are speculative and not intelligence products.
"""

from __future__ import annotations

import json
import sys
import os
import argparse
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.runner import SimulationRunner, load_world


# ── Ground Truth Loading ────────────────────────────────────────────────────

def load_ground_truth(path: str = "scenarios/hormuz_ground_truth.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Action Matching ─────────────────────────────────────────────────────────

ACTION_SIMILARITY = {
    # Exact matches
    ("sanction", "sanction"): 1.0,
    ("mobilize", "mobilize"): 1.0,
    ("hold", "hold"): 1.0,
    ("trade_offer", "trade_offer"): 1.0,
    ("treaty_proposal", "treaty_proposal"): 1.0,
    ("aid", "aid"): 1.0,
    ("intel_share", "intel_share"): 1.0,
    ("proxy_support", "proxy_support"): 1.0,
    ("recruit", "recruit"): 1.0,
    ("sabotage", "sabotage"): 1.0,
    ("propaganda", "propaganda"): 1.0,
    ("seek_sponsor", "seek_sponsor"): 1.0,
    # Partial matches (escalatory actions are somewhat interchangeable)
    ("sanction", "mobilize"): 0.5,
    ("mobilize", "sanction"): 0.5,
    ("sanction", "cyber_operation"): 0.4,
    ("cyber_operation", "sanction"): 0.4,
    ("trade_offer", "aid"): 0.6,
    ("aid", "trade_offer"): 0.6,
    ("trade_offer", "treaty_proposal"): 0.5,
    ("treaty_proposal", "trade_offer"): 0.5,
    ("treaty_proposal", "intel_share"): 0.4,
    ("intel_share", "treaty_proposal"): 0.4,
    ("hold", "recruit"): 0.3,
    ("recruit", "hold"): 0.3,
    ("sabotage", "raid"): 0.7,
    ("raid", "sabotage"): 0.7,
    ("propaganda", "recruit"): 0.4,
    ("recruit", "propaganda"): 0.4,
    ("seek_sponsor", "hold"): 0.3,
    ("hold", "seek_sponsor"): 0.3,
}


def score_action_match(sim_action: str, real_action: str) -> float:
    """Score how well a simulated action matches the real-world action."""
    if sim_action == real_action:
        return 1.0
    return ACTION_SIMILARITY.get((sim_action, real_action), 0.1)


# ── Backtesting ─────────────────────────────────────────────────────────────

def backtest(
    world_path: str = "scenarios/seed_worlds/hormuz_crisis_apr8.json",
    truth_path: str = "scenarios/hormuz_ground_truth.json",
    seed: int = 42,
    agent_type: str = "mock",
    llm_model: str = "big-pickle",
    llm_api_key: Optional[str] = None,
    llm_provider: Optional[str] = None,
) -> dict:
    """Run simulation and compare against ground truth. Returns comparison report."""
    world = load_world(world_path)
    truth = load_ground_truth(truth_path)

    runner = SimulationRunner(
        world,
        seed=seed,
        output_dir="logs/replays",
        agent_type=agent_type,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_provider=llm_provider,
        world_path=world_path,
    )
    replay = runner.run()

    # ── Compare each turn ───────────────────────────────────────────────
    report = {
        "scenario": truth["scenario_id"],
        "baseline_date": truth["baseline_date"],
        "agent_type": agent_type,
        "llm_model": llm_model if agent_type == "llm" else "N/A",
        "disclaimer": truth["disclaimer"],
        "turn_comparisons": [],
        "overall_accuracy": 0.0,
        "actor_accuracy": {},
        "divergences": [],
        "correct_predictions": [],
    }

    all_scores = []
    actor_scores: dict[str, list[float]] = {}

    for turn_truth in truth["turns"]:
        turn_num = turn_truth["turn"]
        if turn_num > len(replay.turns):
            break

        sim_turn = replay.turns[turn_num - 1]
        turn_comparison = {
            "turn": turn_num,
            "label": turn_truth["label"],
            "date_range": turn_truth["date_range"],
            "actor_matches": [],
        }

        for actor_id, real_action_data in turn_truth["real_actions"].items():
            real_action_type = real_action_data["action_type"]
            real_description = real_action_data["description"]

            # Find simulated action for this actor
            sim_action_data = next(
                (a for a in sim_turn.actions if a.get("actor_id") == actor_id),
                None,
            )

            if sim_action_data:
                sim_action_type = sim_action_data["action_type"]
                sim_target = sim_action_data.get("target", "")
                sim_rationale = sim_action_data.get("rationale", "")
            else:
                sim_action_type = "MISSING"
                sim_target = ""
                sim_rationale = ""

            score = score_action_match(sim_action_type, real_action_type)
            all_scores.append(score)

            if actor_id not in actor_scores:
                actor_scores[actor_id] = []
            actor_scores[actor_id].append(score)

            match_record = {
                "actor_id": actor_id,
                "real_action": real_action_type,
                "real_description": real_description,
                "sim_action": sim_action_type,
                "sim_target": sim_target,
                "sim_rationale": sim_rationale,
                "score": score,
                "match": "EXACT" if score == 1.0 else "PARTIAL" if score >= 0.4 else "MISS",
            }
            turn_comparison["actor_matches"].append(match_record)

            if score == 1.0:
                report["correct_predictions"].append(
                    f"Turn {turn_num} [{turn_truth['label']}]: {actor_id} correctly predicted {real_action_type}"
                )
            elif score < 0.4:
                report["divergences"].append(
                    f"Turn {turn_num} [{turn_truth['label']}]: {actor_id} predicted {sim_action_type} but reality was {real_action_type} ({real_description})"
                )

        turn_comparison["turn_accuracy"] = (
            sum(m["score"] for m in turn_comparison["actor_matches"])
            / len(turn_comparison["actor_matches"])
            if turn_comparison["actor_matches"]
            else 0.0
        )
        report["turn_comparisons"].append(turn_comparison)

    # ── Aggregate scores ────────────────────────────────────────────────
    report["overall_accuracy"] = sum(all_scores) / len(all_scores) if all_scores else 0.0
    for actor_id, scores in actor_scores.items():
        report["actor_accuracy"][actor_id] = sum(scores) / len(scores) if scores else 0.0

    return report


def print_report(report: dict) -> None:
    """Pretty-print the backtesting report."""
    print(f"\n{'='*70}")
    print(f"  BACKTEST REPORT: {report['scenario']}")
    print(f"  Baseline: {report['baseline_date']} | Agent: {report['agent_type']}")
    if report["agent_type"] == "llm":
        print(f"  Model: {report['llm_model']}")
    print(f"  {report['disclaimer']}")
    print(f"{'='*70}")

    # Overall accuracy
    accuracy = report["overall_accuracy"]
    bar = "#" * int(accuracy * 30) + "-" * (30 - int(accuracy * 30))
    print(f"\n  OVERALL ACCURACY: {accuracy:.1%}  [{bar}]")

    # Per-actor accuracy
    print(f"\n  ACTOR ACCURACY:")
    for actor_id, acc in sorted(report["actor_accuracy"].items(), key=lambda x: -x[1]):
        bar = "#" * int(acc * 20) + "-" * (20 - int(acc * 20))
        print(f"    {actor_id:.<20} {acc:.1%}  [{bar}]")

    # Turn-by-turn
    print(f"\n  TURN-BY-TURN COMPARISON:")
    for tc in report["turn_comparisons"]:
        print(f"\n  --- {tc['label']} (Accuracy: {tc['turn_accuracy']:.1%}) ---")
        for m in tc["actor_matches"]:
            icon = {
                "EXACT": "[OK]",
                "PARTIAL": "[~~]",
                "MISS": "[XX]",
            }[m["match"]]
            print(
                f"    {icon} {m['actor_id']:.<15} "
                f"Sim: {m['sim_action']:<18} Real: {m['real_action']:<18} "
                f"({m['score']:.0%})"
            )

    # Correct predictions
    if report["correct_predictions"]:
        print(f"\n  CORRECT PREDICTIONS ({len(report['correct_predictions'])}):")
        for p in report["correct_predictions"]:
            print(f"    + {p}")

    # Divergences
    if report["divergences"]:
        print(f"\n  DIVERGENCES ({len(report['divergences'])}):")
        for d in report["divergences"]:
            print(f"    - {d}")

    print()


# ── Branching Variants ──────────────────────────────────────────────────────

DOCTRINE_VARIANTS = {
    "baseline": {
        "description": "Default doctrines from intelligence assessment",
        "overrides": {},
    },
    "iran_hawkish": {
        "description": "Iran maximally escalatory - risk_tolerance=0.95, escalation=0.95",
        "overrides": {
            "iran": {"risk_tolerance": 0.95, "cooperation_bias": 0.1, "escalation_bias": 0.95},
        },
    },
    "iran_dovish": {
        "description": "Iran seeks deal - risk_tolerance=0.3, cooperation=0.8",
        "overrides": {
            "iran": {"risk_tolerance": 0.3, "cooperation_bias": 0.8, "escalation_bias": 0.2},
        },
    },
    "us_deescalation": {
        "description": "US prioritizes diplomacy over force",
        "overrides": {
            "usa": {"risk_tolerance": 0.3, "cooperation_bias": 0.7, "escalation_bias": 0.3},
        },
    },
    "china_assertive": {
        "description": "China takes active military/economic role",
        "overrides": {
            "china": {"risk_tolerance": 0.6, "cooperation_bias": 0.4, "escalation_bias": 0.5},
        },
    },
    "houthi_all_in": {
        "description": "Houthis launch full Red Sea campaign",
        "overrides": {
            "houthis": {"risk_tolerance": 0.95, "cooperation_bias": 0.05, "escalation_bias": 0.95},
        },
    },
}


def run_variants(
    world_path: str = "scenarios/seed_worlds/hormuz_crisis_apr8.json",
    truth_path: str = "scenarios/hormuz_ground_truth.json",
    agent_type: str = "mock",
    llm_model: str = "big-pickle",
    llm_api_key: Optional[str] = None,
) -> list[dict]:
    """Run multiple simulation variants with different doctrine overrides."""
    results = []

    for variant_name, variant in DOCTRINE_VARIANTS.items():
        print(f"\n{'='*70}")
        print(f"  VARIANT: {variant_name}")
        print(f"  {variant['description']}")
        print(f"{'='*70}")

        # Load world and apply overrides
        world = load_world(world_path)
        for actor in world.actors:
            if actor.actor_id in variant["overrides"]:
                overrides = variant["overrides"][actor.actor_id]
                if "risk_tolerance" in overrides:
                    actor.doctrine.risk_tolerance = overrides["risk_tolerance"]
                if "cooperation_bias" in overrides:
                    actor.doctrine.cooperation_bias = overrides["cooperation_bias"]
                if "escalation_bias" in overrides:
                    actor.doctrine.escalation_bias = overrides["escalation_bias"]

        runner = SimulationRunner(
            world,
            seed=42,
            output_dir="logs/replays",
            agent_type=agent_type,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            world_path=world_path,
        )
        replay = runner.run()

        # Compare against ground truth
        truth = load_ground_truth(truth_path)
        # Quick accuracy calc
        all_scores = []
        for turn_truth in truth["turns"]:
            turn_num = turn_truth["turn"]
            if turn_num > len(replay.turns):
                break
            sim_turn = replay.turns[turn_num - 1]
            for actor_id, real_action_data in turn_truth["real_actions"].items():
                sim_action = next(
                    (a for a in sim_turn.actions if a.get("actor_id") == actor_id), None
                )
                if sim_action:
                    all_scores.append(
                        score_action_match(sim_action["action_type"], real_action_data["action_type"])
                    )

        accuracy = sum(all_scores) / len(all_scores) if all_scores else 0.0
        final_scores = replay.final_scores

        results.append({
            "variant": variant_name,
            "description": variant["description"],
            "accuracy_vs_reality": round(accuracy, 3),
            "final_leaderboard": final_scores,
        })

    # ── Summary table ───────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  VARIANT COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Variant':<25} {'Accuracy':>10} {'Top Actor':<25} {'Score':>8}")
    print(f"  {'-'*25} {'-'*10} {'-'*25} {'-'*8}")
    for r in sorted(results, key=lambda x: -x["accuracy_vs_reality"]):
        top = r["final_leaderboard"][0] if r["final_leaderboard"] else {"name": "N/A", "final_score": 0}
        print(
            f"  {r['variant']:<25} {r['accuracy_vs_reality']:>9.1%} "
            f"{top['name']:<25} {top['final_score']:>7.1f}"
        )
    print()

    # Save results
    output_path = Path("logs/metrics/variant_comparison.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"  Results saved to: {output_path}")

    return results


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Hormuz Crisis Backtest")
    parser.add_argument("--agent", "-a", choices=["mock", "llm"], default="mock")
    parser.add_argument("--model", "-m", default="big-pickle")
    parser.add_argument("--key", "-k", default=None)
    parser.add_argument("--provider", "-p", default=None)
    parser.add_argument("--variants", action="store_true", help="Run all doctrine variants")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    api_key = args.key or os.environ.get("OPENCODE_ZEN_API_KEY")

    if args.agent == "llm" and not api_key:
        print("ERROR: LLM agent requires API key. Set OPENCODE_ZEN_API_KEY or use --key")
        sys.exit(1)

    if args.variants:
        run_variants(
            agent_type=args.agent,
            llm_model=args.model,
            llm_api_key=api_key,
        )
    else:
        report = backtest(
            seed=args.seed,
            agent_type=args.agent,
            llm_model=args.model,
            llm_api_key=api_key,
            llm_provider=args.provider,
        )
        print_report(report)

        # Save report
        output_path = Path("logs/metrics/backtest_report.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"  Report saved to: {output_path}")


if __name__ == "__main__":
    main()
