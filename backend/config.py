"""All tunables in one place. Every threshold here is documented in docs/DECISIONS.md."""
from __future__ import annotations

import os
from pathlib import Path

try:  # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
TOPICS_PATH = REPO_ROOT / "config" / "topics.json"
REPORTS_PATH = REPO_ROOT / "data" / "reports" / "reports.jsonl"


def data_dir() -> Path:
    return REPO_ROOT / os.getenv("ONRECORD_DATA_DIR", "data/seed")


def mode() -> str:
    """'keyword' (no-LLM, default) or 'llm' (Gemini proposes, code verifies)."""
    m = os.getenv("ONRECORD_MODE", "keyword").strip().lower()
    return m if m in {"keyword", "llm"} else "keyword"


REPORT_EMAIL = os.getenv("ONRECORD_REPORT_EMAIL", "onrecord-reports@example.org")

# --- Verification (docs/DECISIONS.md D6) ---
NEAR_EXACT_THRESHOLD = 0.90  # difflib token ratio for near-exact matches
MIN_QUOTE_TOKENS = 4  # shorter proposals are too ambiguous to verify
CONTEXT_SEGMENTS = 1  # transcript segments shown before/after a quote
TIMESTAMP_TOLERANCE_SEC = 3.0  # proposals off by more than this are flagged as corrected

# Tokens whose change flips meaning; a near-exact match may never differ on these.
CRITICAL_TOKENS = {
    "not", "no", "never", "nor", "dont", "doesnt", "didnt", "wont", "wouldnt",
    "cant", "cannot", "shouldnt", "isnt", "arent", "wasnt", "werent",
    "support", "oppose", "against", "for", "favor", "ban", "allow", "always",
    "yes", "only", "without",
}

# --- Coverage unevenness ---
UNEVENNESS_RATIO = 2.0  # warn if max/min hours (or videos) across candidates exceeds this
