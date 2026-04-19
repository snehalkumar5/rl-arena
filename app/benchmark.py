"""Benchmark runner — sweeps models x seeds x scenarios.

Aggregates cost/latency/coercion statistics and final leaderboards across a
matrix of (scenario, model, seed) tuples. Intended for head-to-head model
comparisons and reproducibility audits.
"""
from __future__ import annotations

import json
import datetime
import itertools
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.runner import SimulationRunner, load_world


@dataclass
class BenchmarkConfig:
    """Defines a benchmark sweep."""
    name: str = "benchmark_001"
    scenarios: list[str] = field(default_factory=lambda: [])
    models: list[dict] = field(default_factory=lambda: [
        {"model": "big-pickle", "provider": "zen", "temperature": 0.7}
    ])
    seeds: list[int] = field(default_factory=lambda: [42])
    agent_type: str = "llm"
    output_dir: str = "logs/benchmarks"
    api_key: Optional[str] = None
    # Mixed-model configs: each entry is {actor_id: {model, provider, temperature}}
    # e.g. [{"usa": {"model": "gpt-5-nano"}, "israel": {"model": "big-pickle"}}]
    mixed_configs: list[dict] = field(default_factory=list)


@dataclass 
class BenchmarkResult:
    """Result of a single run within a benchmark."""
    run_id: str = ""
    scenario: str = ""
    model: str = ""                    # "mixed" for mixed-model runs
    provider: str = ""
    seed: int = 42
    replay_path: str = ""
    final_leaderboard: list = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    total_api_calls: int = 0
    coercion_count: int = 0
    error: Optional[str] = None
    actor_model_map: dict = field(default_factory=dict)  # {actor_id: model_name} for mixed runs


