"""Shared paths, file helpers and candidate-config loading for the ingest job.

Nothing in ingest/ runs at request time. It is an offline batch job whose output a person
reviews before anything reaches the dataset the backend reads (data/real/).
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "backend") not in sys.path:  # reuse the backend's pydantic schema
    sys.path.insert(0, str(REPO_ROOT / "backend"))


@dataclass(frozen=True)
class Paths:
    """Every file the ingest job reads or writes. Tests point `root` at a temp dir."""

    root: Path = REPO_ROOT

    @property
    def sources(self) -> Path:
        return self.root / "config" / "sources.json"

    @property
    def candidates(self) -> Path:
        return self.root / "config" / "candidates.json"

    @property
    def settings(self) -> Path:
        return self.root / "ingest" / "settings.json"

    @property
    def ingest_dir(self) -> Path:
        return self.root / "data" / "ingest"

    @property
    def proposed(self) -> Path:
        return self.ingest_dir / "proposed"

    @property
    def approved(self) -> Path:
        return self.ingest_dir / "approved"

    @property
    def rejected(self) -> Path:
        return self.ingest_dir / "rejected"

    @property
    def evidence(self) -> Path:
        return self.ingest_dir / "evidence"

    @property
    def log(self) -> Path:
        return self.ingest_dir / "log.jsonl"

    @property
    def progress(self) -> Path:
        return self.ingest_dir / "progress.json"

    @property
    def manual_queue(self) -> Path:
        return self.ingest_dir / "manual_queue.csv"

    @property
    def coverage(self) -> Path:
        return self.ingest_dir / "coverage.json"

    @property
    def link_check(self) -> Path:
        return self.ingest_dir / "link_check.json"

    @property
    def real_dir(self) -> Path:
        """The dataset the backend reads with ONRECORD_DATA_DIR=data/real."""
        return self.root / "data" / "real"

    @property
    def transcripts(self) -> Path:
        """Where scripts/fetch_transcript.py writes official captions (gitignored)."""
        return self.root / "data" / "transcripts"


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)  # atomic, so a crash never leaves half a file behind


def append_log(paths: Paths, event: str, **fields: Any) -> None:
    """One JSON line per decision the job makes, so every drop is visible later."""
    paths.log.parent.mkdir(parents=True, exist_ok=True)
    line = {"at": now_utc().isoformat(), "event": event, **fields}
    with paths.log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")


def read_log(paths: Paths) -> list[dict]:
    if not paths.log.exists():
        return []
    return [json.loads(l) for l in paths.log.read_text(encoding="utf-8").splitlines() if l.strip()]


def video_id_for(candidate_id: str, url: str) -> str:
    """Stable id from the candidate and the video URL, so re-runs never duplicate an item."""
    digest = hashlib.sha1(f"{candidate_id}|{url}".encode()).hexdigest()[:10]
    host = (urlsplit(url).hostname or "x").removeprefix("www.").split(".")[0]
    return f"{candidate_id}-{host}-{digest}"


def is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and (value.strip().startswith("<") or "YYYY" in value)


def parse_date(value: Any) -> Optional[date]:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip()
    attempts = [lambda: date.fromisoformat(s[:10]), lambda: datetime.strptime(s[:8], "%Y%m%d").date(),
                lambda: datetime.fromisoformat(s.replace("Z", "+00:00")).date()]
    for attempt in attempts:
        try:
            return attempt()
        except ValueError:
            continue
    return None


def load_candidates(path: Path) -> list[dict]:
    """Flatten config/candidates.json (races -> candidates) into one dict per candidate.

    Party is copied through for display only. No ingest code reads it.
    """
    cfg = read_json(path)
    if cfg is None:
        raise FileNotFoundError(
            f"{path} not found. Copy config/candidates.example.json to config/candidates.json and fill it in."
        )
    out = []
    for race in cfg.get("races", []):
        for c in race.get("candidates", []):
            out.append(
                {
                    **c,
                    "office": race.get("office"),
                    "jurisdiction": race.get("jurisdiction"),
                    "election_date": race.get("election_date"),
                    "race_id": race.get("race_id"),
                }
            )
    return out


def source_urls(candidate: dict) -> list[str]:
    """`sources` entries may be plain URLs or {"url": ...} objects."""
    urls = []
    for s in candidate.get("sources", []):
        url = s.get("url") if isinstance(s, dict) else s
        if url:
            urls.append(url)
    return urls
