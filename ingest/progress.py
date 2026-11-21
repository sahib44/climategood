"""Resumable progress and the browser-time budget (data/ingest/progress.json).

Each (candidate, listing URL) pair is one task. A finished or blocked task is skipped on the
next run, so a crash or a timeout never re-spends browser minutes on work already done.
"""
from __future__ import annotations

from ingest.common import Paths, now_utc, read_json, write_json


class Progress:
    def __init__(self, paths: Paths):
        self.paths = paths
        self.data = read_json(paths.progress, {"browser_seconds_used": 0.0, "tasks": {}})

    @staticmethod
    def key(candidate_id: str, url: str) -> str:
        return f"{candidate_id}|{url}"

    def status(self, candidate_id: str, url: str) -> str | None:
        return self.data["tasks"].get(self.key(candidate_id, url), {}).get("status")

    def should_run(self, candidate_id: str, url: str, force: bool = False) -> bool:
        return force or self.status(candidate_id, url) not in ("done", "blocked")

    def mark(self, candidate_id: str, url: str, status: str, **extra) -> None:
        self.data["tasks"][self.key(candidate_id, url)] = {"status": status, "at": now_utc().isoformat(), **extra}
        self.save()

    def add_browser_seconds(self, seconds: float) -> None:
        self.data["browser_seconds_used"] = round(self.data["browser_seconds_used"] + max(0.0, seconds), 1)
        self.save()

    @property
    def browser_minutes_used(self) -> float:
        return self.data["browser_seconds_used"] / 60

    def minutes_left(self, budget_minutes: float) -> float:
        return budget_minutes - self.browser_minutes_used

    def save(self) -> None:
        write_json(self.paths.progress, self.data)
