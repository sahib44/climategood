"""Re-check approved items: does the link still load, is the date the same, is the publisher's
domain still on the allowlist? Writes data/ingest/link_check.json and exits 1 if anything changed.

    .venv/bin/python -m ingest.verify_links

YouTube links are checked through YouTube's public oEmbed endpoint (an official API for
embedding; a private or removed video returns an error). Other pages are fetched only if their
domain allows automated_fetch; otherwise the item is listed for a person to check by hand.
This script never downloads media.
"""
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from typing import Callable, Optional
from urllib.parse import quote

from ingest.allowlist import Allowlist, host_of
from ingest.common import Paths, now_utc, write_json
from ingest.extract import extract_listing
from ingest.store import load_items

USER_AGENT = "OnRecordLinkCheck/0.1 (offline link check; no media download)"
HttpGet = Callable[[str], tuple[Optional[int], str]]


def _ssl_context() -> ssl.SSLContext:
    """Some Python installs (python.org builds on macOS) ship without CA certificates."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:  # pragma: no cover
        return ssl.create_default_context()


def http_get(url: str, timeout: float = 20) -> tuple[Optional[int], str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:  # noqa: S310
            return r.status, r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, TimeoutError) as e:
        return None, str(e)


def check_item(item, allow: Allowlist, get: HttpGet = http_get) -> dict:
    res = {"video_id": item.video_id, "candidate_id": item.candidate_id, "url": item.video_url, "flags": []}
    if not allow.allows(item.video_url, "link_ok"):
        res["flags"].append("publisher domain no longer on the allowlist")
        return res
    host = host_of(item.video_url)
    if host in ("youtube.com", "youtu.be") or host.endswith(".youtube.com"):
        status, body = get(f"https://www.youtube.com/oembed?format=json&url={quote(item.video_url, safe='')}")
        res["http_status"] = status
        if status != 200:
            res["flags"].append(f"video no longer available (oEmbed status {status}); may be private or removed")
            return res
        try:
            author = json.loads(body).get("author_name", "")
        except json.JSONDecodeError:
            author = ""
        res["channel_now"] = author
        res["date_checked"] = False
        res["note"] = "oEmbed gives no date; check the date by hand if the channel name changed"
        return res
    if not allow.allows(item.video_url, "automated_fetch"):
        res["flags"].append("manual check needed (automated fetch not allowed for this domain)")
        return res
    status, html = get(item.video_url)
    res["http_status"] = status
    if status != 200:
        res["flags"].append(f"page did not load (status {status})")
        return res
    found = [f for f in extract_listing(html, item.video_url) if f.get("published_date")]
    if found:
        res["date_checked"] = True
        if all(f["published_date"] != item.published_date for f in found):
            res["flags"].append(f"date changed: approved {item.published_date}, page now {found[0]['published_date']}")
    else:
        res["date_checked"] = False
    return res


def verify_all(paths: Paths, allow: Allowlist, get: HttpGet = http_get) -> dict:
    results = [check_item(i, allow, get) for i in load_items(paths, states=("approved",))]
    report = {"checked_at": now_utc().isoformat(), "items": results,
              "flagged": [r for r in results if r["flags"]]}
    write_json(paths.link_check, report)
    return report


def main(argv: Optional[list[str]] = None) -> int:
    paths = Paths()
    report = verify_all(paths, Allowlist.load(paths.sources))
    for r in report["flagged"]:
        print(f"FLAG {r['candidate_id']} {r['url']}: {'; '.join(r['flags'])}")
    print(f"Checked {len(report['items'])} approved item(s); {len(report['flagged'])} flagged. "
          f"Details: {paths.link_check.relative_to(paths.root)}")
    return 1 if report["flagged"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
