"""Terminal review: a person approves, rejects or flags every proposed item.

    .venv/bin/python -m ingest.review --reviewer "<your name>"            # review the queue
    .venv/bin/python -m ingest.review --reviewer "<your name>" --candidate <id>
    .venv/bin/python -m ingest.review --publish                           # re-check transcripts, rebuild data/real

The ONLY path into data/real/ is publish_real(), which rebuilds data/real/videos.json from
approved items that have an official transcript in data/transcripts/<video_id>.json (fetched
with scripts/fetch_transcript.py, never generated). Approved items with no transcript stay in
data/ingest/approved/ marked "no_transcript" and are counted as unavailable, not searched.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Optional

from pydantic import ValidationError

from ingest.allowlist import Allowlist
from ingest.common import Paths, append_log, is_placeholder, load_candidates, now_utc, read_json, write_json
from ingest.coverage import write_coverage
from ingest.models import Decision, ProposedItem, ReviewRecord
from ingest.store import load_items, save_item

from models import Candidate, Transcript, Video  # backend schema (path set in ingest.common)


class ReviewError(ValueError):
    pass


def transcript_for(paths: Paths, video_id: str) -> Optional[Transcript]:
    f = paths.transcripts / f"{video_id}.json"
    if not f.exists():
        return None
    try:
        t = Transcript.model_validate(read_json(f))
    except ValidationError:
        return None
    return t if t.segments and t.transcript_source != "fictional" else None


def sync_transcript(paths: Paths, item: ProposedItem) -> ProposedItem:
    t = transcript_for(paths, item.video_id)
    if t is None:
        item.transcript_status = "no_transcript"
    else:
        item.transcript_status = "available"
        item.transcript_source = t.transcript_source
        item.lower_confidence = t.transcript_source == "platform_auto_captions"
    return item


def decide(paths: Paths, allow: Allowlist, item: ProposedItem, decision: Decision, reviewer: str,
           reason: str = "", venue: Optional[str] = None, duration_sec: Optional[int] = None) -> ProposedItem:
    """Record one person's decision on one item and move its file. Raises ReviewError if the
    decision can't be applied (the item is left unchanged)."""
    if not reviewer or not reviewer.strip():
        raise ReviewError("reviewer name is required")
    if decision in ("reject", "needs_fix") and not reason.strip():
        raise ReviewError(f"a reason is required to {decision.replace('_', ' ')}")
    item = item.model_copy(deep=True)
    if decision == "approve":
        allow.require(item.video_url, "link_ok")  # the allowlist may have changed since collection
        item.venue = (venue if venue is not None else item.venue).strip()
        item.duration_sec = duration_sec or item.duration_sec
        if not item.venue:
            raise ReviewError("venue is required to approve (where was it said?)")
        if not item.duration_sec:
            raise ReviewError("duration_sec is required to approve (from the publisher's page)")
        item = sync_transcript(paths, item)
    item.status = {"approve": "approved", "reject": "rejected", "needs_fix": "needs_fix"}[decision]
    item.review = ReviewRecord(reviewer=reviewer.strip(), reviewed_at=now_utc(), decision=decision, reason=reason.strip())
    save_item(paths, item)
    append_log(paths, f"review_{decision}", candidate_id=item.candidate_id, url=item.video_url,
               video_id=item.video_id, reviewer=item.review.reviewer, reason=item.review.reason,
               transcript_status=item.transcript_status)
    return item


def to_backend_video(item: ProposedItem) -> Video:
    return Video(id=item.video_id, candidate_id=item.candidate_id, title=item.title, publisher=item.publisher,
                 url=item.video_url, published_date=item.published_date, venue=item.venue,
                 duration_sec=item.duration_sec, transcript_path=f"../transcripts/{item.video_id}.json",
                 transcript_source=item.transcript_source, fictional=False)


def to_backend_candidate(c: dict) -> Optional[Candidate]:
    fields = ("id", "name", "office", "party", "jurisdiction", "election_date")
    if any(not c.get(k) or is_placeholder(c.get(k)) for k in fields):
        return None
    urls = [s.get("url") if isinstance(s, dict) else s for s in c.get("sources", [])]
    return Candidate(**{k: c[k] for k in fields}, sources=[u for u in urls if u and not is_placeholder(u)],
                     fictional=False)


