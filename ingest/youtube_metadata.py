"""Fill published_date and duration_sec for YouTube rows from the official YouTube Data API v3.

    .venv/bin/python -m ingest.youtube_metadata          # updates data/ingest/manual_rows.csv

Needs YOUTUBE_API_KEY in .env (Google Cloud console -> enable "YouTube Data API v3" -> API key).
This is YouTube's own API for video metadata, so nothing is scraped. One videos.list call covers
50 videos and costs 1 quota unit (the free quota is 10,000 units a day).

- published_date: the upload date, converted to the candidate's state time zone (Kansas: Central;
  Florida, New Hampshire: Eastern), because publishedAt is UTC and an evening upload would
  otherwise land on the next day.
- duration_sec: from contentDetails.duration.
- The channel name the API returns is compared with the row's publisher; a mismatch is noted.
- A video the API doesn't return is private or removed, and is marked so a person drops it.
Never overwrites a field a person already filled. Venue is never filled: YouTube has no venue.

YouTube's API policies limit how long API data may be kept without refreshing; re-run this (or
ingest.verify_links) before relying on old rows. Check the current policy if this goes beyond the
hackathon.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import parse_qs, urlencode, urlsplit
from zoneinfo import ZoneInfo

from ingest.common import Paths, load_candidates, now_utc
from ingest.extract import iso_duration_sec
from ingest.import_manual import REQUIRED_COLUMNS

API = "https://www.googleapis.com/youtube/v3/videos"
STATE_TZ = {"Kansas": "America/Chicago", "Florida": "America/New_York", "New Hampshire": "America/New_York"}


class MissingKey(RuntimeError):
    pass


def _key() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # pragma: no cover
        pass
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise MissingKey("Set YOUTUBE_API_KEY in .env (see the docstring of ingest/youtube_metadata.py).")
    return key


def video_id(url: str) -> Optional[str]:
    parts = urlsplit(url)
    if (parts.hostname or "").removeprefix("www.") == "youtube.com" and parts.path == "/watch":
        return (parse_qs(parts.query).get("v") or [None])[0]
    return None


def fetch(ids: list[str], key: str, get: Callable) -> dict[str, dict]:
    out = {}
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        status, body = get(API + "?" + urlencode({"part": "snippet,contentDetails", "id": ",".join(batch), "key": key}))
        if status != 200:
            raise RuntimeError(f"YouTube Data API returned {status}: {body[:300]}")
        for item in json.loads(body).get("items", []):
            out[item["id"]] = item
    return out


def fill(paths: Paths, candidates: list[dict], get: Optional[Callable] = None, key: Optional[str] = None,
         out_name: str = "manual_rows.csv") -> dict:
    if get is None:
        from ingest.verify_links import http_get as get
    key = key or _key()
    tz_for = {c["id"]: ZoneInfo(STATE_TZ.get(c.get("jurisdiction", ""), "UTC")) for c in candidates if c.get("id")}
    path = paths.ingest_dir / out_name
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    todo = [r for r in rows if video_id(r["video_url"]) and (not r["published_date"].strip() or not r["duration_sec"].strip())
            and "VIDEO UNAVAILABLE" not in r["notes"]]
    found = fetch(sorted({video_id(r["video_url"]) for r in todo}), key, get) if todo else {}
    counts = {"rows_checked": len(todo), "filled": 0, "unavailable": 0, "channel_mismatch": 0}
    today = now_utc().date()
    for r in todo:
        item = found.get(video_id(r["video_url"]))
        if item is None:
            r["notes"] = (r["notes"] + "; VIDEO UNAVAILABLE (YouTube API: private or removed): reject or remove").strip("; ")
            counts["unavailable"] += 1
            continue
        snip, details = item.get("snippet", {}), item.get("contentDetails", {})
        if not r["published_date"].strip() and snip.get("publishedAt"):
            utc = datetime.fromisoformat(snip["publishedAt"].replace("Z", "+00:00"))
            r["published_date"] = utc.astimezone(tz_for.get(r["candidate_id"], ZoneInfo("UTC"))).date().isoformat()
        if not r["duration_sec"].strip():
            sec = iso_duration_sec(details.get("duration", ""))
            r["duration_sec"] = str(sec) if sec else ""
        channel = snip.get("channelTitle", "")
        if r["publisher"].strip() and channel and channel != r["publisher"].strip():
            r["notes"] += f"; CHANNEL MISMATCH: API says {channel!r}"
            counts["channel_mismatch"] += 1
        r["notes"] = (r["notes"] + f"; date (upload, local time) and duration from YouTube Data API {today}").strip("; ")
        counts["filled"] += 1
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return counts


def main(argv: Optional[list[str]] = None) -> int:
    paths = Paths()
    try:
        counts = fill(paths, load_candidates(paths.candidates))
    except MissingKey as e:
        print(e)
        return 2
    print(f"{counts}\nVenue and added_by are still yours to fill. Then: "
          ".venv/bin/python -m ingest.import_manual data/ingest/manual_rows.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
