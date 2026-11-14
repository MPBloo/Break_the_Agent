"""Frontier-model agent: a plain tool-calling loop, no shell, no code execution.

The model sees the same one-paragraph instruction and the same seven tools as every other agent,
and nothing else. It talks to any OpenAI-compatible chat-completions endpoint, which covers
Gemini, OpenAI, OpenRouter and local servers (vLLM, Ollama) for small models. Claude models go
through agents/anthropic_agent.py instead, which uses the Anthropic SDK.

Configuration (environment variables or arguments of `make_agent`):
    LLM_PROVIDER   gemini | openai | openrouter   (sets the base URL)
    LLM_BASE_URL   overrides the provider's base URL
    LLM_API_KEY    API key
    LLM_MODEL      model id, e.g. gemini-3-pro-preview
    LLM_EXTRA      optional JSON merged into every request body (e.g. {"reasoning_effort":"high"})
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from bomber.episode import INSTRUCTION, TOOLS

BASE_URLS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

SYSTEM = INSTRUCTION + (
    " You cannot run code: reason step by step and use the tools. Think about which test drops will tell "
    "you the most before spending them."
)
NUDGE = "The mission is not over. Continue with the tools, and call declare_done when you have finished."


def _tool_specs() -> list[dict]:
    out = []
    for t in TOOLS:
        params = {k: v for k, v in t["parameters"].items() if k != "additionalProperties"}
        out.append({"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                      "parameters": params}})
    return out


class LLMConfig:
    def __init__(self, model=None, base_url=None, api_key=None, provider=None, extra=None,
                 max_tool_calls=260, timeout=300):
        provider = provider or os.environ.get("LLM_PROVIDER", "gemini")
        self.model = model or os.environ.get("LLM_MODEL", "")
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL") or BASE_URLS.get(provider, "")).rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.extra = extra if extra is not None else json.loads(os.environ.get("LLM_EXTRA", "{}"))
        self.max_tool_calls = max_tool_calls
        self.timeout = timeout

    def ready(self) -> bool:
        return bool(self.model and self.base_url and self.api_key)


def _post(cfg: LLMConfig, body: dict) -> dict:
    req = urllib.request.Request(
        cfg.base_url + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg.api_key}"})
    delay = 2.0
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=cfg.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            if e.code not in (408, 409, 429, 500, 502, 503, 504, 529) or attempt == 5:
                raise RuntimeError(f"LLM endpoint returned HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 5:
                raise RuntimeError(f"LLM endpoint unreachable: {e}") from None
        time.sleep(delay)
        delay = min(delay * 2, 60)
    raise RuntimeError("unreachable")


def make_agent(cfg: LLMConfig | None = None):
    cfg = cfg or LLMConfig()

    def run(client) -> dict:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "Begin the mission."}]
        tools = _tool_specs()
        notes, usage = [], {"prompt_tokens": 0, "completion_tokens": 0, "requests": 0}
        n_calls, nudges, done = 0, 0, False
        while not done and n_calls < cfg.max_tool_calls:
            resp = _post(cfg, {"model": cfg.model, "messages": messages, "tools": tools, **cfg.extra})
            usage["requests"] += 1
            for k in ("prompt_tokens", "completion_tokens"):
                usage[k] += (resp.get("usage") or {}).get(k) or 0
            msg = resp["choices"][0]["message"]
            # Echo the assistant message back untouched: some providers attach opaque fields to
            # tool calls (e.g. Gemini thought signatures) that must be returned as received.
            messages.append(msg)
            text = msg.get("content")
            if isinstance(text, list):
                text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
            if text and text.strip():
                notes.append({"before_call": n_calls + 1, "text": text.strip()[:4000]})
            calls = msg.get("tool_calls") or []
            if not calls:
                nudges += 1
                if nudges > 3:
                    break
                messages.append({"role": "user", "content": NUDGE})
                continue
            for call in calls:
                fn = call.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                    result = client.call(fn.get("name", ""), **args) if isinstance(args, dict) \
                        else {"error": "Arguments must be an object."}
                except (json.JSONDecodeError, TypeError):
                    result = {"error": "Arguments are not valid JSON."}
                n_calls += 1
                messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": json.dumps(result)})
                if fn.get("name") == "declare_done" and "error" not in result:
                    done = True
        return {"model": cfg.model, "notes": notes, "usage": usage, "stopped": "done" if done else "limit"}

    return run
