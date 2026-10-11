"""OpenAI-compatible chat client with native tool calling and a JSON-mode fallback.

The harness always sees the same shape (AssistantTurn with tool_calls), whichever
mode is active. In JSON mode the model is told to reply with
{"tool": name, "args": {...}} or {"final": "..."}, and tool-call history is
rewritten into plain user/assistant text before each request.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import openai

from core import config

RETRYABLE = (openai.APITimeoutError, openai.APIConnectionError,
             openai.RateLimitError, openai.InternalServerError)


@dataclass
class ToolCall:
    id: str
    name: str
    args_json: str


@dataclass
class AssistantTurn:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Thinking models (e.g. DeepSeek) require their reasoning to be sent back
    # with the assistant turn in later requests.
    reasoning: str | None = None

    def as_message(self) -> dict:
        """Assistant message to append to history (OpenAI format)."""
        msg: dict[str, Any] = {"role": "assistant", "content": self.text or ""}
        if self.reasoning is not None:
            msg["reasoning_content"] = self.reasoning
        if self.tool_calls:
            msg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": tc.args_json}}
                for tc in self.tool_calls
            ]
        return msg


class LLM:
    def __init__(self, client: openai.OpenAI | None = None, model: str | None = None,
                 mode: str = "native", max_tokens: int = 1500):
        if client is None:
            base_url, api_key, model_name = config.llm_settings()
            client = openai.OpenAI(base_url=base_url, api_key=api_key, timeout=60, max_retries=0)
            model = model or model_name
        self.client = client
        self.model = model
        self.mode = mode  # "native" | "json"
        self.max_tokens = max_tokens
        self._native_confirmed = False
        self._json_call_seq = 0

    def chat(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        if self.mode == "native":
            try:
                turn = self._chat_native(messages, tools)
                self._native_confirmed = True
                return turn
            except (openai.BadRequestError, openai.UnprocessableEntityError,
                    openai.NotFoundError) as e:
                if self._native_confirmed:
                    raise
                print(f"[llm] native tool calling rejected ({type(e).__name__}); "
                      f"switching to JSON mode")
                self.mode = "json"
        return self._chat_json(messages, tools)

    # ---- native ----

    def _chat_native(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        resp = self._create(messages=messages, tools=tools)
        msg = resp.choices[0].message
        calls = [ToolCall(tc.id, tc.function.name, tc.function.arguments or "{}")
                 for tc in (msg.tool_calls or [])]
        text = msg.content or ""
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning is None:
            reasoning = (getattr(msg, "model_extra", None) or {}).get("reasoning_content")
        if not calls:
            # Some models emit the JSON-mode shape as text even with tools available.
            parsed = _parse_json_reply(text)
            if parsed and "tool" in parsed:
                calls = [self._synth_call(parsed)]
                text = ""
        return AssistantTurn(text=text, tool_calls=calls, reasoning=reasoning)

    # ---- JSON fallback ----

    def _chat_json(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        converted = _to_json_mode_messages(messages, tools)
        for attempt in range(2):
            resp = self._create(messages=converted)
            text = resp.choices[0].message.content or ""
            parsed = _parse_json_reply(text)
            if parsed and "tool" in parsed:
                return AssistantTurn(text="", tool_calls=[self._synth_call(parsed)])
            if parsed and "final" in parsed:
                return AssistantTurn(text=str(parsed["final"]))
            if attempt == 0:
                converted = converted + [
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": 'Invalid format. Reply with ONLY one JSON object: '
                     '{"tool": "<name>", "args": {...}} or {"final": "<text>"}.'},
                ]
        return AssistantTurn(text=text)

    def _synth_call(self, parsed: dict) -> ToolCall:
        self._json_call_seq += 1
        args = parsed.get("args") or {}
        return ToolCall(id=f"call_json_{self._json_call_seq}", name=str(parsed["tool"]),
                        args_json=json.dumps(args) if not isinstance(args, str) else args)

    # ---- transport with retries ----

    def _create(self, **kwargs):
        for attempt in range(3):
            try:
                return self.client.chat.completions.create(
                    model=self.model, max_tokens=self.max_tokens, temperature=0.2, **kwargs)
            except RETRYABLE:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)


def _parse_json_reply(text: str) -> dict | None:
    """Extract the first JSON object from a reply (tolerates code fences / prose)."""
    text = re.sub(r"```(?:json)?", "", text or "").strip()
    start = text.find("{")
    while start != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[start:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        start = text.find("{", start + 1)
    return None


def json_mode_instructions(tools: list[dict]) -> str:
    lines = ["", "## Tools",
             "You cannot call functions natively. To use a tool, reply with ONLY a JSON object:",
             '{"tool": "<tool_name>", "args": {<arguments>}}',
             "Call one tool per reply. You will receive the result in the next message.",
             'When completely done, reply with {"final": "<short summary>"}.',
             "Available tools:"]
    for t in tools:
        f = t["function"]
        lines.append(f"- {f['name']}: {f['description']} "
                     f"args schema: {json.dumps(f['parameters']['properties'])}")
    return "\n".join(lines)


def _to_json_mode_messages(messages: list[dict], tools: list[dict]) -> list[dict]:
    out: list[dict] = []
    names: dict[str, str] = {}
    for m in messages:
        role = m["role"]
        if role == "system":
            out.append({"role": "system", "content": m["content"] + json_mode_instructions(tools)})
        elif role == "assistant" and m.get("tool_calls"):
            parts = [m["content"]] if m.get("content") else []
            for tc in m["tool_calls"]:
                names[tc["id"]] = tc["function"]["name"]
                raw = tc["function"]["arguments"] or "{}"
                try:
                    args: Any = json.loads(raw)
                except json.JSONDecodeError:
                    args = raw
                parts.append(json.dumps({"tool": tc["function"]["name"], "args": args}))
            out.append({"role": "assistant", "content": "\n".join(parts)})
        elif role == "tool":
            name = names.get(m["tool_call_id"], "tool")
            out.append({"role": "user", "content": f"Result of {name}:\n{m['content']}"})
        else:
            out.append({"role": role, "content": m.get("content") or ""})
    return out
