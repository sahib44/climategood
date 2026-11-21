"""Pre-fill the manual CSV with every video collect found but could not complete.

    .venv/bin/python -m ingest.prefill_manual        # writes data/ingest/manual_rows.csv

Fills candidate_id, video_url, title (as found) and listing_page_url. With --oembed it also
fills title and publisher for YouTube rows from YouTube's public oEmbed endpoint (the uploader's
channel name and the video's own title), and marks unavailable videos. published_date, venue,
duration_sec and added_by stay EMPTY on purpose: a person opens each video on its official page
and copies them from there. Nothing is guessed. Re-running never overwrites a filled-in field.
"""
from __future__ import annotations

import argparse
import csv
import json
from typing import Callable, Optional
from urllib.parse import quote

from ingest.common import Paths, now_utc
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


def fill_from_oembed(paths: Paths, get: Optional[Callable] = None, out_name: str = "manual_rows.csv") -> int:
    """Fill blank publisher (and the title) of YouTube rows from oEmbed. Returns rows changed."""
    if get is None:
        from ingest.verify_links import http_get as get
    out = paths.ingest_dir / out_name
    rows = list(csv.DictReader(out.open(newline="", encoding="utf-8")))
    changed = 0
    for r in rows:
        if r["publisher"].strip() or "youtube.com/watch" not in r["video_url"] or "VIDEO UNAVAILABLE" in r["notes"]:
            continue
        status, body = get("https://www.youtube.com/oembed?format=json&url=" + quote(r["video_url"], safe=""))
        if status != 200:
            r["notes"] = (r["notes"] + f"; VIDEO UNAVAILABLE (oEmbed {status}): reject or remove").strip("; ")
            changed += 1
            continue
        d = json.loads(body)
        r["publisher"] = d.get("author_name", "")
        r["title"] = d.get("title") or r["title"]
        r["notes"] = (r["notes"].replace("; TITLE IS THE PAGE TITLE: copy the video title from YouTube", "")
                      + f"; title and publisher from YouTube oEmbed {now_utc().date()} ({d.get('author_url', '')}); confirm").strip("; ")
        changed += 1
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return changed


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--oembed", action="store_true", help="fill title/publisher of YouTube rows from oEmbed")
    args = ap.parse_args(argv)
    paths = Paths()
    kept, added = prefill(paths)
    if args.oembed:
        print(f"oEmbed: filled {fill_from_oembed(paths)} row(s).")
    print(f"{paths.ingest_dir / 'manual_rows.csv'}: kept {kept} row(s), added {added}. "
          "Fill in publisher, published_date (YYYY-MM-DD), venue, duration_sec and added_by from each "
          "video's official page, then run: .venv/bin/python -m ingest.import_manual data/ingest/manual_rows.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
