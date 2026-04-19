"""
FastAPI backend for the World Engine frontend.

Wraps existing simulation engine, runner, and backtesting harness as REST endpoints.
CORS enabled for local React dev server.

Run with: uvicorn api.server:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import json as json_module
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import StreamingResponse

# Add project root to path — must come before any local imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# Also set as env var so subprocesses inherit it
os.environ.setdefault("PYTHONPATH", str(PROJECT_ROOT))

app = FastAPI(
    title="World Engine API",
    description="Geopolitical Simulation Backend",
    version="1.0.0",
)

# CORS — allow local dev + Vercel production/preview deploys
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

# Allow any Vercel preview/production URL
VERCEL_ORIGIN = os.environ.get("FRONTEND_URL", "")
if VERCEL_ORIGIN:
    ALLOWED_ORIGINS.append(VERCEL_ORIGIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Path Helpers ────────────────────────────────────────────────────────────

SCENARIOS_DIR = PROJECT_ROOT / "scenarios" / "seed_worlds"
REPLAYS_DIR = PROJECT_ROOT / "logs" / "replays"
METRICS_DIR = PROJECT_ROOT / "logs" / "metrics"
BENCHMARKS_DIR = Path(os.path.join(os.path.dirname(__file__), "..", "logs", "benchmarks"))
GROUND_TRUTH_PATH = PROJECT_ROOT / "scenarios" / "hormuz_ground_truth.json"


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Request/Response Models ─────────────────────────────────────────────────

class ActorModelAssignment(BaseModel):
    """Per-actor model assignment for mixed-model simulations."""
    actor_id: str
    model: str
    provider: str = "zen"
    temperature: float = 0.7


class SimulateRequest(BaseModel):
    scenario: str = "hormuz_crisis_apr8"
    agent_type: str = "mock"
    seed: int = 42
    llm_model: str = "big-pickle"                       # default model for all actors
    llm_api_key: Optional[str] = None
    # NEW: per-actor model overrides (mixed-model mode)
    actor_models: Optional[list[ActorModelAssignment]] = None  # e.g. [{"actor_id": "usa", "model": "gpt-5-nano"}, ...]


class BacktestRequest(BaseModel):
    agent_type: str = "mock"
    seed: int = 42
    run_variants: bool = False
    llm_model: str = "big-pickle"
    llm_api_key: Optional[str] = None


class BenchmarkRequest(BaseModel):
    name: str = "benchmark_001"
    scenarios: list[str] = ["hormuz_crisis_apr8"]
    models: list[dict] = [{"model": "big-pickle", "provider": "zen", "temperature": 0.7}]
    seeds: list[int] = [42]
    agent_type: str = "llm"
    api_key: Optional[str] = None
    # NEW: mixed-model configurations — each entry maps actor_id → model config
    # e.g. [{"usa": {"model": "gpt-5-nano"}, "israel": {"model": "big-pickle"}}]
    # If provided, these are run IN ADDITION to the homogeneous model sweeps
    mixed_configs: Optional[list[dict]] = None


# ── Scenario Endpoints ──────────────────────────────────────────────────────

@app.get("/api/scenarios")
def list_scenarios():
    """List all available scenario files."""
    scenarios = []
    if SCENARIOS_DIR.exists():
        for f in sorted(SCENARIOS_DIR.glob("*.json")):
            data = _load_json(f)
            scenarios.append({
                "id": f.stem,
                "name": data.get("name", f.stem),
                "world_id": data.get("world_id", f.stem),
                "turn_limit": data.get("turn_limit", 5),
                "actor_count": len(data.get("actors", [])),
                "region_count": len(data.get("regions", [])),
            })
    return {"scenarios": scenarios}


@app.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: str):
    """Get full scenario world definition."""
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Scenario '{scenario_id}' not found")
    return _load_json(path)


# ── Replay Endpoints ────────────────────────────────────────────────────────

@app.get("/api/replays")
def list_replays():
    """List all available replay files."""
    replays = []
    if REPLAYS_DIR.exists():
        for f in sorted(REPLAYS_DIR.glob("*_replay.json"), reverse=True):
            try:
                data = _load_json(f)
                world = data.get("world", {})
                replays.append({
                    "id": f.stem,
                    "filename": f.name,
                    "name": world.get("name", f.stem),
                    "world_id": world.get("world_id", ""),
                    "turns": len(data.get("turns", [])),
                    "actor_count": len(world.get("actors", [])),
                    "agent_type": data.get("metadata", {}).get("agent_type", "unknown"),
                })
            except Exception:
                continue
    return {"replays": replays}


@app.get("/api/replays/{replay_id}")
def get_replay(replay_id: str):
    """Get full replay data (world + turns + scores)."""
    path = REPLAYS_DIR / f"{replay_id}.json"
    if not path.exists():
        # Try without _replay suffix
        path = REPLAYS_DIR / f"{replay_id}_replay.json"
    if not path.exists():
        raise HTTPException(404, f"Replay '{replay_id}' not found")
    return _load_json(path)


# ── Run Registry Endpoints ──────────────────────────────────────────────────

@app.get("/api/runs")
def list_runs(scenario: Optional[str] = None, model: Optional[str] = None):
    """List all runs with their configs. Scans replay files for run_config."""
    runs = []
    for path in sorted(REPLAYS_DIR.glob("*_replay.json"), reverse=True):
        try:
            data = _load_json(path)
        except Exception:
            continue

        config = data.get("run_config", {})
        meta = data.get("metadata", {})

        run_info = {
            "run_id": config.get("run_id", meta.get("run_id", path.stem.replace("_replay", ""))),
            "scenario": data.get("world", {}).get("world_id", "unknown") if isinstance(data.get("world"), dict) else "unknown",
            "model": config.get("global_model", meta.get("model")),
            "seed": config.get("seed", meta.get("seed")),
            "agent_type": config.get("global_agent_type", meta.get("agent_type")),
            "turns": len(data.get("turns", [])),
            "started_at": config.get("started_at"),
            "filename": path.name,
        }

        # Apply filters
        if scenario and run_info["scenario"] != scenario:
            continue
        if model and run_info["model"] != model:
            continue

        runs.append(run_info)
    return runs


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    """Get a specific run's full replay by run_id."""
    # Search for matching replay file
    for path in REPLAYS_DIR.glob("*_replay.json"):
        try:
            data = _load_json(path)
        except Exception:
            continue
        config = data.get("run_config", {})
        meta = data.get("metadata", {})
        rid = config.get("run_id", meta.get("run_id", path.stem.replace("_replay", "")))
        if rid == run_id or path.stem.replace("_replay", "") == run_id:
            return data
    raise HTTPException(404, f"Run {run_id} not found")


