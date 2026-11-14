"""Claude agent: a plain tool-calling loop on the Anthropic Messages API, through the official SDK.

Same contract as agents/llm_agent.py: the model gets a one-paragraph instruction and the seven
mission tools, nothing else. No shell, no code execution.

Configuration (environment variables, or a .env file read by run_llm.py):
    ANTHROPIC_API_KEY   credentials (the SDK also accepts ANTHROPIC_AUTH_TOKEN or an `ant auth login` profile)
    LLM_MODEL           model id, default claude-opus-5-5
    LLM_EFFORT          low | medium | high | xhigh | max, default high
    LLM_FALLBACKS       "off" disables server-side refusal fallbacks (on by default where supported)
"""
from __future__ import annotations

import json
import os

import anthropic

from bomber.episode import TOOLS

from .llm_agent import NUDGE, SYSTEM

# Models that accept the server-side `fallbacks` parameter.
FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeConfig:
    def __init__(self, model=None, effort=None, fallbacks=None, max_tool_calls=260, base_url=None, api_key=None):
        self.model = model or os.environ.get("LLM_MODEL") or "claude-opus-5-5"
        self.effort = effort or os.environ.get("LLM_EFFORT") or "high"
        if fallbacks is None:
            fallbacks = os.environ.get("LLM_FALLBACKS", "").lower() != "off"
        self.fallbacks = fallbacks and self.model in FALLBACK_MODELS
        self.max_tool_calls = max_tool_calls
        self.base_url = base_url      # tests only; None lets the SDK resolve it
        self.api_key = api_key        # tests only; None lets the SDK resolve credentials

    def ready(self) -> bool:
        return bool(self.api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _tool_specs() -> list[dict]:
    return [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in TOOLS]


def make_agent(cfg: ClaudeConfig | None = None):
    cfg = cfg or ClaudeConfig()

    def run(client) -> dict:
        kwargs = {"max_retries": 4}
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        if cfg.api_key:
            kwargs["api_key"] = cfg.api_key
        api = anthropic.Anthropic(**kwargs)
        tools = _tool_specs()
        messages = [{"role": "user", "content": "Begin the mission."}]
        notes = []
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "cache_read_tokens": 0, "requests": 0}
        served, n_calls, nudges, done, stopped = set(), 0, 0, False, "limit"

        while not done and n_calls < cfg.max_tool_calls:
            request = dict(
                model=cfg.model, max_tokens=16000, system=SYSTEM, tools=tools, messages=messages,
                thinking={"type": "adaptive", "display": "summarized"},
                output_config={"effort": cfg.effort},
                cache_control={"type": "ephemeral"},   # the history only grows: cache the whole prefix
            )
            try:
                if cfg.fallbacks:
                    resp = api.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **request)
                else:
                    resp = api.messages.create(**request)
            except anthropic.AuthenticationError:
                raise RuntimeError("Anthropic rejected the API key. Check ANTHROPIC_API_KEY.") from None
            except anthropic.NotFoundError:
                raise RuntimeError(f"Unknown model '{cfg.model}'. Check LLM_MODEL.") from None
            except anthropic.BadRequestError as e:
                raise RuntimeError(f"Request rejected by the API: {e.message}") from None
            except anthropic.RateLimitError:
                raise RuntimeError("Rate limited after retries. Lower --parallel and run again.") from None
            except anthropic.APIStatusError as e:
                raise RuntimeError(f"Anthropic API error {e.status_code}: {e.message}") from None
            except anthropic.APIConnectionError as e:
                raise RuntimeError(f"Cannot reach the Anthropic API: {e}") from None

            usage["requests"] += 1
            u = resp.usage
            read = getattr(u, "cache_read_input_tokens", 0) or 0
            written = getattr(u, "cache_creation_input_tokens", 0) or 0
            usage["prompt_tokens"] += (u.input_tokens or 0) + read + written
            usage["cache_read_tokens"] += read
            usage["completion_tokens"] += u.output_tokens or 0
            served.add(resp.model)

            for block in resp.content:
                text = block.text if block.type == "text" else getattr(block, "thinking", "") if block.type == "thinking" else ""
                if text and text.strip():
                    notes.append({"before_call": n_calls + 1, "text": text.strip()[:4000]})

            if resp.stop_reason == "refusal":
                stopped = "refusal"
                break
            # History is append-only and blocks go back untouched (thinking blocks included).
            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason == "pause_turn":
                continue

            results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                if resp.stop_reason != "tool_use":      # cut off before the call was complete
                    result = {"error": "The call was cut off before it was complete. Send it again."}
                elif not isinstance(block.input, dict):
                    result = {"error": "Arguments must be an object."}
                else:
                    try:
                        result = client.call(block.name, **block.input)
                    except TypeError:
                        result = {"error": "Invalid arguments."}
                    n_calls += 1
                    if block.name == "declare_done" and "error" not in result:
                        done, stopped = True, "done"
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result),
                                "is_error": "error" in result})
            if results:
                messages.append({"role": "user", "content": results})   # all results in one message
                continue
            nudges += 1
            if nudges > 3:
                stopped = "gave_up"
                break
            messages.append({"role": "user", "content": NUDGE})

        return {"model": cfg.model, "served_by": sorted(served), "effort": cfg.effort, "fallbacks": cfg.fallbacks,
                "notes": notes, "usage": usage, "stopped": stopped}

    return run
