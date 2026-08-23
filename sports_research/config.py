"""Application configuration. All defaults are zero-cost — no setting
here requires a paid API key. See .env.example and docs/configuration.md.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


def _int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


class Config:
    # "duckduckgo" | "wikipedia" | "duckduckgo,wikipedia" (fallback chain, in order)
    SEARCH_PROVIDER = os.environ.get("SEARCH_PROVIDER", "duckduckgo,wikipedia")
    REQUEST_TIMEOUT = _float("REQUEST_TIMEOUT", 15.0)
    MAX_SOURCES_TO_FETCH = _int("MAX_SOURCES_TO_FETCH", 5)

    CACHE_ENABLED = _bool("CACHE_ENABLED", True)
    CACHE_DIR = Path(os.environ.get("CACHE_DIR", str(BASE_DIR / "data" / "cache")))
    CACHE_TTL_SECONDS = _int("CACHE_TTL_SECONDS", 24 * 3600)

    OLLAMA_ENABLED = _bool("OLLAMA_ENABLED", False)
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    USE_BROWSER_FALLBACK = _bool("USE_BROWSER_FALLBACK", False)

    OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(BASE_DIR / "data" / "exports")))
