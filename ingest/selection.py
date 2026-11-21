"""Candidate-neutral rules applied identically to every candidate.

- Relevance: a keyword FORMAT filter on the title (debate, forum, town hall, ...). It never looks
  at what was said and never filters by topic or by whether a statement helps or hurts anyone.
- Scope: published_date inside the candidate's campaign_period, if one is given.
- Cap: newest first, ties broken by URL, keep the first N. N comes from ingest/settings.json and
  there is no per-candidate override.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from ingest.common import parse_date


def cap_for(candidate: dict, settings: dict) -> int:
    """The same cap for everyone. Any 'cap' key on a candidate is ignored on purpose."""
    return int(settings["per_candidate_cap"])


def relevance_match(title: str, settings: dict) -> Optional[str]:
    """Return the format keyword that keeps this item, or None. Disabled filter keeps everything."""
    rel = settings.get("relevance", {})
    if not rel.get("enabled", False):
        return "(filter disabled)"
    low = f" {title.lower()} "
    for kw in rel.get("keywords", []):
        if kw.lower() in low:
            return kw
    return None


def in_campaign_period(published: date, candidate: dict) -> bool:
    period = candidate.get("campaign_period") or {}
    start, end = parse_date(period.get("start")), parse_date(period.get("end"))
    if start and published < start:
        return False
    if end and published > end:
        return False
    return True


def apply_cap(items: list, cap: int) -> tuple[list, list]:
    """Split into (kept, over_cap). Items need .published_date and .video_url (or dict keys)."""

    def key(it):
        get = it.get if isinstance(it, dict) else lambda k: getattr(it, k)
        return (-parse_date(get("published_date")).toordinal(), get("video_url"))

    ordered = sorted(items, key=key)
    return ordered[:cap], ordered[cap:]
