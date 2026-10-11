"""Environment loading. Values are read lazily so modules that don't need a
given variable (e.g. embeddings) can be imported without a full .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

LOCAL_TZ = "America/New_York"
EMBED_MODEL = "all-MiniLM-L6-v2"
EMBED_DIM = 384


class ConfigError(RuntimeError):
    pass


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or "<" in value:  # unfilled .env.example placeholder
        raise ConfigError(
            f"Missing env var {name}. Copy .env.example to .env and fill it in."
        )
    return value


def mongodb_uri() -> str:
    return require("MONGODB_URI")


def db_name() -> str:
    return os.getenv("DB_NAME", "").strip() or "volunteerops"


def llm_settings() -> tuple[str, str, str]:
    """(base_url, api_key, model)"""
    return require("LLM_BASE_URL"), require("LLM_API_KEY"), require("LLM_MODEL")


def demo_mode() -> bool:
    """NEXTUP_DEMO=1 enables demo-only features (the simulated-weather switch). Off by default,
    so a normal deployment always uses the real forecast."""
    return os.getenv("NEXTUP_DEMO", "").strip().lower() in ("1", "true", "yes", "on")
