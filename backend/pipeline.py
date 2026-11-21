"""propose -> verify -> clip cards. One code path for every candidate (rule 1).

`party` is never read in this module.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

import config
import storage
from keyword_match import KeywordProposer
from llm import MomentProposer
from models import (
    Candidate, ClipCard, Coverage, EmptyState, SourceInfo, Statement, Topic, TopicResult, Video,
)
from verify import verify_quote

log = logging.getLogger("firsthand.pipeline")

# LLM drop rate (TASKS.md hour 3-5): how many LLM proposals passed verification. Keyed by
# distinct proposal so a page refresh served from the cache doesn't count twice. In memory only:
# it covers proposals seen since the server started. Nothing about users is recorded.
_llm_outcomes: dict[tuple[str, str, float, str], bool] = {}
_stats_lock = threading.Lock()


def _record_llm_outcome(video_id: str, topic_id: str, start_sec: float, quote_text: str, verified: bool) -> None:
    with _stats_lock:
        _llm_outcomes[(video_id, topic_id, round(float(start_sec), 1), quote_text)] = verified


def llm_proposal_stats() -> dict:
    """Proposed vs verified LLM moments. `modeled`: it describes the model's behaviour, not a candidate."""
    with _stats_lock:
        proposed = len(_llm_outcomes)
        verified = sum(_llm_outcomes.values())
    return {
        "proposed": proposed,
        "verified": verified,
        "dropped": proposed - verified,
        "drop_rate": round((proposed - verified) / proposed, 3) if proposed else None,
        "label": "modeled",
        "note": "Distinct LLM proposals since the server started. Dropped proposals did not match the "
                "transcript and were never shown.",
    }


def reset_llm_proposal_stats() -> None:
    with _stats_lock:
        _llm_outcomes.clear()


def coverage_for(candidate_id: str, videos: list[Video], data_dir: Optional[Path] = None) -> Coverage:
    """Counts only videos whose transcript we actually have (= actually searched)."""
    searched = [v for v in videos if v.candidate_id == candidate_id and storage.load_transcript(v, data_dir)]
    return Coverage(videos_searched=len(searched), hours_searched=_hours(sum(v.duration_sec for v in searched)))


def _hours(seconds: int) -> float:
    """Hours searched. One decimal, but never round real coverage down to 0.0 (a 2-minute clip is 0.03 h)."""
    h = max(seconds, 0) / 3600
    return round(h, 1) if h == 0 or round(h, 1) > 0 else round(h, 2)


def unevenness_warning(names_cov: list[tuple[str, Coverage]]) -> Optional[str]:
    if len(names_cov) < 2:
        return None
    lo = min(names_cov, key=lambda x: x[1].hours_searched)
    hi = max(names_cov, key=lambda x: x[1].hours_searched)
    vids = [c.videos_searched for _, c in names_cov]
    hours_uneven = hi[1].hours_searched > config.UNEVENNESS_RATIO * max(lo[1].hours_searched, 0.0001)
    videos_uneven = max(vids) > config.UNEVENNESS_RATIO * max(min(vids), 0.0001)
    if not (hours_uneven or videos_uneven):
        return None
    def vids_txt(c: Coverage) -> str:
        return f"{c.videos_searched} video{'s' if c.videos_searched != 1 else ''} ({c.hours_searched} h)"

    return (
        f"Coverage is uneven: we searched {vids_txt(hi[1])} for {hi[0]} "
        f"but {vids_txt(lo[1])} for {lo[0]}. "
        "Fewer results can reflect less coverage, not a different position."
    )


def empty_state(topic: Topic, coverage: Coverage) -> EmptyState:
    n = coverage.videos_searched
    if n == 0:  # "no statement found in 0 videos" would read like evidence of silence (rule 7)
        return EmptyState(
            message="We have not searched any videos for this candidate yet, so we cannot show statements on this topic.",
            suggested_question=topic.suggested_question,
        )
    return EmptyState(
        message=f"No statement found in the {n} video{'s' if n != 1 else ''} we searched.",
        suggested_question=topic.suggested_question,
    )


def build_topic_result(
    candidate: Candidate,
    topic: Topic,
    videos: list[Video],
    proposer: Optional[MomentProposer] = None,
    all_candidates: Optional[list[Candidate]] = None,
    data_dir: Optional[Path] = None,
) -> TopicResult:
    keyword = KeywordProposer()
    proposer = proposer or keyword
    mode = "keyword" if proposer.name == "keyword" else "llm"
    cards: list[ClipCard] = []
    cand_videos = [v for v in videos if v.candidate_id == candidate.id]

    for video in cand_videos:
        transcript = storage.load_transcript(video, data_dir)
        if transcript is None:
            continue
        segs = transcript.segments
        try:
            proposals = proposer.propose(video.id, segs, [topic])
            found_by = "keyword" if proposer.name == "keyword" else "llm"
        except Exception as e:  # quota, network, bad JSON → no-LLM fallback
            log.warning("proposer %s failed on %s (%s); falling back to keyword", proposer.name, video.id, e)
            proposals, found_by = keyword.propose(video.id, segs, [topic]), "keyword"

        seen: set[tuple[float, str]] = set()
        for p in proposals:
            if p.topic_id != topic.id:
                continue
            r = verify_quote(p.quote_text, segs, proposed_start=p.start_sec)
            if found_by == "llm":
                _record_llm_outcome(video.id, p.topic_id, p.start_sec, p.quote_text, r.verified)
            if not r.verified:
                log.info("dropped unverified proposal on %s: %s", video.id, r.reason)
                continue
            key = (r.start_sec, r.quote_text)
            if key in seen:
                continue
            seen.add(key)
            stmt = Statement(
                id=f"{video.id}:{topic.id}:{int(r.start_sec * 1000)}",
                candidate_id=candidate.id, topic_id=topic.id, video_id=video.id,
                quote_text=r.quote_text, video_url=video.url,
                start_sec=r.start_sec, end_sec=r.end_sec,
                context_before=r.context_before, context_after=r.context_after,
                verified=True, verification_method=r.method, label="measured",
                found_by=found_by, timestamp_corrected=r.timestamp_corrected,
            )
            cards.append(ClipCard(statement=stmt, source=SourceInfo(
                title=video.title, publisher=video.publisher, published_date=video.published_date,
                venue=video.venue, url=video.url, transcript_source=video.transcript_source,
            )))

    # ALL matches, chronological. No "best" selection, no truncation.
    cards.sort(key=lambda c: (c.source.published_date, c.statement.start_sec))
    cov = coverage_for(candidate.id, videos, data_dir)
    others = all_candidates or [candidate]
    warning = unevenness_warning([(c.name, coverage_for(c.id, videos, data_dir)) for c in others])
    return TopicResult(
        candidate=candidate, topic=topic, coverage=cov, mode=mode, cards=cards,
        empty_state=None if cards else empty_state(topic, cov),
        unevenness_warning=warning,
    )
