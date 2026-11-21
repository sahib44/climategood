"""FastAPI app. Run: uvicorn main:app --reload --app-dir backend

Privacy (rule 10): no accounts, no cookies, no analytics, no logging of searches.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config
import pipeline
import storage
from models import (
    CandidatesResponse, CandidateSummary, ProblemReport, Topic, TopicResult, VerifyRequest, VerifyResponse,
)
from verify import verify_quote

app = FastAPI(title="Firsthand", description="Verbatim candidate statements. No scores.")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
)


def _proposer():
    if config.mode() == "llm":
        try:
            from llm import get_proposer
            from proposal_cache import CachingProposer
            # One Gemini call per video for all topics, cached on disk (backend/proposal_cache.py).
            return CachingProposer(get_proposer(), storage.load_topics())
        except Exception:  # missing key/SDK → no-LLM mode
            return None
    return None


@app.get("/health")
def health():
    return {"status": "ok", "mode": config.mode(), "report_email": config.REPORT_EMAIL}


@app.get("/topics", response_model=list[Topic])
def topics():
    return storage.load_topics()


@app.get("/candidates", response_model=CandidatesResponse)
def candidates():
    cands, videos = storage.load_candidates(), storage.load_videos()
    summaries = [CandidateSummary(candidate=c, coverage=pipeline.coverage_for(c.id, videos)) for c in cands]
    return CandidatesResponse(
        candidates=summaries,
        unevenness_warning=pipeline.unevenness_warning([(s.candidate.name, s.coverage) for s in summaries]),
    )


@app.get("/candidates/{candidate_id}/topics/{topic_id}", response_model=TopicResult)
def candidate_topic(candidate_id: str, topic_id: str):
    cands = storage.load_candidates()
    cand = next((c for c in cands if c.id == candidate_id), None)
    topic = next((t for t in storage.load_topics() if t.id == topic_id), None)
    if not cand or not topic:
        raise HTTPException(404, "unknown candidate or topic")
    return pipeline.build_topic_result(cand, topic, storage.load_videos(), proposer=_proposer(), all_candidates=cands)


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest):
    """Strict check for the demo: exact (normalized) matches only."""
    video = next((v for v in storage.load_videos() if v.id == req.video_id), None)
    transcript = storage.load_transcript(video) if video else None
    if transcript is None:
        raise HTTPException(404, "unknown video or transcript missing")
    r = verify_quote(req.quote_text, transcript.segments, proposed_start=req.start_sec, allow_near=False)
    return VerifyResponse(
        verified=r.verified, method=r.method, reason=r.reason,
        transcript_text=r.quote_text, start_sec=r.start_sec, similarity=r.similarity,
    )


@app.post("/reports")
def report(rep: ProblemReport):
    """Append to a local JSONL log. No IP, no user identity stored."""
    config.REPORTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **rep.model_dump()}
    with config.REPORTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return {"status": "received", "next": "A human will check the original source. See docs/TRUST_AND_SAFETY.md."}
