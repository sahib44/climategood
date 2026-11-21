"""Domain allowlist, enforced in code (config/sources.json + a hard social-media block).

Two separate permissions per domain:
- automated_fetch: Browserbase may load pages there (robots.txt and terms allow it).
- link_ok: we may store a link to a video there and play it in that publisher's own player.
A domain counts only if both robots_checked_on and terms_checked_on are filled in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlsplit

from ingest.common import read_json

# Refused whatever config/sources.json says (AGENTS.md: official sources only, no social reposts).
BLOCKED_DOMAINS = (
    "facebook.com", "fb.watch", "instagram.com", "twitter.com", "x.com", "tiktok.com", "threads.net",
    "reddit.com", "linkedin.com", "snapchat.com", "rumble.com", "truthsocial.com", "bsky.app",
)

Permission = Literal["automated_fetch", "link_ok"]
_ARCHIVE_RE = re.compile(r"^/web/(\d{4,14})[a-z_]*/(.+)$")


class NotAllowed(Exception):
    pass


@dataclass(frozen=True)
class SourceRule:
    domain: str
    aliases: tuple[str, ...]
    source_type: str
    automated_fetch: bool
    link_ok: bool
    checked: bool  # robots AND terms both dated
    attribution: str


def host_of(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise NotAllowed(f"not an http(s) URL: {url!r}")
    if parts.username or parts.password:
        raise NotAllowed(f"URL with credentials refused: {url!r}")
    return parts.hostname.lower().rstrip(".").removeprefix("www.")


def _matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def unwrap_archive(url: str) -> tuple[str, Optional[str]]:
    """web.archive.org/web/<timestamp>/<original> -> (<original>, <timestamp>). Others unchanged."""
    parts = urlsplit(url)
    if (parts.hostname or "").lower().removeprefix("www.") == "web.archive.org":
        m = _ARCHIVE_RE.match(parts.path + (("?" + parts.query) if parts.query else ""))
        if m:
            original = m.group(2)
            if original.startswith("//"):
                original = "https:" + original
            elif not re.match(r"^https?://", original):
                original = "https://" + original
            return original, m.group(1)
    return url, None


class Allowlist:
    def __init__(self, rules: list[SourceRule]):
        self.rules = rules

    @classmethod
    def load(cls, path: Path) -> "Allowlist":
        cfg = read_json(path, {"sources": []})
        rules = []
        for s in cfg.get("sources", []):
            rules.append(
                SourceRule(
                    domain=s["domain"].lower().removeprefix("www."),
                    aliases=tuple(a.lower().removeprefix("www.") for a in s.get("aliases", [])),
                    source_type=s["source_type"],
                    automated_fetch=bool(s.get("automated_fetch")),
                    link_ok=bool(s.get("link_ok")),
                    checked=bool(s.get("robots_checked_on")) and bool(s.get("terms_checked_on")),
                    attribution=s.get("attribution", ""),
                )
            )
        return cls(rules)

    def rule_for(self, url: str) -> SourceRule:
        host = host_of(url)
        if any(_matches(host, d) for d in BLOCKED_DOMAINS):
            raise NotAllowed(f"social media is never a source: {host}")
        for r in self.rules:
            if any(_matches(host, d) for d in (r.domain, *r.aliases)):
                if not r.checked:
                    raise NotAllowed(f"{host}: robots.txt and terms not both checked yet (docs/SOURCES.md)")
                return r
        raise NotAllowed(f"{host} is not on the allowlist (config/sources.json)")

    def require(self, url: str, permission: Permission) -> SourceRule:
        rule = self.rule_for(url)
        if not getattr(rule, permission):
            raise NotAllowed(f"{host_of(url)} does not allow {permission} (config/sources.json)")
        # An archived page must itself be an archived copy of an allowed, non-social site.
        original, _ = unwrap_archive(url)
        if original != url:
            host = host_of(original)
            if any(_matches(host, d) for d in BLOCKED_DOMAINS):
                raise NotAllowed(f"archived social media is never a source: {host}")
        return rule

    def allows(self, url: str, permission: Permission) -> bool:
        try:
            self.require(url, permission)
            return True
        except NotAllowed:
            return False
