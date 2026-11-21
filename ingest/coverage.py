"""data/ingest/coverage.json: per-candidate and per-source-type counts, computed from disk.

Counts are recomputed from the item files and the log every time, never kept as running totals,
so they always match the items. Every configured candidate appears, including ones with zero
items, so the UI can show uneven coverage honestly.

"searched" means approved by a person AND an official transcript exists; only those videos are
searched for statements. Approved videos without a transcript are counted as "unavailable".
"""
from __future__ import annotations

from collections import defaultdict

from ingest.common import Paths, now_utc, read_log, write_json
from ingest.store import load_incomplete, load_items

LOG_COUNTED = ("filtered_out", "out_of_period", "over_cap", "not_allowlisted")
STATE_KEYS = ("proposed", "needs_fix", "approved_searched", "approved_unavailable", "rejected_by_reviewer",
              "incomplete", *LOG_COUNTED)


def _empty() -> dict:
    return {k: 0 for k in STATE_KEYS}


def compute_coverage(paths: Paths, candidates: list[dict]) -> dict:
    ids = [c["id"] for c in candidates if c.get("id")]
    per = {cid: {"by_source_type": defaultdict(_empty), "hours_searched": 0.0, "listings_sent_to_manual": 0}
           for cid in ids}

    for item in load_items(paths):
        if item.candidate_id not in per:
            continue
        b = per[item.candidate_id]["by_source_type"][item.source_type]
        if item.status == "approved":
            if item.transcript_status == "available":
                b["approved_searched"] += 1
                per[item.candidate_id]["hours_searched"] += (item.duration_sec or 0) / 3600
            else:
                b["approved_unavailable"] += 1
        elif item.status == "rejected":
            b["rejected_by_reviewer"] += 1
        else:
            b[item.status] += 1

    for cid in ids:
        for rec in load_incomplete(paths, cid):
            per[cid]["by_source_type"][rec.get("source_type", "unknown")]["incomplete"] += 1

    seen = set()
    for ev in read_log(paths):
        cid, kind = ev.get("candidate_id"), ev.get("event")
        if cid not in per:
            continue
        key = (kind, cid, ev.get("url"))
        if key in seen:  # a --force re-run must not double count
            continue
        seen.add(key)
        if kind in LOG_COUNTED:
            per[cid]["by_source_type"][ev.get("source_type", "unknown")][kind] += 1
        elif kind == "manual_queue":
            per[cid]["listings_sent_to_manual"] += 1

    out = {}
    for cid, v in per.items():
        by_type = {k: dict(b) for k, b in sorted(v["by_source_type"].items())}
        out[cid] = {
            "videos_searched": sum(b["approved_searched"] for b in by_type.values()),
            "hours_searched": round(v["hours_searched"], 2),
            "videos_unavailable_no_transcript": sum(b["approved_unavailable"] for b in by_type.values()),
            "listings_sent_to_manual": v["listings_sent_to_manual"],
            "by_source_type": by_type,
            "label": "measured",
        }
    return {"generated_at": now_utc().isoformat(),
            "note": "Counts from data/ingest files and log. 'searched' = approved by a person with an official transcript.",
            "candidates": out}


def write_coverage(paths: Paths, candidates: list[dict]) -> dict:
    cov = compute_coverage(paths, candidates)
    write_json(paths.coverage, cov)
    return cov