@app.get("/api/runs/{run_id}/traces")
def get_run_traces(run_id: str, actor: Optional[str] = None, turn: Optional[int] = None):
    """Get all LLM traces for a run, optionally filtered."""
    data = get_run(run_id)  # Reuse the get_run function

    traces = []
    for turn_record in data.get("turns", []):
        for trace in turn_record.get("traces", []):
            if actor and trace.get("actor_id") != actor:
                continue
            if turn is not None and trace.get("turn") != turn:
                continue
            traces.append(trace)

    # Compute summary stats
    total_tokens = sum((t.get("prompt_tokens") or 0) + (t.get("completion_tokens") or 0) for t in traces)
    total_latency = sum(t.get("latency_ms", 0) for t in traces)
    coerced = sum(1 for t in traces if t.get("was_coerced"))

    return {
        "run_id": run_id,
        "total_traces": len(traces),
        "total_tokens": total_tokens,
        "total_latency_ms": round(total_latency, 1),
        "coercion_count": coerced,
        "coercion_rate": round(coerced / max(len(traces), 1), 3),
        "traces": traces,
    }


@app.get("/api/runs/{run_id}/events")
def get_run_events(run_id: str, actor: Optional[str] = None, turn: Optional[int] = None):
    """Get all structured resolution events for a run."""
    data = get_run(run_id)

    events = []
    for turn_record in data.get("turns", []):
        for event in turn_record.get("resolution_events", []):
            if actor and event.get("actor_id") != actor:
                continue
            if turn is not None and event.get("turn") != turn:
                continue
            events.append(event)

    return {
        "run_id": run_id,
        "total_events": len(events),
        "success_count": sum(1 for e in events if e.get("success")),
        "failure_count": sum(1 for e in events if not e.get("success")),
        "events": events,
    }


# ── Comparison Endpoint ─────────────────────────────────────────────────────

