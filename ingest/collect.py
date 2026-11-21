"""Offline batch job: find official video listings for each configured candidate.

    .venv/bin/python -m ingest.collect --dry-run                       # plan only, no network
    .venv/bin/python -m ingest.collect --candidate <id>                # real run, one candidate
    .venv/bin/python -m ingest.collect --budget-minutes 20             # stop before 20 browser-min

For every candidate and every listing URL in config/candidates.json, the same steps run:
  allowlist (automated_fetch) -> load page in Browserbase -> block check -> screenshot (local
  evidence only) -> deterministic extraction -> allowlist each video URL (link_ok) -> required
  fields (date, publisher) -> format filter (logged) -> campaign period -> same cap for everyone
  -> data/ingest/proposed/<candidate_id>/<video_id>.json with status "proposed".
Nothing reaches data/real/ until a person approves it with ingest/review.py.
Blocked pages, login walls and CAPTCHAs are never worked around: the URL goes to
data/ingest/manual_queue.csv for a person to add by hand through the manual CSV.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Protocol

from ingest.allowlist import Allowlist, NotAllowed
from ingest.common import (Paths, append_log, is_placeholder, load_candidates, now_utc, read_json,
                           source_urls, video_id_for)
from ingest.coverage import write_coverage
from ingest.extract import extract_listing, looks_blocked
from ingest.progress import Progress
from ingest.selection import apply_cap, cap_for, in_campaign_period, relevance_match
from ingest.store import load_items, save_incomplete, save_item, validate_item

MANUAL_QUEUE_FIELDS = ["candidate_id", "listing_page_url", "reason", "logged_at"]


def queue_for_manual(paths: Paths, candidate_id: str, url: str, reason: str) -> None:
    """Send a URL we may not or could not load automatically to the manual CSV fallback."""
    paths.manual_queue.parent.mkdir(parents=True, exist_ok=True)
    new = not paths.manual_queue.exists()
    with paths.manual_queue.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANUAL_QUEUE_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"candidate_id": candidate_id, "listing_page_url": url, "reason": reason,
                    "logged_at": now_utc().isoformat()})
    append_log(paths, "manual_queue", candidate_id=candidate_id, url=url, reason=reason)


def process_listing(paths: Paths, allow: Allowlist, settings: dict, candidate: dict, listing_url: str,
                    html: str, *, fetched_at: datetime, session_id: Optional[str],
                    screenshot_path: Optional[str]) -> dict:
    """Turn one fetched listing page into proposed items. Pure apart from writing data/ingest/."""
    cid = candidate["id"]
    rule = allow.rule_for(listing_url)
    counts = {"found": 0, "not_allowlisted": 0, "incomplete": 0, "filtered_out": 0,
              "out_of_period": 0, "over_cap": 0, "proposed": 0, "already_known": 0}
    fresh = []
    for raw in extract_listing(html, listing_url):
        counts["found"] += 1
        url = raw["video_url"]
        try:
            allow.require(url, "link_ok")
        except NotAllowed as e:
            counts["not_allowlisted"] += 1
            append_log(paths, "not_allowlisted", candidate_id=cid, url=url, reason=str(e))
            continue
        data = {**raw, "video_id": video_id_for(cid, url), "candidate_id": cid, "venue": "",
                "listing_page_url": listing_url, "source_type": rule.source_type, "origin": "browserbase",
                "fetched_at": fetched_at, "browserbase_session_id": session_id, "screenshot_path": screenshot_path}
        item, reasons = validate_item(data)
        if item is None:
            counts["incomplete"] += 1
            save_incomplete(paths, cid, raw, reasons, listing_page_url=listing_url, source_type=rule.source_type)
            append_log(paths, "incomplete", candidate_id=cid, url=url, reasons=reasons)
            continue
        kw = relevance_match(item.title, settings)
        if kw is None:
            counts["filtered_out"] += 1
            append_log(paths, "filtered_out", candidate_id=cid, url=url, title=item.title,
                       source_type=rule.source_type, reason="no format keyword in title")
            continue
        if not in_campaign_period(item.published_date, candidate):
            counts["out_of_period"] += 1
            append_log(paths, "out_of_period", candidate_id=cid, url=url, published_date=str(item.published_date),
                       source_type=rule.source_type)
            continue
        item.relevance_keyword = kw
        fresh.append(item)

    existing = [i for i in load_items(paths, cid, ("proposed", "approved"))]
    known = {i.video_id for i in existing}
    pool = existing + [i for i in fresh if i.video_id not in known]
    counts["already_known"] = sum(1 for i in fresh if i.video_id in known)
    kept, over = apply_cap(pool, cap_for(candidate, settings))
    kept_ids = {i.video_id for i in kept}
    for item in fresh:
        if item.video_id in known:
            continue
        if item.video_id in kept_ids:
            save_item(paths, item)
            counts["proposed"] += 1
        else:
            counts["over_cap"] += 1
            append_log(paths, "over_cap", candidate_id=cid, url=item.video_url, source_type=item.source_type,
                       published_date=str(item.published_date), cap=cap_for(candidate, settings))
    append_log(paths, "listing_done", candidate_id=cid, url=listing_url, session_id=session_id, **counts)
    return counts


class Fetcher(Protocol):
    def fetch(self, url: str, screenshot_path: Path) -> tuple[Optional[int], str]: ...


class PlaywrightFetcher:
    """Loads one URL at a time in an existing Browserbase session (CDP). No clicks, no forms,
    no following links found on the page: only the listing URLs a person put in the config."""

    def __init__(self, connect_url: str, nav_timeout_ms: int):
        self.connect_url, self.nav_timeout_ms = connect_url, nav_timeout_ms

    def __enter__(self) -> "PlaywrightFetcher":
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.connect_url)
        ctx = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        self._page = ctx.pages[0] if ctx.pages else ctx.new_page()
        return self

    def fetch(self, url: str, screenshot_path: Path) -> tuple[Optional[int], str]:
        resp = self._page.goto(url, timeout=self.nav_timeout_ms, wait_until="domcontentloaded")
        self._page.wait_for_timeout(1500)
        html = self._page.content()
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(screenshot_path))
        return (resp.status if resp else None), html

    def __exit__(self, *exc) -> None:
        try:
            self._browser.close()
        finally:
            self._pw.stop()


def plan(paths: Paths, allow: Allowlist, candidates: list[dict], settings: dict, progress: Progress,
         force: bool = False) -> list[dict]:
    """Classify every (candidate, listing URL) without touching the network."""
    rows = []
    for c in candidates:
        cid = c.get("id", "?")
        problems = [k for k in ("id", "name", "office", "jurisdiction", "election_date")
                    if not c.get(k) or is_placeholder(c.get(k))]
        urls = source_urls(c)
        if problems:
            rows.append({"candidate_id": cid, "url": None, "action": "skip", "why": f"placeholder or missing: {', '.join(problems)}"})
        if not urls:
            rows.append({"candidate_id": cid, "url": None, "action": "skip", "why": "no source URLs listed"})
        for url in urls:
            if is_placeholder(url):
                rows.append({"candidate_id": cid, "url": url, "action": "skip", "why": "placeholder URL"})
                continue
            if not progress.should_run(cid, url, force):
                rows.append({"candidate_id": cid, "url": url, "action": "skip", "why": f"already {progress.status(cid, url)} (use --force)"})
                continue
            try:
                allow.require(url, "automated_fetch")
                rows.append({"candidate_id": cid, "url": url, "action": "fetch", "why": allow.rule_for(url).source_type})
            except NotAllowed as e:
                action = "manual" if allow.allows(url, "link_ok") else "refuse"
                rows.append({"candidate_id": cid, "url": url, "action": action, "why": str(e)})
    return rows


def run(paths: Paths, *, candidates: list[dict], settings: dict, allow: Allowlist, budget_minutes: float,
        force: bool = False, client_factory: Optional[Callable] = None,
        fetcher_factory: Optional[Callable] = None, out=sys.stdout) -> dict:
    progress = Progress(paths)
    rows = plan(paths, allow, candidates, settings, progress, force)
    by_cand = {c["id"]: c for c in candidates if c.get("id")}
    totals = {"listings_done": 0, "blocked": 0, "manual": 0, "failed": 0, "proposed": 0}

    for r in rows:
        if r["action"] in ("manual", "refuse"):
            queue_for_manual(paths, r["candidate_id"], r["url"], r["why"])
            progress.mark(r["candidate_id"], r["url"], "blocked", reason=r["why"])
            totals["manual"] += 1

    if client_factory is None:
        from ingest.browserbase_client import BrowserbaseClient

        client_factory = lambda: BrowserbaseClient(timeout_sec=settings["session_timeout_sec"])  # noqa: E731
    if fetcher_factory is None:
        fetcher_factory = lambda handle: PlaywrightFetcher(handle.connect_url, settings["navigation_timeout_ms"])  # noqa: E731

    fetch_rows = [r for r in rows if r["action"] == "fetch"]
    client = client_factory() if fetch_rows else None
    for cid in dict.fromkeys(r["candidate_id"] for r in fetch_rows):  # one session per candidate
        left = progress.minutes_left(budget_minutes)
        if left < settings["min_minutes_to_start_session"]:
            print(f"Budget reached ({progress.browser_minutes_used:.1f} of {budget_minutes} min). Stopping; re-run to resume.", file=out)
            append_log(paths, "budget_stop", minutes_used=progress.browser_minutes_used, budget=budget_minutes)
            break
        timeout = int(min(settings["session_timeout_sec"], left * 60))
        urls = [r["url"] for r in fetch_rows if r["candidate_id"] == cid]
        with client.session(timeout) as handle:
            append_log(paths, "session_start", candidate_id=cid, session_id=handle.id, timeout_sec=timeout)
            try:
                with fetcher_factory(handle) as fetcher:
                    for url in urls:
                        if handle.timed_out.is_set():
                            progress.mark(cid, url, "failed", reason="session timeout")
                            totals["failed"] += 1
                            continue
                        shot = paths.evidence / cid / f"{video_id_for(cid, url)}.png"
                        try:
                            status, html = fetcher.fetch(url, shot)
                        except Exception as e:  # noqa: BLE001 - log and move on; resume retries it
                            progress.mark(cid, url, "failed", reason=f"{type(e).__name__}: {e}"[:300])
                            append_log(paths, "fetch_failed", candidate_id=cid, url=url, error=str(e)[:300])
                            totals["failed"] += 1
                            continue
                        blocked = looks_blocked(status, html)
                        if blocked:
                            queue_for_manual(paths, cid, url, f"blocked: {blocked}")
                            progress.mark(cid, url, "blocked", reason=blocked)
                            totals["blocked"] += 1
                            continue
                        counts = process_listing(
                            paths, allow, settings, by_cand[cid], url, html, fetched_at=now_utc(),
                            session_id=handle.id, screenshot_path=str(shot.relative_to(paths.root)) if shot.exists() else None)
                        progress.mark(cid, url, "done", **counts)
                        totals["listings_done"] += 1
                        totals["proposed"] += counts["proposed"]
            finally:
                progress.add_browser_seconds(handle.elapsed())
                append_log(paths, "session_end", candidate_id=cid, session_id=handle.id,
                           seconds=round(handle.elapsed(), 1), timed_out=handle.timed_out.is_set())
    write_coverage(paths, candidates)
    return totals


def print_plan(rows: list[dict], progress: Progress, budget_minutes: float, settings: dict, out=sys.stdout) -> None:
    print("DRY RUN: no network, no Browserbase session, nothing written.\n", file=out)
    for r in rows:
        url = r["url"] or "-"
        print(f"  [{r['action']:<6}] {r['candidate_id']:<28} {url}\n           {r['why']}", file=out)
    n_fetch = sum(r["action"] == "fetch" for r in rows)
    sessions = len({r["candidate_id"] for r in rows if r["action"] == "fetch"})
    print(f"\nWould load {n_fetch} listing page(s) in {sessions} session(s), one candidate per session, "
          f"each capped at {settings['session_timeout_sec'] // 60} min.", file=out)
    print(f"Browser time used so far: {progress.browser_minutes_used:.1f} min of a {budget_minutes} min budget.", file=out)
    print(f"Per-candidate cap: {settings['per_candidate_cap']} (same for everyone).", file=out)
    print("Selection rule reminder: 3 completed races, same office level, 2 candidates per race from "
          "different parties, winners and losers. A person picks them; this script never does.", file=out)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, default=None, help="candidate config (default config/candidates.json)")
    ap.add_argument("--candidate", help="only this candidate id")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; no network, writes nothing")
    ap.add_argument("--budget-minutes", type=float, default=None, help="total browser minutes this job may use")
    ap.add_argument("--force", action="store_true", help="re-run listings already done or blocked")
    args = ap.parse_args(argv)

    paths = Paths()
    settings = read_json(paths.settings)
    allow = Allowlist.load(paths.sources)
    candidates = load_candidates(args.config or paths.candidates)
    if args.candidate:
        candidates = [c for c in candidates if c.get("id") == args.candidate]
        if not candidates:
            print(f"No candidate with id {args.candidate!r} in the config.", file=sys.stderr)
            return 2
    budget = args.budget_minutes if args.budget_minutes is not None else settings["budget_minutes"]
    progress = Progress(paths)
    if args.dry_run:
        print_plan(plan(paths, allow, candidates, settings, progress, args.force), progress, budget, settings)
        return 0
    totals = run(paths, candidates=candidates, settings=settings, allow=allow, budget_minutes=budget, force=args.force)
    print(f"Done: {totals}. Browser minutes used in total: {Progress(paths).browser_minutes_used:.1f}.")
    print("Next: .venv/bin/python -m ingest.review --reviewer <your name>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
