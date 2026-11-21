"""Circuit breaker for the LLM proposer: when Gemini fails, stop waiting on it for a while.

Without this, an overloaded model (503) or a rate limit (429) costs one slow failure per video
per request, so a page could hang for minutes. After one failure the breaker "opens": further
calls fail immediately for LLM_COOLDOWN_SEC, and the pipeline uses keyword mode for them,
which is the documented fallback. After the cooldown the next call tries Gemini again.

State is per process and per proposer name, so it carries across requests (the API builds a new
proposer for each request). Cached proposals are unaffected: CachingProposer sits in front of
this breaker and answers from disk without calling through.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional, Sequence

import config
from llm import MomentProposer, ProposedMoment
from models import Topic, TranscriptSegment

log = logging.getLogger("onrecord.circuit_breaker")

_lock = threading.Lock()
_open_until: dict[str, float] = {}  # proposer name -> monotonic time the breaker closes again


class LLMUnavailable(RuntimeError):
    """Raised instead of calling the LLM while the breaker is open."""


def reset() -> None:
    """Close every breaker (tests, or after fixing a key)."""
    with _lock:
        _open_until.clear()


def is_open(name: str, clock: Callable[[], float] = time.monotonic) -> bool:
    with _lock:
        return clock() < _open_until.get(name, 0.0)


class CircuitBreakerProposer:
    """Wraps a proposer. Same interface; `name` and `model` pass through so cache keys don't change."""

    def __init__(self, inner: MomentProposer, cooldown_sec: Optional[float] = None,
                 clock: Callable[[], float] = time.monotonic):
        self.inner = inner
        self.name = inner.name
        self.model = getattr(inner, "model", None)
        self.cooldown_sec = config.LLM_COOLDOWN_SEC if cooldown_sec is None else cooldown_sec
        self.clock = clock

    def propose(self, video_id: str, segments: Sequence[TranscriptSegment], topics: Sequence[Topic]) -> list[ProposedMoment]:
        if is_open(self.name, self.clock):
            raise LLMUnavailable(f"{self.name} skipped: it failed recently (circuit open)")
        try:
            moments = self.inner.propose(video_id, segments, topics)
        except Exception as e:
            with _lock:
                _open_until[self.name] = self.clock() + self.cooldown_sec
            log.warning("%s failed (%s); using keyword mode for %.0f s", self.name, e, self.cooldown_sec)
            raise
        with _lock:
            _open_until.pop(self.name, None)
        return moments