@app.get("/api/compare")
def compare_runs(run_ids: str):
    """Compare 2+ runs. Accepts comma-separated run_ids."""
    ids = [rid.strip() for rid in run_ids.split(",") if rid.strip()]
    if len(ids) < 2:
        raise HTTPException(400, "Need at least 2 run_ids (comma-separated)")

    replays = {}
    for rid in ids:
        try:
            replays[rid] = get_run(rid)
        except HTTPException:
            raise HTTPException(404, f"Run {rid} not found")

    # Build comparison
    comparison = {
        "run_ids": ids,
        "configs": {},
        "score_comparison": {},
        "action_comparison": {},
        "trace_stats": {},
    }

    for rid, data in replays.items():
        config = data.get("run_config", data.get("metadata", {}))
        comparison["configs"][rid] = {
            "model": config.get("global_model", config.get("model")),
            "agent_type": config.get("global_agent_type", config.get("agent_type")),
            "seed": config.get("seed"),
        }

        # Final scores
        comparison["score_comparison"][rid] = {}
        for entry in data.get("final_scores", []):
            if isinstance(entry, dict):
                comparison["score_comparison"][rid][entry.get("actor_id", "?")] = entry.get("final_score", 0)

        # Per-turn actions
        comparison["action_comparison"][rid] = []
        for turn_record in data.get("turns", []):
            turn_actions = {}
            t = turn_record.get("turn", 0) if isinstance(turn_record, dict) else getattr(turn_record, "turn", 0)
            actions = turn_record.get("actions", []) if isinstance(turn_record, dict) else getattr(turn_record, "actions", [])
            for action in actions:
                if isinstance(action, dict):
                    turn_actions[action.get("actor_id", "?")] = {
                        "action_type": action.get("action_type"),
                        "target": action.get("target"),
                        "rationale": action.get("rationale", "")[:200],
                    }
            comparison["action_comparison"][rid].append({"turn": t, "actions": turn_actions})

        # Trace stats
        traces = []
        for turn_record in data.get("turns", []):
            tr = turn_record if isinstance(turn_record, dict) else turn_record.__dict__
            traces.extend(tr.get("traces", []))

        total_tokens = sum((t.get("prompt_tokens") or 0) + (t.get("completion_tokens") or 0) for t in traces)
        comparison["trace_stats"][rid] = {
            "total_traces": len(traces),
            "total_tokens": total_tokens,
            "total_latency_ms": round(sum(t.get("latency_ms", 0) for t in traces), 1),
            "coercion_count": sum(1 for t in traces if t.get("was_coerced")),
        }

    # Compute diffs between first two runs
    if len(ids) >= 2:
        id_a, id_b = ids[0], ids[1]
        score_diffs = {}
        scores_a = comparison["score_comparison"].get(id_a, {})
        scores_b = comparison["score_comparison"].get(id_b, {})
        for actor_id in set(list(scores_a.keys()) + list(scores_b.keys())):
            sa = scores_a.get(actor_id, 0)
            sb = scores_b.get(actor_id, 0)
            score_diffs[actor_id] = {"run_a": sa, "run_b": sb, "delta": round(sb - sa, 2)}
        comparison["score_diffs"] = score_diffs

        # Action diffs per turn
        action_diffs = []
        actions_a = comparison["action_comparison"].get(id_a, [])
        actions_b = comparison["action_comparison"].get(id_b, [])
        for ta, tb in zip(actions_a, actions_b):
            turn_diff = {"turn": ta.get("turn", 0), "diffs": {}}
            for actor_id in set(list(ta.get("actions", {}).keys()) + list(tb.get("actions", {}).keys())):
                aa = ta.get("actions", {}).get(actor_id, {})
                ab = tb.get("actions", {}).get(actor_id, {})
                if aa.get("action_type") != ab.get("action_type") or aa.get("target") != ab.get("target"):
                    turn_diff["diffs"][actor_id] = {
                        "run_a": f"{aa.get('action_type', '?')} -> {aa.get('target', 'none')}",
                        "run_b": f"{ab.get('action_type', '?')} -> {ab.get('target', 'none')}",
                    }
            if turn_diff["diffs"]:
                action_diffs.append(turn_diff)
        comparison["action_diffs"] = action_diffs

    return comparison


# ── Backtest Endpoints ──────────────────────────────────────────────────────

@app.get("/api/backtest/report")
def get_backtest_report():
    """Get the latest backtest report."""
    path = METRICS_DIR / "backtest_report.json"
    if not path.exists():
        raise HTTPException(404, "No backtest report found. Run a backtest first.")
    return _load_json(path)


