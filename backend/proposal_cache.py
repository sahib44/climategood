"""Disk cache for LLM proposals: one model call per video, all topics at once.

The pipeline asks for one topic at a time, so without this a single page load costs
(videos x topics) Gemini calls, which drains the free quota mid-demo. CachingProposer wraps
any MomentProposer, asks it once per video for EVERY topic, saves the result to
<proposals dir>/<video_id>.proposals.json, and answers later requests from that file.

Caching changes nothing about trust: cached proposals are still only PROPOSALS ("modeled").
The pipeline verifies every one against the transcript before it is shown (rule 2), so a
stale or tampered cache can never put words on screen that are not in the transcript.

The cache key covers the transcript text and timestamps, the topic list, the prompt and the
model, so changing any of them triggers a fresh call. Failed calls are never cached: the
error propagates and the pipeline falls back to keyword mode for that video.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import config
from llm import MomentProposer, ProposedMoment
from models import Topic, TranscriptSegment

log = logging.getLogger("firsthand.proposal_cache")

CACHE_VERSION = 1


def cache_key(proposer: MomentProposer, segments: Sequence[TranscriptSegment], topics: Sequence[Topic]) -> str:
    """Hash of everything that can change the model's answer."""
    import llm  # read PROMPT at call time so edits to it invalidate the cache

    payload = {
        "v": CACHE_VERSION,
        "proposer": proposer.name,
        "model": getattr(proposer, "model", None),
        "prompt": getattr(llm, "PROMPT", ""),
        "topics": [t.model_dump() for t in sorted(topics, key=lambda t: t.id)],
        "segments": [[s.start, s.end, s.text] for s in segments],
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def cache_path(cache_dir: Path, video_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", video_id)
    return cache_dir / f"{safe}.proposals.json"


class CachingProposer:
    """Wraps a proposer. Same interface, so the pipeline needs no changes."""

    def __init__(self, inner: MomentProposer, all_topics: Sequence[Topic], cache_dir: Optional[Path] = None):
        self.inner = inner
        self.name = inner.name  # keeps mode/found_by = "llm" for an LLM proposer
        self.all_topics = list(all_topics)
        self.cache_dir = Path(cache_dir) if cache_dir else config.proposals_dir()
        self.calls = 0  # model calls made by this instance (useful in tests and logs)

    def _load(self, path: Path, key: str) -> Optional[list[ProposedMoment]]:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("key") != key:
                return None  # transcript, topics, prompt or model changed
            return [ProposedMoment(**m) for m in data["moments"]]
        except Exception as e:  # corrupt or hand-edited file: ignore it and re-ask
            log.warning("ignoring unreadable proposal cache %s (%s)", path, e)
            return None

    def _save(self, path: Path, key: str, video_id: str, moments: list[ProposedMoment]) -> None:
        data = {
            "_note": "Cached LLM PROPOSALS (modeled, unverified). Every one is verified against the "
                     "transcript before display. Safe to delete; it is rebuilt on the next request.",
            "key": key,
            "video_id": video_id,
            "proposer": self.inner.name,
            "model": getattr(self.inner, "model", None),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "moments": [m.model_dump() for m in moments],
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            tmp.replace(path)  # atomic: a crash never leaves a half-written cache
        except OSError as e:  # read-only disk etc.: still answer, just don't cache
            log.warning("could not write proposal cache %s (%s)", path, e)

    def all_moments(self, video_id: str, segments: Sequence[TranscriptSegment]) -> list[ProposedMoment]:
        key = cache_key(self.inner, segments, self.all_topics)
        path = cache_path(self.cache_dir, video_id)
        cached = self._load(path, key)
        if cached is not None:
            return cached
        moments = self.inner.propose(video_id, segments, self.all_topics)  # errors propagate, not cached
        self.calls += 1
        self._save(path, key, video_id, moments)
        return moments

    def propose(self, video_id: str, segments: Sequence[TranscriptSegment], topics: Sequence[Topic]) -> list[ProposedMoment]:
        wanted = {t.id for t in topics}
        return [m for m in self.all_moments(video_id, segments) if m.topic_id in wanted]