class BenchmarkRunner:
    """Runs a matrix of (scenario x model x seed) and aggregates results."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: list[BenchmarkResult] = []

    def run(self) -> dict:
        """Execute the full benchmark sweep. Returns aggregate report."""
        matrix = list(itertools.product(
            self.config.scenarios,
            self.config.models,
            self.config.seeds,
        ))

        print(f"\n{'='*60}")
        print(f"BENCHMARK: {self.config.name}")
        print(
            f"Matrix: {len(self.config.scenarios)} scenarios x "
            f"{len(self.config.models)} models x "
            f"{len(self.config.seeds)} seeds = {len(matrix)} runs"
        )
        print(f"{'='*60}\n")

        for i, (scenario_path, model_cfg, seed) in enumerate(matrix):
            print(
                f"\n--- Run {i+1}/{len(matrix)}: "
                f"{model_cfg.get('model', '?')} seed={seed} "
                f"scenario={Path(scenario_path).name} ---"
            )
            try:
                result = self._run_single(scenario_path, model_cfg, seed)
            except Exception as e:
                result = BenchmarkResult(
                    scenario=scenario_path,
                    model=model_cfg.get("model", "?"),
                    provider=model_cfg.get("provider", "?"),
                    seed=seed,
                    error=str(e),
                )
                print(f"  ERROR: {e}")
            self.results.append(result)

        # ── Mixed-model runs ────────────────────────────────────────
        if self.config.mixed_configs:
            mixed_matrix = list(itertools.product(
                self.config.scenarios,
                self.config.mixed_configs,
                self.config.seeds,
            ))
            print(f"\n--- Mixed-model runs: {len(mixed_matrix)} ---")
            for i, (scenario_path, actor_models, seed) in enumerate(mixed_matrix):
                label = "+".join(f"{aid}={cfg.get('model','?')}" for aid, cfg in sorted(actor_models.items()))
                print(f"\n--- Mixed {i+1}/{len(mixed_matrix)}: {label} seed={seed} ---")
                try:
                    result = self._run_mixed(scenario_path, actor_models, seed)
                except Exception as e:
                    result = BenchmarkResult(
                        scenario=scenario_path,
                        model="mixed",
                        seed=seed,
                        error=str(e),
                        actor_model_map={aid: cfg.get("model", "?") for aid, cfg in actor_models.items()},
                    )
                    print(f"  ERROR: {e}")
                self.results.append(result)

        report = self._aggregate()
        self._save_report(report)
        return report

    def _run_single(self, scenario_path: str, model_cfg: dict, seed: int) -> BenchmarkResult:
        world = load_world(scenario_path)

        runner = SimulationRunner(
            world=world,
            seed=seed,
            output_dir=self.config.output_dir,
            agent_type=self.config.agent_type,
            llm_model=model_cfg.get("model", "big-pickle"),
            llm_api_key=self.config.api_key,
            llm_provider=model_cfg.get("provider", "zen"),
            llm_temperature=model_cfg.get("temperature", 0.7),
            world_path=scenario_path,
        )
        replay = runner.run()

        # Extract trace statistics from replay
        total_tokens = 0
        total_latency = 0.0
        total_calls = 0
        coercions = 0

        turns_data = replay.turns if hasattr(replay, "turns") else []
        for turn_record in turns_data:
            if hasattr(turn_record, "traces"):
                traces = turn_record.traces
            elif isinstance(turn_record, dict):
                traces = turn_record.get("traces", [])
            else:
                traces = []

            for trace in traces:
                # Normalize model/dict
                if hasattr(trace, "model_dump"):
                    trace = trace.model_dump()
                if not isinstance(trace, dict):
                    continue
                total_calls += 1
                total_tokens += (trace.get("prompt_tokens") or 0) + (trace.get("completion_tokens") or 0)
                total_latency += trace.get("latency_ms", 0) or 0
                if trace.get("was_coerced"):
                    coercions += 1

        replay_path = str(Path(self.config.output_dir) / f"{runner.run_id}_replay.json")

        final_scores = replay.final_scores if hasattr(replay, "final_scores") else []

        return BenchmarkResult(
            run_id=runner.run_id,
            scenario=world.world_id,
            model=model_cfg.get("model", "big-pickle"),
            provider=model_cfg.get("provider", "zen"),
            seed=seed,
            replay_path=replay_path,
            final_leaderboard=final_scores,
            total_tokens=total_tokens,
            total_latency_ms=total_latency,
            total_api_calls=total_calls,
            coercion_count=coercions,
        )

    def _run_mixed(self, scenario_path: str, actor_models: dict, seed: int) -> BenchmarkResult:
        """Run a single simulation with different models assigned to different actors.
        
        actor_models: {actor_id: {"model": "gpt-5-nano", "provider": "zen", "temperature": 0.7}}
        """
        world = load_world(scenario_path)

        # Build per-actor agent configs
        actor_agent_configs = {}
        for actor_id, cfg in actor_models.items():
            actor_agent_configs[actor_id] = {
                "agent_type": "llm",
                "model": cfg.get("model", "big-pickle"),
                "provider": cfg.get("provider", "zen"),
                "temperature": cfg.get("temperature", 0.7),
                "api_key": self.config.api_key,
            }

        runner = SimulationRunner(
            world=world,
            seed=seed,
            output_dir=self.config.output_dir,
            agent_type=self.config.agent_type,
            llm_model="big-pickle",  # default for actors not in actor_models
            llm_api_key=self.config.api_key,
            llm_provider="zen",
            world_path=scenario_path,
            actor_agent_configs=actor_agent_configs,
        )
        replay = runner.run()

        # Extract trace stats (same as _run_single)
        total_tokens = 0
        total_latency = 0.0
        total_calls = 0
        coercions = 0
        turns_data = replay.turns if hasattr(replay, "turns") else []
        for turn_record in turns_data:
            if hasattr(turn_record, "traces"):
                traces = turn_record.traces
            elif isinstance(turn_record, dict):
                traces = turn_record.get("traces", [])
            else:
                traces = []
            for trace in traces:
                if hasattr(trace, "model_dump"):
                    trace = trace.model_dump()
                if not isinstance(trace, dict):
                    continue
                total_calls += 1
                total_tokens += (trace.get("prompt_tokens") or 0) + (trace.get("completion_tokens") or 0)
                total_latency += trace.get("latency_ms", 0) or 0
                if trace.get("was_coerced"):
                    coercions += 1

        replay_path = str(Path(self.config.output_dir) / f"{runner.run_id}_replay.json")
        final_scores = replay.final_scores if hasattr(replay, "final_scores") else []
        actor_model_map = {aid: cfg.get("model", "?") for aid, cfg in actor_models.items()}

        return BenchmarkResult(
            run_id=runner.run_id,
            scenario=world.world_id,
            model="mixed",
            provider="mixed",
            seed=seed,
            replay_path=replay_path,
            final_leaderboard=final_scores,
            total_tokens=total_tokens,
            total_latency_ms=total_latency,
            total_api_calls=total_calls,
            coercion_count=coercions,
            actor_model_map=actor_model_map,
        )

    def _aggregate(self) -> dict:
        """Aggregate results across the sweep."""
        from collections import defaultdict

        by_model = defaultdict(list)
        for r in self.results:
            by_model[r.model].append(r)

        model_summaries = {}
        for model, runs in by_model.items():
            successful = [r for r in runs if r.error is None]
            n_success = max(len(successful), 1)
            model_summaries[model] = {
                "runs": len(runs),
                "successful": len(successful),
                "failed": len(runs) - len(successful),
                "avg_tokens": sum(r.total_tokens for r in successful) / n_success,
                "avg_latency_ms": sum(r.total_latency_ms for r in successful) / n_success,
                "total_api_calls": sum(r.total_api_calls for r in successful),
                "avg_coercion_rate": (
                    sum(r.coercion_count for r in successful) /
                    max(sum(r.total_api_calls for r in successful), 1)
                ),
                "avg_final_scores": self._avg_leaderboards(
                    [r.final_leaderboard for r in successful]
                ),
            }

        return {
            "benchmark_name": self.config.name,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "total_runs": len(self.results),
            "successful_runs": sum(1 for r in self.results if r.error is None),
            "matrix": {
                "scenarios": self.config.scenarios,
                "models": [m.get("model", "?") for m in self.config.models],
                "seeds": self.config.seeds,
            },
            "model_summaries": model_summaries,
            "all_results": [
                {
                    "run_id": r.run_id,
                    "scenario": r.scenario,
                    "model": r.model,
                    "provider": r.provider,
                    "seed": r.seed,
                    "replay_path": r.replay_path,
                    "total_tokens": r.total_tokens,
                    "total_latency_ms": r.total_latency_ms,
                    "total_api_calls": r.total_api_calls,
                    "coercion_count": r.coercion_count,
                    "final_leaderboard": r.final_leaderboard,
                    "error": r.error,
                }
                for r in self.results
            ],
        }

    def _avg_leaderboards(self, leaderboards: list) -> dict:
        from collections import defaultdict
        totals = defaultdict(lambda: {"sum": 0.0, "count": 0})
        for lb in leaderboards:
            for entry in lb:
                if isinstance(entry, dict):
                    aid = entry.get("actor_id", "?")
                    totals[aid]["sum"] += entry.get("final_score", 0) or 0
                    totals[aid]["count"] += 1
        return {
            aid: round(v["sum"] / max(v["count"], 1), 2)
            for aid, v in totals.items()
        }

    def _save_report(self, report: dict):
        out = Path(self.config.output_dir) / f"{self.config.name}_benchmark.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nBenchmark report saved: {out}")