@app.get("/api/backtest/variants")
def get_variant_comparison():
    """Get branching variant comparison results."""
    path = METRICS_DIR / "variant_comparison.json"
    if not path.exists():
        raise HTTPException(404, "No variant comparison found. Run backtest with --variants.")
    return _load_json(path)


@app.get("/api/backtest/ground-truth")
def get_ground_truth():
    """Get the ground truth timeline data."""
    if not GROUND_TRUTH_PATH.exists():
        raise HTTPException(404, "Ground truth file not found")
    return _load_json(GROUND_TRUTH_PATH)


# ── Simulation Endpoints ────────────────────────────────────────────────────

# Simple in-memory job tracking for async simulation runs
_jobs: dict[str, dict] = {}
# Turn-by-turn progress for streaming
_job_turns: dict[str, list[dict]] = {}  # job_id -> list of completed turn dicts


@app.post("/api/simulate")
def run_simulation_endpoint(req: SimulateRequest, background_tasks: BackgroundTasks):
    """Start a new simulation run (async). Returns job_id to poll."""
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}

    def _run():
        try:
            from app.runner import SimulationRunner, load_world
            scenario_path = SCENARIOS_DIR / f"{req.scenario}.json"
            if not scenario_path.exists():
                _jobs[job_id] = {"status": "error", "result": None, "error": f"Scenario not found: {req.scenario}"}
                return

            # Build per-actor config overrides for mixed-model mode
            actor_agent_configs = {}
            if req.actor_models:
                for assignment in req.actor_models:
                    actor_agent_configs[assignment.actor_id] = {
                        "agent_type": "llm",
                        "model": assignment.model,
                        "provider": assignment.provider,
                        "temperature": assignment.temperature,
                        "api_key": req.llm_api_key,
                    }

            # Track turns in real-time for SSE streaming
            _job_turns[job_id] = []

            def _on_turn(turn_num, turn_data):
                """Callback invoked after each turn completes."""
                _job_turns[job_id].append({
                    "turn": turn_num,
                    "data": turn_data,
                })

            world = load_world(str(scenario_path))
            runner = SimulationRunner(
                world=world,
                seed=req.seed,
                agent_type=req.agent_type,
                llm_model=req.llm_model,
                llm_api_key=req.llm_api_key,
                world_path=str(scenario_path),
                actor_agent_configs=actor_agent_configs,
                on_turn_complete=_on_turn,
                llm_call_delay=2.0,
            )
            replay = runner.run()
            _jobs[job_id] = {"status": "complete", "result": replay.model_dump(), "error": None}
        except Exception as e:
            _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "running"}


@app.get("/api/simulate/{job_id}")
def get_simulation_status(job_id: str):
    """Poll simulation job status."""
    if job_id not in _jobs:
        raise HTTPException(404, f"Job '{job_id}' not found")
    job = _jobs[job_id]
    return {"job_id": job_id, "status": job["status"], "error": job.get("error")}


@app.get("/api/simulate/{job_id}/result")
def get_simulation_result(job_id: str):
    """Get completed simulation result."""
    if job_id not in _jobs:
        raise HTTPException(404, f"Job '{job_id}' not found")
    job = _jobs[job_id]
    if job["status"] != "complete":
        raise HTTPException(409, f"Job is {job['status']}, not complete")
    return job["result"]


@app.get("/api/simulate/{job_id}/stream")
async def stream_simulation(job_id: str):
    """Stream simulation progress via Server-Sent Events.
    
    Each event contains a completed turn's data.
    Use from frontend: const es = new EventSource('/api/simulate/{job_id}/stream')
    """
    if job_id not in _jobs:
        raise HTTPException(404, f"Job '{job_id}' not found")

    async def event_generator():
        last_sent = 0
        while True:
            job = _jobs.get(job_id, {})
            turns = _job_turns.get(job_id, [])

            # Send any new turns
            while last_sent < len(turns):
                turn_data = turns[last_sent]
                # Simplify the turn data for streaming (don't send full state snapshots)
                summary = {
                    "turn": turn_data["turn"],
                    "actions": turn_data["data"].get("actions", []),
                    "resolutions": turn_data["data"].get("resolutions", []),
                    "scores": turn_data["data"].get("scores", []),
                    "public_news": turn_data["data"].get("public_news", []),
                    "public_statements": turn_data["data"].get("public_statements", {}),
                    "traces": [
                        {
                            "actor_id": t.get("actor_id"),
                            "model": t.get("model"),
                            "latency_ms": t.get("latency_ms"),
                            "parse_success": t.get("parse_success"),
                            "was_coerced": t.get("was_coerced"),
                        }
                        for t in turn_data["data"].get("traces", [])
                    ],
                }
                yield f"event: turn\ndata: {json_module.dumps(summary, default=str)}\n\n"
                last_sent += 1

            # Check if simulation is done
            if job.get("status") in ("complete", "error"):
                final = {"status": job["status"]}
                if job.get("error"):
                    final["error"] = job["error"]
                yield f"event: done\ndata: {json_module.dumps(final)}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/simulate/{job_id}/turns")