def publish_real(paths: Paths, candidates: list[dict]) -> dict:
    """Rebuild data/real/{candidates,videos}.json. Only approved items with a transcript go in."""
    approved = [sync_transcript(paths, i) for i in load_items(paths, states=("approved",))]
    for item in approved:  # keep the item files' transcript_status current
        save_item(paths, item)
    videos = [to_backend_video(i) for i in approved
              if i.status == "approved" and i.transcript_status == "available" and i.venue and i.duration_sec]
    cands = [bc for bc in (to_backend_candidate(c) for c in candidates) if bc]
    write_json(paths.real_dir / "candidates.json", {
        "_note": "REAL candidates. Generated by ingest/review.py from config/candidates.json. Do not hand-edit.",
        "candidates": [c.model_dump(mode="json") for c in cands]})
    write_json(paths.real_dir / "videos.json", {
        "_note": "REAL videos. Generated by ingest/review.py from human-approved items with official transcripts. Do not hand-edit.",
        "videos": [v.model_dump(mode="json") for v in sorted(videos, key=lambda v: (v.candidate_id, v.published_date, v.id))]})
    write_coverage(paths, candidates)
    return {"candidates": len(cands), "videos": len(videos),
            "approved_without_transcript": sum(i.transcript_status == "no_transcript" for i in approved)}


def preview_text(paths: Paths, item: ProposedItem, n: int = 300) -> str:
    t = transcript_for(paths, item.video_id)
    if t:
        return f"[{t.transcript_source}] " + " ".join(s.text for s in t.segments)[:n]
    if item.caption_text:
        return "[text on the publisher's page, untimed] " + item.caption_text[:n]
    return "(no transcript yet: run scripts/fetch_transcript.py " + item.video_id + " --url <video url>)"


def show(paths: Paths, allow: Allowlist, item: ProposedItem, out=sys.stdout) -> None:
    rule = allow.rule_for(item.video_url) if allow.allows(item.video_url, "link_ok") else None
    print("\n" + "-" * 72, file=out)
    print(f"{item.video_id}   [{item.status}]  candidate: {item.candidate_id}", file=out)
    print(f"  title:      {item.title}", file=out)
    print(f"  publisher:  {item.publisher}", file=out)
    print(f"  date:       {item.published_date}    venue: {item.venue or '(not set)'}    "
          f"duration: {item.duration_sec or '(not set)'} s", file=out)
    print(f"  video URL:  {item.video_url}", file=out)
    print(f"  found on:   {item.listing_page_url}  ({item.origin}, {item.source_type})", file=out)
    print(f"  screenshot: {item.screenshot_path or '(none)'}", file=out)
    print(f"  allowlist:  {'ok' if rule else 'NOT ALLOWED NOW'}", file=out)
    if item.review and item.status == "needs_fix":
        print(f"  needs fix:  {item.review.reason} ({item.review.reviewer})", file=out)
    print(f"  transcript: {preview_text(paths, item)}", file=out)
    print("  Open the video at the URL and check the speaker, date and publisher before approving.", file=out)


def interactive(paths: Paths, allow: Allowlist, candidates: list[dict], reviewer: str,
                candidate_id: Optional[str] = None, ask: Callable[[str], str] = input, out=sys.stdout) -> None:
    queue = [i for i in load_items(paths, candidate_id, ("proposed",))]
    print(f"{len(queue)} item(s) to review. Reviewer: {reviewer}", file=out)
    for item in queue:
        show(paths, allow, item, out)
        while True:
            choice = ask("  [a]pprove / [r]eject / [n]eeds fix / [s]kip / [q]uit: ").strip().lower()[:1]
            if choice == "q":
                print(f"Published: {publish_real(paths, candidates)}", file=out)
                return
            if choice == "s":
                break
            try:
                if choice == "a":
                    venue = item.venue or ask("  venue (where it was said): ")
                    dur = item.duration_sec or int(ask("  duration in seconds (from the publisher's page): ") or 0)
                    done = decide(paths, allow, item, "approve", reviewer, venue=venue, duration_sec=dur)
                    if done.transcript_status == "no_transcript":
                        print("  Approved, but there is no transcript yet: marked 'no_transcript', not searched.", file=out)
                elif choice == "r":
                    decide(paths, allow, item, "reject", reviewer, reason=ask("  reason: "))
                elif choice == "n":
                    decide(paths, allow, item, "needs_fix", reviewer, reason=ask("  what needs fixing: "))
                else:
                    continue
                break
            except (ReviewError, ValueError) as e:
                print(f"  Not applied: {e}", file=out)
    print(f"Published: {publish_real(paths, candidates)}", file=out)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reviewer", help="your name (recorded with every decision)")
    ap.add_argument("--candidate", help="only this candidate id")
    ap.add_argument("--config", type=Path, default=None, help="candidate config (default config/candidates.json)")
    ap.add_argument("--publish", action="store_true", help="re-check transcripts and rebuild data/real only")
    args = ap.parse_args(argv)
    paths = Paths()
    candidates = load_candidates(args.config or paths.candidates)
    allow = Allowlist.load(paths.sources)
    if args.publish:
        print(publish_real(paths, candidates))
        return 0
    if not args.reviewer:
        ap.error("--reviewer is required to review")
    interactive(paths, allow, candidates, args.reviewer, args.candidate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
