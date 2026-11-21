"""Pydantic models for ingest's own files (data/ingest/).

These carry extra provenance fields the backend schema does not have yet (fetched_at,
listing_page_url, browserbase_session_id, review record). They stay in data/ingest/ until the
backend schema grows them; see docs/DATA_REQUESTS.md. What reaches data/real/ is validated
against backend/models.py `Video` and `Candidate` exactly.

NEUTRALITY: like backend/models.py, no field here may be a score, rating, rank, grade, stance
or verdict.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

ItemStatus = Literal["proposed", "needs_fix", "approved", "rejected"]
Decision = Literal["approve", "reject", "needs_fix"]
# Backend TranscriptSource minus `fictional`; "unknown" until a person or fetch_transcript.py sets it.
IngestTranscriptSource = Literal[
    "official_captions", "publisher_transcript", "platform_auto_captions", "hand_transcribed", "unknown"
]
TranscriptStatus = Literal["unknown", "available", "no_transcript"]


class ReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str = Field(min_length=1)
    reviewed_at: datetime
    decision: Decision
    reason: str = ""
    # "watched": a person opened the video. "batch_not_watched": approved by rule in a batch; the
    # displayed clips from it must still be watched by a person before they are relied on.
    method: Literal["watched", "batch_not_watched"] = "watched"


class ProposedItem(BaseModel):
    """One video found by collect.py or added through the manual CSV. Never shown to voters
    until a person approves it and an official transcript exists."""

    model_config = ConfigDict(extra="forbid")

    video_id: str
    candidate_id: str
    video_url: str
    title: str = Field(min_length=1, max_length=300)
    publisher: str = Field(min_length=1, max_length=200)
    published_date: date
    venue: str = ""  # often not on the listing page; the reviewer fills it in
    duration_sec: Optional[int] = Field(default=None, ge=1)
    listing_page_url: str
    source_type: str
    origin: Literal["browserbase", "manual"]
    fetched_at: datetime
    browserbase_session_id: Optional[str] = None
    screenshot_path: Optional[str] = None
    # Text the official page itself published (e.g. a transcript block). Kept for the reviewer
    # only; the verifier always uses the timed transcript from scripts/fetch_transcript.py.
    caption_text: Optional[str] = Field(default=None, max_length=200_000)
    transcript_source: IngestTranscriptSource = "unknown"
    transcript_status: TranscriptStatus = "unknown"
    lower_confidence: bool = False  # true for platform auto-captions
    relevance_keyword: Optional[str] = None  # which format keyword kept it, for the log
    added_by: Optional[str] = None  # manual rows only
    notes: str = ""
    status: ItemStatus = "proposed"
    review: Optional[ReviewRecord] = None

    @field_validator("title", "publisher", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class IncompleteItem(Exception):
    """Raised when a found item lacks a field we require (date, publisher, title, url)."""
