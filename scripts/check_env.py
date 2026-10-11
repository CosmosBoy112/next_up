"""Connectivity checks. Usage: python -m scripts.check_env"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `python scripts/x.py`

import json
import time
from collections.abc import Callable

from core import config


def check(label: str, fn: Callable[[], str]) -> bool:
    try:
        detail = fn()
        print(f"✅ {label}: {detail}")
        return True
    except Exception as e:  # noqa: BLE001 - report any failure as ❌
        print(f"❌ {label}: {type(e).__name__}: {str(e)[:300]}")
        return False


def check_mongo() -> str:
    from core import db

    db.get_client().admin.command("ping")
    tmp = db.col("_check_env")
    doc_id = tmp.insert_one({"ts": time.time()}).inserted_id
    assert tmp.find_one({"_id": doc_id}) is not None, "read-back failed"
    tmp.drop()
    return f"ping ok, write/read ok (db={config.db_name()})"


def _client():
    from openai import OpenAI

    base_url, api_key, model = config.llm_settings()
    return OpenAI(base_url=base_url, api_key=api_key, timeout=60), model


def check_llm_chat() -> str:
    client, model = _client()
    r = client.chat.completions.create(
        model=model, max_tokens=20,
        messages=[{"role": "user", "content": "Reply with the single word: pong"}],
    )
    return f"model={model} reply={(r.choices[0].message.content or '').strip()[:40]!r}"


def check_llm_tools() -> str:
    client, model = _client()
    tool = {"type": "function", "function": {
        "name": "get_weather", "description": "Get the weather for a city.",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                       "required": ["city"], "additionalProperties": False},
    }}
    r = client.chat.completions.create(
        model=model, max_tokens=100, tools=[tool],
        messages=[{"role": "user", "content": "What's the weather in Boston? Use the tool."}],
    )
    calls = r.choices[0].message.tool_calls or []
    if not calls:
        raise RuntimeError("endpoint accepted tools= but model returned no tool call "
                           "-> harness will use JSON mode")
    args = json.loads(calls[0].function.arguments)
    return f"NATIVE tool calling works ({calls[0].function.name}({args}))"


def check_embeddings() -> str:
    from core.embeddings import embed

    vec = embed("I can drive a van and lift boxes")
    assert len(vec) == config.EMBED_DIM, f"got {len(vec)} dims"
    return f"{config.EMBED_MODEL} -> {len(vec)} dims"


def main() -> None:
    results = [
        check("MongoDB Atlas", check_mongo),
        check("LLM chat completion", check_llm_chat),
        check("LLM tool calling", check_llm_tools),
        check("Embedding model", check_embeddings),
    ]
    print("\nAll good." if all(results) else "\nSome checks failed (see ❌ above).")


if __name__ == "__main__":
    main()
