"""Central paths and settings for Sports Research Agent.

Stdlib only — no external dependencies. Extend this as real config
(API keys, source lists, etc.) is needed.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"

DOCS_DIR = BASE_DIR / "docs"
