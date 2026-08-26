"""Project-wide configuration constants."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
DB_PATH = DATA_DIR / "ledger.sqlite"

OLLAMA_HOST = "http://localhost:11434"
CHAT_MODEL = "llama3.2:3b"
EMBED_MODEL = "llama3.2:3b"
EMBED_DIM = 64

DEFAULT_MONTHLY_TOKEN_BUDGET = 200_000

CATEGORIES: list[str] = [
    "groceries",
    "eating_out",
    "coffee",
    "transport",
    "housing",
    "utilities",
    "subscriptions",
    "health",
    "income",
    "transfer",
    "other",
]

CACHE_SIMILARITY_THRESHOLD = 0.92