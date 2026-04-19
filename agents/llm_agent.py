"""
LLM-backed agent adapter using OpenCode Zen or direct provider APIs.

Supports three endpoint types via OpenCode Zen gateway:
  - /v1/chat/completions  (OpenAI-compatible: GPT, Qwen, MiniMax, GLM, Kimi, Big Pickle, Nemotron)
  - /v1/messages          (Anthropic-compatible: Claude models)
  - /v1/responses         (OpenAI Responses API: GPT 5.x series)

Also supports direct OpenAI/Anthropic API keys as fallback.

DISCLAIMER: Simulation outputs are speculative and not intelligence products.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

from env.world_schema import (
    Actor, ActorObservation, AgentTurnOutput, ActionPayload,
    DiplomaticMessage, STATE_ACTIONS, NON_STATE_ACTIONS,
)
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Load prompt templates
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


ACTOR_POLICY_PROMPT = _load_prompt("actor_policy.txt")
REPAIR_PROMPT = (
    "The following text was supposed to be valid JSON matching the schema but it is broken. "
    "Repair it into valid JSON. Output ONLY the repaired JSON, no explanation."
)

# ── Zen model routing ───────────────────────────────────────────────────────

# Models that use the Anthropic /messages endpoint
ANTHROPIC_MODELS = {
    "claude-opus-4-7", "claude-opus-4-6", "claude-opus-4-5", "claude-opus-4-1",
    "claude-sonnet-4-6", "claude-sonnet-4-5", "claude-sonnet-4",
    "claude-haiku-4-5", "claude-3-5-haiku",
}

# Models that use the OpenAI /responses endpoint
RESPONSES_MODELS = {
    "gpt-5.4", "gpt-5.4-pro", "gpt-5.4-mini", "gpt-5.4-nano",
    "gpt-5.3-codex", "gpt-5.3-codex-spark",
    "gpt-5.2", "gpt-5.2-codex",
    "gpt-5.1", "gpt-5.1-codex", "gpt-5.1-codex-max", "gpt-5.1-codex-mini",
    "gpt-5", "gpt-5-codex", "gpt-5-nano",
}

# Models that use /chat/completions (everything else)
CHAT_COMPLETIONS_MODELS = {
    "qwen3.6-plus", "qwen3.5-plus",
    "minimax-m2.5", "minimax-m2.5-free",
    "glm-5.1", "glm-5",
    "kimi-k2.5",
    "big-pickle",
    "nemotron-3-super-free",
}

# Free models (no cost)
FREE_MODELS = {"gpt-5-nano", "big-pickle", "nemotron-3-super-free", "minimax-m2.5-free"}

ZEN_BASE_URL = "https://opencode.ai/zen/v1"


def _detect_endpoint(model: str) -> str:
    """Determine which API endpoint type to use for a model."""
    if model in ANTHROPIC_MODELS:
        return "anthropic"
    if model in RESPONSES_MODELS:
        return "responses"
    # Default to chat completions (most compatible)
    return "chat_completions"


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    if not text:
        return '{"action": {"action_type": "hold"}, "rationale": "Empty LLM response"}'

    # Try to extract from ```json ... ``` blocks
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try to find a JSON object directly
    # Look for the outermost { ... }
    brace_start = text.find('{')
    if brace_start != -1:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    return text[brace_start:i + 1]

    return text


class LLMAgent(BaseAgent):
    """
    Agent backed by an LLM via OpenCode Zen or direct provider APIs.

    Usage:
        # Via OpenCode Zen (recommended)
        agent = LLMAgent(actor, model="big-pickle", api_key="your-zen-key")

        # Via OpenCode Zen with Claude
        agent = LLMAgent(actor, model="claude-sonnet-4", api_key="your-zen-key")

        # Direct OpenAI API
        agent = LLMAgent(actor, model="gpt-4o", api_key="sk-...", provider="openai")

        # Direct Anthropic API
        agent = LLMAgent(actor, model="claude-sonnet-4-20250514", api_key="sk-ant-...", provider="anthropic")

    Free models (no cost via Zen):
        big-pickle, nemotron-3-super-free, minimax-m2.5-free, gpt-5-nano
    """

    def __init__(
        self,
        actor: Actor,
        model: str = "big-pickle",
        api_key: Optional[str] = None,
        provider: Optional[str] = None,  # "zen", "openai", "anthropic" -- auto-detected if None
        max_retries: int = 3,
        temperature: float = 0.7,
    ):
        super().__init__(actor.actor_id, actor.name)
        self.actor = actor
        self.model = model
        self.api_key = api_key or os.environ.get("OPENCODE_ZEN_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        self.max_retries = max_retries
        self.temperature = temperature

        # Auto-detect provider
        if provider:
            self.provider = provider
        elif model in ANTHROPIC_MODELS or model in RESPONSES_MODELS or model in CHAT_COMPLETIONS_MODELS:
            self.provider = "zen"
        elif self.api_key and self.api_key.startswith("sk-ant-"):
            self.provider = "anthropic"
        else:
            self.provider = "openai"

        self._provider_name = provider or "zen"
        self._last_traces: list = []
        self.endpoint_type = _detect_endpoint(model)

        # Initialize clients lazily
        self._openai_client = None
        self._anthropic_client = None

    @property
    def openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI
            if self.provider == "zen":
                self._openai_client = OpenAI(
                    api_key=self.api_key,
                    base_url=ZEN_BASE_URL,
                )
            else:
                self._openai_client = OpenAI(api_key=self.api_key)
        return self._openai_client

    @property
    def anthropic_client(self):
        if self._anthropic_client is None:
            from anthropic import Anthropic
            if self.provider == "zen":
                self._anthropic_client = Anthropic(
                    api_key=self.api_key,
                    base_url=ZEN_BASE_URL,
                )
            else:
                self._anthropic_client = Anthropic(api_key=self.api_key)
        return self._anthropic_client

    def _build_system_prompt(self) -> str:
        """Construct the system prompt for this actor."""
        doctrine = self.actor.doctrine
        return (
            f"{ACTOR_POLICY_PROMPT}\n\n"
            f"You are playing as: {self.actor.name} ({self.actor.archetype})\n"
            f"Actor type: {self.actor.actor_type}\n"
            f"Doctrine: risk_tolerance={doctrine.risk_tolerance}, "
            f"cooperation_bias={doctrine.cooperation_bias}, "
            f"escalation_bias={doctrine.escalation_bias}\n\n"
            f"IMPORTANT: You must output ONLY valid JSON. No markdown, no commentary, no explanation."
        )

    def _build_user_prompt(self, observation: ActorObservation) -> str:
        """Construct the user prompt with the observation packet."""
        packet = {
            "actor_profile": observation.actor_profile,
            "private_brief": observation.private_obs.private_brief,
            "public_world_state": observation.public_obs.model_dump(),
            "inbox_messages": [m.model_dump() for m in observation.private_obs.inbox_messages],
            "memory_summary": observation.memory_summary,
            "legal_actions": observation.legal_actions,
            "resource_update": observation.private_obs.resource_update,
        }
        return (
            "Here is your current observation. Respond with your decision as JSON.\n\n"
            + json.dumps(packet, indent=2)
        )

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM API and return the raw text response."""
        if self.endpoint_type == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt)
        else:
            # Both chat_completions and responses use the OpenAI SDK
            return self._call_openai(system_prompt, user_prompt)

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Call via OpenAI chat completions endpoint."""
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=1500,
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call via Anthropic messages endpoint."""
        response = self.anthropic_client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=1500,
        )
        # Extract text from content blocks
        return "".join(
            block.text for block in response.content if hasattr(block, "text")
        )

    # ── Traced LLM call ────────────────────────────────────────────────────

    def _call_llm_traced(self, system_prompt: str, user_prompt: str,
                          turn: int, run_id: str) -> tuple:
        """Call LLM and return (raw_text, trace_dict).
        Returns a dict instead of LLMTrace to avoid import issues during transition."""
        trace = {
            "trace_id": uuid.uuid4().hex[:12],
            "run_id": run_id,
            "turn": turn,
            "actor_id": self.actor_id,
            "model": self.model,
            "provider": self._provider_name,
            "temperature": self.temperature,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_completion": "",
            "prompt_tokens": None,
            "completion_tokens": None,
            "finish_reason": None,
            "parse_success": False,
            "parse_error": None,
            "repair_attempted": False,
            "repair_completion": None,
            "latency_ms": 0.0,
            "total_latency_ms": 0.0,
            "attempt_number": 0,
            "parsed_action": None,
            "was_coerced": False,
            "coercion_reason": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        start = time.perf_counter()
        try:
            if self.endpoint_type == "anthropic":
                response = self.anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=1500,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                raw = response.content[0].text
                trace["prompt_tokens"] = response.usage.input_tokens
                trace["completion_tokens"] = response.usage.output_tokens
                trace["finish_reason"] = response.stop_reason
            else:
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=1500,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                raw = response.choices[0].message.content
                if response.usage:
                    trace["prompt_tokens"] = response.usage.prompt_tokens
                    trace["completion_tokens"] = response.usage.completion_tokens
                trace["finish_reason"] = response.choices[0].finish_reason
        except Exception as e:
            trace["latency_ms"] = (time.perf_counter() - start) * 1000
            trace["parse_error"] = f"API call failed: {str(e)}"
            raise

        trace["latency_ms"] = (time.perf_counter() - start) * 1000
        trace["raw_completion"] = raw  # Full text, NOT truncated
        return raw, trace

    # ── Strict response parsing ────────────────────────────────────────────

    def _parse_response_strict(self, raw: str, observation) -> tuple:
        """Parse LLM output with strict validation.
        Returns (AgentTurnOutput, coercion_reason_or_None)."""
        json_str = _extract_json(raw)
        data = json.loads(json_str)

        coercion_reasons = []

        # Validate action_type
        legal = observation.legal_actions if hasattr(observation, 'legal_actions') and observation.legal_actions else STATE_ACTIONS + NON_STATE_ACTIONS
        action_data = data.get("action", {})
        action_type = action_data.get("action_type", "hold")
        if action_type not in legal:
            coercion_reasons.append(f"illegal_action:{action_type}->hold")
            action_type = "hold"

        # Validate target is not self
        target = action_data.get("target")
        if target and target == self.actor_id:
            coercion_reasons.append(f"self_target:{target}->None")
            target = None

        # Build validated output
        messages = data.get("private_messages", [])
        if not isinstance(messages, list):
            messages = []
        messages = messages[:2]  # Enforce max 2

        parsed_messages = []
        for m in messages:
            if isinstance(m, dict) and "to" in m and "text" in m:
                parsed_messages.append(DiplomaticMessage(to=m["to"], text=str(m["text"])))

        result = AgentTurnOutput(
            actor_id=self.actor_id,
            private_messages=parsed_messages,
            public_statement=str(data.get("public_statement", "No comment.")),
            action=ActionPayload(
                action_type=action_type,
                target=target,
                parameters=action_data.get("parameters", {}),
            ),
            rationale=str(data.get("rationale", "No rationale provided.")),
        )

        coercion = "|".join(coercion_reasons) if coercion_reasons else None
        return result, coercion

    # ── Legacy parse (kept for backwards compatibility) ────────────────────

    def _parse_response(self, raw: str) -> AgentTurnOutput:
        """Parse LLM response into structured output."""
        json_str = _extract_json(raw)
        data = json.loads(json_str)

        messages = [
            DiplomaticMessage(**m) for m in data.get("private_messages", [])[:2]
        ]

        action_data = data.get("action", {"action_type": "hold"})
        action = ActionPayload(
            action_type=action_data.get("action_type", "hold"),
            target=action_data.get("target"),
            parameters=action_data.get("parameters", {}),
        )

        # Validate action type
        legal = STATE_ACTIONS if self.actor.actor_type == "state" else NON_STATE_ACTIONS
        if action.action_type not in legal:
            logger.warning(
                f"[{self.actor.name}] Invalid action '{action.action_type}', "
                f"legal actions: {legal}. Defaulting to hold."
            )
            action = ActionPayload(action_type="hold")

        return AgentTurnOutput(
            actor_id=self.actor.actor_id,
            private_messages=messages,
            public_statement=data.get("public_statement", ""),
            action=action,
            rationale=data.get("rationale", ""),
        )

    # ── Main decide with trace capture ─────────────────────────────────────

    def decide(self, observation: ActorObservation, turn: int = 0, run_id: str = "") -> AgentTurnOutput:
        """Generate a decision using the LLM with retry logic and full trace capture."""
        self._last_traces = []
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(observation)

        total_start = time.perf_counter()
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                raw, trace = self._call_llm_traced(system_prompt, user_prompt, turn, run_id)
                trace["attempt_number"] = attempt

                # Try strict parse
                try:
                    result, coercion = self._parse_response_strict(raw, observation)
                    trace["parse_success"] = True
                    trace["parsed_action"] = {
                        "action_type": result.action.action_type,
                        "target": result.action.target,
                        "parameters": result.action.parameters,
                    }
                    trace["was_coerced"] = coercion is not None
                    trace["coercion_reason"] = coercion
                    trace["total_latency_ms"] = (time.perf_counter() - total_start) * 1000
                    self._last_traces.append(trace)
                    return result
                except (json.JSONDecodeError, KeyError, ValueError) as parse_err:
                    trace["parse_success"] = False
                    trace["parse_error"] = str(parse_err)

                    # Attempt LLM repair
                    try:
                        trace["repair_attempted"] = True
                        repair_raw, repair_trace = self._call_llm_traced(
                            REPAIR_PROMPT, raw, turn, run_id
                        )
                        trace["repair_completion"] = repair_raw

                        result, coercion = self._parse_response_strict(repair_raw, observation)
                        trace["parse_success"] = True
                        trace["parsed_action"] = {
                            "action_type": result.action.action_type,
                            "target": result.action.target,
                            "parameters": result.action.parameters,
                        }
                        trace["was_coerced"] = coercion is not None
                        trace["coercion_reason"] = coercion
                        trace["total_latency_ms"] = (time.perf_counter() - total_start) * 1000
                        self._last_traces.append(trace)
                        # Don't append repair_trace separately — it's embedded in the main trace
                        return result
                    except Exception:
                        pass  # Repair failed, fall through to retry

                    trace["total_latency_ms"] = (time.perf_counter() - total_start) * 1000
                    self._last_traces.append(trace)
                    last_error = parse_err

            except Exception as e:
                if 'trace' in locals():
                    trace["total_latency_ms"] = (time.perf_counter() - total_start) * 1000
                    self._last_traces.append(trace)
                last_error = e
                logger.error(f"[{self.actor_name}] Attempt {attempt} failed: {e}")

        # All retries exhausted — fallback to hold
        logger.warning(f"[{self.actor_name}] All {self.max_retries} attempts failed, falling back to hold")
        fallback_trace = {
            "trace_id": uuid.uuid4().hex[:12],
            "run_id": run_id,
            "turn": turn,
            "actor_id": self.actor_id,
            "model": self.model,
            "provider": self._provider_name,
            "temperature": self.temperature,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_completion": "EXHAUSTED_RETRIES",
            "parse_success": False,
            "parse_error": f"All {self.max_retries} attempts failed: {last_error}",
            "was_coerced": True,
            "coercion_reason": "retry_exhaustion",
            "latency_ms": 0,
            "total_latency_ms": (time.perf_counter() - total_start) * 1000,
            "attempt_number": self.max_retries + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_tokens": None,
            "completion_tokens": None,
            "finish_reason": None,
            "repair_attempted": False,
            "repair_completion": None,
            "parsed_action": {"action_type": "hold", "target": None, "parameters": {}},
        }
        self._last_traces.append(fallback_trace)

        return AgentTurnOutput(
            actor_id=self.actor_id,
            private_messages=[],
            public_statement="No comment.",
            action=ActionPayload(action_type="hold"),
            rationale=f"Fallback: {last_error}",
        )

    def get_agent_metadata(self) -> dict:
        """Return agent config metadata for run registry."""
        return {
            "agent_type": self.agent_type,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "model": self.model,
            "provider": self._provider_name,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
        }
