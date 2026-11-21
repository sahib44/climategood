"""Deterministic extraction of video links from a listing page. No LLM.

Page content is untrusted. This module only reads structure (JSON-LD VideoObject, <iframe>
embeds, <a> links to known video URL shapes, <track> captions, elements marked as transcripts).
Text on the page is never interpreted as an instruction: it can only ever become a title or
caption string, and everything returned is validated and allowlist-checked by the caller.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import parse_qs, urljoin, urlsplit

from ingest.allowlist import unwrap_archive
from ingest.common import parse_date

_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_ISO_DUR = re.compile(r"^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$", re.I)
MAX_TITLE = 300


def canonical_video_url(url: str) -> Optional[str]:
    """Return the publisher's canonical watch URL for a link, or None if it isn't a video link.

    Archive-wrapped links (web.archive.org/web/<ts>/<url>) are unwrapped first, so an archived
    campaign page that embeds a YouTube video yields the live YouTube watch URL.
    """
    url, _ = unwrap_archive(url)
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        vid = parts.path.strip("/").split("/")[0]
    elif host in ("youtube.com", "youtube-nocookie.com"):
        if parts.path == "/watch":
            vid = (parse_qs(parts.query).get("v") or [""])[0]
        elif parts.path.startswith(("/embed/", "/live/", "/shorts/", "/v/")):
            vid = parts.path.split("/")[2] if len(parts.path.split("/")) > 2 else ""
        else:
            return None
    elif host.endswith("c-span.org") and parts.path.startswith("/video/"):
        return f"https://www.c-span.org{parts.path}" + (f"?{parts.query}" if parts.query else "")
    else:
        return None
    return f"https://www.youtube.com/watch?v={vid}" if _YT_ID.match(vid or "") else None


def iso_duration_sec(value: str) -> Optional[int]:
    m = _ISO_DUR.match((value or "").strip())
    if not m or not any(m.groups()):
        return None
    d, h, mi, s = (float(g) if g else 0.0 for g in m.groups())
    total = int(d * 86400 + h * 3600 + mi * 60 + s)
    return total or None


def _clean(text: Optional[str], limit: int = MAX_TITLE) -> Optional[str]:
    if not text:
        return None
    t = re.sub(r"\s+", " ", str(text)).strip()
    return t[:limit] or None


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.jsonld: list[str] = []
        self.iframes: list[dict] = []
        self.links: list[tuple[str, str]] = []  # (href, text)
        self.tracks: list[str] = []
        self.transcript_text: list[str] = []
        self._in_jsonld = False
        self._jsonld_buf: list[str] = []
        self._link_stack: list[list] = []
        self._transcript_depth = 0
        self._depth = 0
        self._skip = 0  # inside <script>/<style> that isn't JSON-LD

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        self._depth += 1
        if tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self._in_jsonld, self._jsonld_buf = True, []
            else:
                self._skip += 1
        elif tag == "style":
            self._skip += 1
        elif tag == "iframe" and a.get("src"):
            self.iframes.append({"src": a["src"], "title": a.get("title", "")})
        elif tag == "a" and a.get("href"):
            self._link_stack.append([a["href"], []])
        elif tag == "track" and a.get("kind", "captions") in ("captions", "subtitles") and a.get("src"):
            self.tracks.append(a["src"])
        marker = f"{a.get('id', '')} {a.get('class', '')}".lower()
        if self._transcript_depth == 0 and "transcript" in marker:
            self._transcript_depth = self._depth

    def handle_endtag(self, tag):
        if tag == "script":
            if self._in_jsonld:
                self.jsonld.append("".join(self._jsonld_buf))
                self._in_jsonld = False
            elif self._skip:
                self._skip -= 1
        elif tag == "style" and self._skip:
            self._skip -= 1
        elif tag == "a" and self._link_stack:
            href, buf = self._link_stack.pop()
            self.links.append((href, "".join(buf)))
        if self._transcript_depth and self._depth <= self._transcript_depth:
            self._transcript_depth = 0
        self._depth -= 1

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_buf.append(data)
            return
        if self._skip:
            return
        for entry in self._link_stack:
            entry[1].append(data)
        if self._transcript_depth:
            self.transcript_text.append(data)


def _video_objects(blob: str) -> list[dict]:
    try:
        data = json.loads(blob)
    except (json.JSONDecodeError, ValueError):
        return []
    stack, found = [data], []
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            types = node.get("@type")
            types = types if isinstance(types, list) else [types]
            if "VideoObject" in types:
                found.append(node)
            stack.extend(v for k, v in node.items() if k in ("@graph", "video", "itemListElement", "item"))
    return found


def extract_listing(html: str, page_url: str) -> list[dict]:
    """Find video items on one listing page.

    Returns dicts with: video_url, title, published_date, publisher, duration_sec, caption_text.
    Missing fields are None; the caller rejects items missing a date or publisher.
    """
    p = _Parser()
    p.feed(html)
    p.close()
    items: dict[str, dict] = {}

    def add(url: Optional[str], **fields) -> None:
        if not url:
            return
        cur = items.setdefault(url, {"video_url": url, "title": None, "published_date": None,
                                     "publisher": None, "duration_sec": None, "caption_text": None})
        for k, v in fields.items():
            if v and not cur.get(k):
                cur[k] = v

    for blob in p.jsonld:
        for vo in _video_objects(blob):
            raw = vo.get("embedUrl") or vo.get("contentUrl") or vo.get("url") or ""
            url = canonical_video_url(urljoin(page_url, raw)) if isinstance(raw, str) else None
            pub = vo.get("publisher") or vo.get("author")
            pub_name = pub.get("name") if isinstance(pub, dict) else (pub if isinstance(pub, str) else None)
            add(url, title=_clean(vo.get("name")), published_date=parse_date(vo.get("uploadDate") or vo.get("datePublished")),
                publisher=_clean(pub_name, 200), duration_sec=iso_duration_sec(vo.get("duration", "")),
                caption_text=_clean(vo.get("transcript"), 200_000))

    for f in p.iframes:
        add(canonical_video_url(urljoin(page_url, f["src"])), title=_clean(f["title"]))

    for href, text in p.links:
        add(canonical_video_url(urljoin(page_url, href)), title=_clean(text))

    # A transcript block or caption track on the page belongs to the page's single video only;
    # with several videos we can't tell which one it describes, so we attach nothing.
    if len(items) == 1:
        only = next(iter(items.values()))
        if not only["caption_text"] and p.transcript_text:
            only["caption_text"] = _clean(" ".join(p.transcript_text), 200_000)
    return list(items.values())


def looks_blocked(status: Optional[int], html: str) -> Optional[str]:
    """Reason string if the page is a block, CAPTCHA or login wall. We never try to get past one."""
    if status in (401, 403, 407, 429, 451):
        return f"http {status}"
    low = html[:200_000].lower()
    for marker, reason in (("g-recaptcha", "captcha"), ("h-captcha", "captcha"), ("cf-challenge", "bot challenge"),
                           ("just a moment...", "bot challenge"), ("captcha", "captcha"),
                           ('type="password"', "login required"), ("sign in to continue", "login required")):
        if marker in low:
            return reason
    return None