def get_simulation_turns(job_id: str):
    """Get completed turns so far for a running simulation (polling alternative to SSE)."""
    if job_id not in _jobs:
        raise HTTPException(404, f"Job '{job_id}' not found")
    turns = _job_turns.get(job_id, [])
    job = _jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "completed_turns": len(turns),
        "turns": [
            {
                "turn": t["turn"],
                "actions": t["data"].get("actions", []),
                "resolutions": t["data"].get("resolutions", []),
                "scores": t["data"].get("scores", []),
                "public_news": t["data"].get("public_news", []),
            }
            for t in turns
        ],
    }


# ── Backtest Run Endpoint ───────────────────────────────────────────────────

@app.post("/api/backtest/run")
def run_backtest_endpoint(req: BacktestRequest, background_tasks: BackgroundTasks):
    """Start a backtest run (async)."""
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}

    def _run():
        try:
            from app.backtest import backtest, run_variants
            if req.run_variants:
                results = run_variants(agent_type=req.agent_type, llm_model=req.llm_model, llm_api_key=req.llm_api_key)
                _jobs[job_id] = {"status": "complete", "result": results, "error": None}
            else:
                report = backtest(seed=req.seed, agent_type=req.agent_type, llm_model=req.llm_model, llm_api_key=req.llm_api_key)
                # Save to disk
                output_path = METRICS_DIR / "backtest_report.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, default=str)
                _jobs[job_id] = {"status": "complete", "result": report, "error": None}
        except Exception as e:
            _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "running"}


# ── Benchmark Endpoint ──────────────────────────────────────────────────────

@app.post("/api/benchmark")
def run_benchmark_endpoint(req: BenchmarkRequest, background_tasks: BackgroundTasks):
    """Trigger a multi-model benchmark sweep as a background job."""
    job_id = f"bench_{str(uuid.uuid4())[:8]}"
    _jobs[job_id] = {"status": "running", "type": "benchmark", "result": None, "error": None}

    def _run():
        try:
            from app.benchmark import BenchmarkRunner, BenchmarkConfig

            scenario_paths = []
            for s in req.scenarios:
                # Resolve scenario name to path
                path = SCENARIOS_DIR / "seed_worlds" / f"{s}.json"
                if path.exists():
                    scenario_paths.append(str(path))
                else:
                    scenario_paths.append(s)

            config = BenchmarkConfig(
                name=req.name,
                scenarios=scenario_paths,
                models=req.models,
                seeds=req.seeds,
                agent_type=req.agent_type,
                api_key=req.api_key,
                mixed_configs=req.mixed_configs or [],
            )
            runner = BenchmarkRunner(config)
            report = runner.run()
            _jobs[job_id]["result"] = report
            _jobs[job_id]["status"] = "completed"
        except Exception as e:
            _jobs[job_id]["error"] = str(e)
            _jobs[job_id]["status"] = "failed"

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "running"}


# ── Health ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def _eager_imports():
    """Eagerly import simulation modules to catch path issues on boot, not in background tasks."""
    try:
        from env.world_schema import World, GameState  # noqa: F401
        from env.engine import resolve_actions  # noqa: F401
        from app.runner import SimulationRunner  # noqa: F401
        print(f"[startup] All simulation modules loaded. PROJECT_ROOT={PROJECT_ROOT}")
    except ImportError as e:
        print(f"[startup] WARNING: Import failed: {e}")
        print(f"[startup] sys.path = {sys.path[:5]}")
        print(f"[startup] PROJECT_ROOT = {PROJECT_ROOT}")
        print(f"[startup] Contents: {list(PROJECT_ROOT.iterdir()) if PROJECT_ROOT.exists() else 'NOT FOUND'}")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
