"""Where items live on disk. One JSON file per item; the directory says its state.

data/ingest/proposed/<candidate_id>/<video_id>.json   status proposed or needs_fix
data/ingest/approved/<candidate_id>/<video_id>.json   approved by a person
data/ingest/rejected/<candidate_id>/<video_id>.json   rejected by a person, with reason
data/ingest/rejected/<candidate_id>/incomplete-*.json found but missing a required field
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Optional

from pydantic import ValidationError

from ingest.common import Paths, now_utc, read_json, write_json
from ingest.models import ProposedItem

_DIR_FOR = {"proposed": "proposed", "needs_fix": "proposed", "approved": "approved", "rejected": "rejected"}


def _dir(paths: Paths, status: str) -> Path:
    return getattr(paths, _DIR_FOR[status])


def item_file(paths: Paths, item: ProposedItem) -> Path:
    return _dir(paths, item.status) / item.candidate_id / f"{item.video_id}.json"


def save_item(paths: Paths, item: ProposedItem) -> Path:
    """Write the item where its status says, and remove any copy in another state's folder."""
    target = item_file(paths, item)
    for d in (paths.proposed, paths.approved, paths.rejected):
        other = d / item.candidate_id / f"{item.video_id}.json"
        if other != target and other.exists():
            other.unlink()
    write_json(target, item.model_dump(mode="json"))
    return target


def load_items(paths: Paths, candidate_id: Optional[str] = None,
               states: Iterable[str] = ("proposed", "approved", "rejected")) -> list[ProposedItem]:
    out = []
    for state in states:
        base = getattr(paths, state)
        dirs = [base / candidate_id] if candidate_id else (sorted(base.iterdir()) if base.exists() else [])
        for d in dirs:
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.json")):
                data = read_json(f)
                if data.get("stage") == "validation":  # incomplete record, not an item
                    continue
                out.append(ProposedItem.model_validate(data))
    return out


def find_item(paths: Paths, candidate_id: str, video_id: str) -> Optional[ProposedItem]:
    for item in load_items(paths, candidate_id):
        if item.video_id == video_id:
            return item
    return None


def save_incomplete(paths: Paths, candidate_id: str, raw: dict, reasons: list[str], **context) -> Path:
    """Record a found item we could not accept (e.g. no date or no publisher)."""
    digest = hashlib.sha1(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest()[:10]
    target = paths.rejected / candidate_id / f"incomplete-{digest}.json"
    write_json(target, {"stage": "validation", "candidate_id": candidate_id, "reasons": reasons,
                        "found": raw, "recorded_at": now_utc().isoformat(), **context})
    return target


def load_incomplete(paths: Paths, candidate_id: str) -> list[dict]:
    d = paths.rejected / candidate_id
    return [read_json(f) for f in sorted(d.glob("incomplete-*.json"))] if d.exists() else []


def validate_item(data: dict) -> tuple[Optional[ProposedItem], list[str]]:
    """Build a ProposedItem or return the list of reasons it is incomplete."""
    reasons = []
    for field_name, label in (("published_date", "date"), ("publisher", "publisher"),
                              ("title", "title"), ("video_url", "video URL")):
        v = data.get(field_name)
        if v is None or (isinstance(v, str) and not v.strip()):
            reasons.append(f"missing {label}")
    if reasons:
        return None, reasons
    try:
        return ProposedItem.model_validate(data), []
    except ValidationError as e:
        return None, [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]
