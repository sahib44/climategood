"""Pre-fill the manual CSV with every video collect found but could not complete.

    .venv/bin/python -m ingest.prefill_manual        # writes data/ingest/manual_rows.csv

Fills candidate_id, video_url, title (as found) and listing_page_url. Leaves publisher,
published_date, venue, duration_sec and added_by EMPTY on purpose: a person opens each video on
its official page and copies them from there. Nothing is guessed. Rows already present in the
CSV are kept as they are, so re-running never overwrites a person's work.
"""
from __future__ import annotations

import csv
from typing import Optional

from ingest.common import Paths
from ingest.import_manual import REQUIRED_COLUMNS
from ingest.store import load_incomplete, load_items


def prefill(paths: Paths, out_name: str = "manual_rows.csv") -> tuple[int, int]:
    out = paths.ingest_dir / out_name
    existing = list(csv.DictReader(out.open(newline="", encoding="utf-8"))) if out.exists() else []
    have = {(r["candidate_id"], r["video_url"]) for r in existing}
    have |= {(i.candidate_id, i.video_url) for i in load_items(paths)}  # already proposed/reviewed
    new = []
    cids = sorted(d.name for d in paths.rejected.iterdir()) if paths.rejected.exists() else []
    for cid in cids:
        for rec in load_incomplete(paths, cid):
            found = rec.get("found", {})
            url = found.get("video_url")
            if not url or (cid, url) in have:
                continue
            have.add((cid, url))
            new.append({"candidate_id": cid, "video_url": url, "title": found.get("title") or "",
                        "publisher": "", "published_date": "", "venue": "", "duration_sec": "",
                        "listing_page_url": rec.get("listing_page_url", ""), "added_by": "",
                        "notes": "found by collect; " + "; ".join(rec.get("reasons", []))})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        w.writeheader()
        w.writerows(existing + new)
    return len(existing), len(new)


def main(argv: Optional[list[str]] = None) -> int:
    paths = Paths()
    kept, added = prefill(paths)
    print(f"{paths.ingest_dir / 'manual_rows.csv'}: kept {kept} row(s), added {added}. "
          "Fill in publisher, published_date (YYYY-MM-DD), venue, duration_sec and added_by from each "
          "video's official page, then run: .venv/bin/python -m ingest.import_manual data/ingest/manual_rows.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
