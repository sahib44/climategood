"""Thin Browserbase wrapper: create a session, enforce a hard timeout, always close it.

Free plan (as of 2026-11): about 1 browser hour in total, 3 concurrent sessions, 15-minute
sessions, no stealth, CAPTCHA solving or proxies. We run one session at a time, ask Browserbase
to end the session itself at the timeout, and also release it from our side when the timer
fires, so a hung page can't burn the budget. We never request stealth, proxies or CAPTCHA
solving, and never try to get past a block.

Keys come from the environment (.env, never committed):
    BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID
"""
from __future__ import annotations

import math
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Optional

DEFAULT_TIMEOUT_SEC = 14 * 60


class MissingKeys(RuntimeError):
    pass


@dataclass
class SessionHandle:
    id: str
    connect_url: str
    timeout_sec: int
    started: float
    timed_out: threading.Event = field(default_factory=threading.Event)

    def elapsed(self, clock: Callable[[], float] = time.monotonic) -> float:
        return clock() - self.started


def _sdk_from_env() -> tuple[Any, str]:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    key, project = os.getenv("BROWSERBASE_API_KEY"), os.getenv("BROWSERBASE_PROJECT_ID")
    if not key or not project:
        raise MissingKeys("Set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID in .env (see .env.example).")
    try:
        from browserbase import Browserbase
    except ImportError as e:  # pragma: no cover
        raise MissingKeys("Install ingest deps: .venv/bin/pip install -r ingest/requirements.txt") from e
    return Browserbase(api_key=key), project


class BrowserbaseClient:
    def __init__(self, sdk: Any = None, project_id: Optional[str] = None,
                 timeout_sec: int = DEFAULT_TIMEOUT_SEC, clock: Callable[[], float] = time.monotonic):
        if sdk is None:
            sdk, project_id = _sdk_from_env()
        self.sdk = sdk
        self.project_id = project_id
        self.timeout_sec = float(timeout_sec)
        self.clock = clock
        self._released: set[str] = set()
        self._lock = threading.Lock()

    def release(self, session_id: str) -> None:
        """Ask Browserbase to end the session. Safe to call more than once."""
        with self._lock:
            if session_id in self._released:
                return
            self._released.add(session_id)
        try:
            self.sdk.sessions.update(session_id, project_id=self.project_id, status="REQUEST_RELEASE")
        except Exception:  # noqa: BLE001 - the server-side timeout ends it anyway
            pass

    @contextmanager
    def session(self, timeout_sec: Optional[int] = None) -> Iterator[SessionHandle]:
        """Yield a live session. It is released when the block exits, raises, or times out."""
        timeout = min(timeout_sec or self.timeout_sec, self.timeout_sec)
        created = self.sdk.sessions.create(project_id=self.project_id, timeout=max(60, math.ceil(timeout)),
                                           keep_alive=False)
        handle = SessionHandle(id=created.id, connect_url=getattr(created, "connect_url", ""),
                               timeout_sec=timeout, started=self.clock())

        def on_timeout() -> None:
            handle.timed_out.set()
            self.release(handle.id)

        timer = threading.Timer(timeout, on_timeout)
        timer.daemon = True
        timer.start()
        try:
            yield handle
        finally:
            timer.cancel()
            self.release(handle.id)

