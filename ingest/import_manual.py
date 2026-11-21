"""Fallback: add videos by hand (link and metadata only) when a site can't or mustn't be scraped.

    cp ingest/manual_template.csv data/ingest/manual_rows.csv     # fill in one row per video
    .venv/bin/python -m ingest.import_manual data/ingest/manual_rows.csv

Each row gets exactly the same checks as a collected item: allowlist (link_ok), required date
and publisher, the format filter from ingest/settings.json (currently disabled), the campaign
period, and the same per-candidate cap. Rows become "proposed" items and still go through
ingest/review.py. Never paste video files, only links.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

from ingest.allowlist import Allowlist, NotAllowed
from ingest.common import Paths, append_log, load_candidates, now_utc, read_json, video_id_for
from ingest.coverage import write_coverage
from ingest.extract import canonical_video_url
from ingest.selection import apply_cap, cap_for, in_campaign_period, relevance_match
from ingest.store import load_items, save_incomplete, save_item, validate_item

REQUIRED_COLUMNS = ["candidate_id", "video_url", "title", "publisher", "published_date", "venue",
                    "duration_sec", "listing_page_url", "added_by", "notes"]


def import_rows(paths: Paths, allow: Allowlist, settings: dict, candidates: list[dict], rows: list[dict]) -> dict:
    by_id = {c["id"]: c for c in candidates if c.get("id")}
    counts = {"rows": 0, "proposed": 0, "already_known": 0, "rejected": 0, "over_cap": 0}
    fresh: dict[str, list] = {}
    for n, row in enumerate(rows, start=2):  # row 1 is the header
        counts["rows"] += 1
        row = {k: (v or "").strip() for k, v in row.items() if k}
        cid = row.get("candidate_id", "")
        problems = []
        if cid not in by_id:
            problems.append(f"unknown candidate_id {cid!r}")
        if not row.get("added_by"):
            problems.append("missing added_by")
        url = row.get("video_url", "")
        try:
            allow.require(url, "link_ok")
            url = canonical_video_url(url) or url
            rule = allow.rule_for(url)
        except NotAllowed as e:
            problems.append(str(e))
            rule = None
        data = {"video_id": video_id_for(cid, url), "candidate_id": cid, "video_url": url,
                "title": row.get("title"), "publisher": row.get("publisher"),
                "published_date": row.get("published_date") or None, "venue": row.get("venue", ""),
                "duration_sec": int(row["duration_sec"]) if row.get("duration_sec", "").isdigit() else None,
                "listing_page_url": row.get("listing_page_url") or url,
                "source_type": rule.source_type if rule else "unknown", "origin": "manual",
                "fetched_at": now_utc(), "added_by": row.get("added_by") or None, "notes": row.get("notes", "")}
        item, reasons = (None, problems) if problems else validate_item(data)
        if item is None:
            counts["rejected"] += 1
            if cid in by_id:
                save_incomplete(paths, cid, row, reasons, source_type=data["source_type"], origin="manual")
            append_log(paths, "manual_row_rejected", candidate_id=cid, url=url, row=n, reasons=reasons)
            print(f"  row {n}: rejected: {'; '.join(reasons)}", file=sys.stderr)
            continue
        kw = relevance_match(item.title, settings)
        if kw is None:
            counts["rejected"] += 1
            append_log(paths, "filtered_out", candidate_id=cid, url=url, title=item.title,
                       source_type=item.source_type, reason="no format keyword in title")
            print(f"  row {n}: no format keyword in the title, not added", file=sys.stderr)
            continue
        item.relevance_keyword = kw
        if not in_campaign_period(item.published_date, by_id[cid]):
            counts["rejected"] += 1
            append_log(paths, "out_of_period", candidate_id=cid, url=url, source_type=item.source_type,
                       published_date=str(item.published_date))
            print(f"  row {n}: outside the campaign period, not added", file=sys.stderr)
            continue
        fresh.setdefault(cid, []).append(item)

    for cid, items in fresh.items():
        existing = load_items(paths, cid, ("proposed", "approved"))
        known = {i.video_id for i in existing}
        new = {i.video_id: i for i in items if i.video_id not in known}
        counts["already_known"] += len(items) - len(new)
        kept, _ = apply_cap(existing + list(new.values()), cap_for(by_id[cid], settings))
        kept_ids = {i.video_id for i in kept}
        for vid, item in new.items():
            if vid in kept_ids:
                save_item(paths, item)
                counts["proposed"] += 1
            else:
                counts["over_cap"] += 1
                append_log(paths, "over_cap", candidate_id=cid, url=item.video_url, source_type=item.source_type,
                           published_date=str(item.published_date), cap=cap_for(by_id[cid], settings))
    write_coverage(paths, candidates)
    return counts


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--config", type=Path, default=None, help="candidate config (default config/candidates.json)")
    args = ap.parse_args(argv)
    paths = Paths()
    with args.csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            print(f"CSV is missing columns: {missing}. Start from ingest/manual_template.csv.", file=sys.stderr)
            return 2
        rows = list(reader)
    counts = import_rows(paths, Allowlist.load(paths.sources), read_json(paths.settings),
                         load_candidates(args.config or paths.candidates), rows)
    print(f"{counts}\nNext: .venv/bin/python -m ingest.review --reviewer <your name>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
