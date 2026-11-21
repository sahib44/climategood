"""Load JSON data. No database (docs/DECISIONS.md D3)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import config
from models import Candidate, Topic, Transcript, Video


def _read(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_topics() -> list[Topic]:
    return [Topic(**t) for t in _read(config.TOPICS_PATH)["topics"]]


def load_candidates(data_dir: Optional[Path] = None) -> list[Candidate]:
    d = data_dir or config.data_dir()
    return [Candidate(**c) for c in _read(d / "candidates.json")["candidates"]]


def load_videos(data_dir: Optional[Path] = None) -> list[Video]:
    d = data_dir or config.data_dir()
    return [Video(**v) for v in _read(d / "videos.json")["videos"]]


def load_transcript(video: Video, data_dir: Optional[Path] = None) -> Optional[Transcript]:
    """Returns None if the transcript file is missing (video then doesn't count as searched)."""
    d = data_dir or config.data_dir()
    path = d / video.transcript_path
    if not path.exists():
        return None
    return Transcript(**_read(path))
