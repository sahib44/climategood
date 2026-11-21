"""Pydantic schemas. Documented in docs/DATA_FORMAT.md.

NEUTRALITY: no model here may contain a score, rating, rank, grade, stance or verdict
field. tests/test_no_scores.py fails if one is added.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Label = Literal["measured", "modeled", "assumed"]
TranscriptSource = Literal[
    "official_captions",
    "publisher_transcript",
    "platform_auto_captions",
    "hand_transcribed",
    "fictional",
]


# ---------- stored data ----------

class Candidate(BaseModel):
    id: str
    name: str
    office: str
    party: str  # display only; the pipeline never reads it
    jurisdiction: str
    election_date: date
    sources: list[str] = Field(default_factory=list, description="Official channels/pages we curate from")
    fictional: bool = False
    # Display only, optional (the pipeline never reads them):
    current_position: Optional[str] = None  # the office or job they hold now, e.g. "State Senator, District 8"
    photo_url: Optional[str] = None  # a photo we are licensed to show; see docs/SOURCES.md
    photo_credit: Optional[str] = None  # required with photo_url: who made it and its license


class Video(BaseModel):
    id: str
    candidate_id: str
    title: str
    publisher: str
    url: str  # official publisher URL; we link/embed, never re-host
    published_date: date
    venue: str
    duration_sec: int
    transcript_path: str  # relative to the data dir
    transcript_source: TranscriptSource
    fictional: bool = False


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class Transcript(BaseModel):
    video_id: str
    transcript_source: TranscriptSource
    segments: list[TranscriptSegment]


class Topic(BaseModel):
    id: str
    label: str
    description: str
    example_phrases: list[str]
    suggested_question: str  # neutral question for the empty state


class Statement(BaseModel):
    """A verified clip card. Only verified statements are ever returned by the API."""
    id: str
    candidate_id: str
    topic_id: str
    video_id: str
    quote_text: str  # copied from the transcript, never from an LLM
    video_url: str
    start_sec: float
    end_sec: float
    context_before: str
    context_after: str
    verified: bool
    verification_method: Literal["exact_normalized", "near_exact", "none"]
    label: Label  # the quote itself: "measured" once verified
    topic_match_label: Label = "modeled"  # that this quote is ABOUT the topic is a model judgement
    found_by: Literal["llm", "keyword"]
    timestamp_corrected: bool = False


# ---------- API responses ----------

class Coverage(BaseModel):
    videos_searched: int
    hours_searched: float
    label: Label = "measured"


class SourceInfo(BaseModel):
    title: str
    publisher: str
    published_date: date
    venue: str
    url: str
    transcript_source: TranscriptSource


class ClipCard(BaseModel):
    statement: Statement
    source: SourceInfo


class EmptyState(BaseModel):
    message: str
    suggested_question: str


class CandidateSummary(BaseModel):
    candidate: Candidate
    coverage: Coverage


class CandidatesResponse(BaseModel):
    candidates: list[CandidateSummary]
    unevenness_warning: Optional[str] = None


class TopicResult(BaseModel):
    candidate: Candidate
    topic: Topic
    coverage: Coverage
    mode: Literal["keyword", "llm"]
    cards: list[ClipCard]  # ALL matches, chronological
    empty_state: Optional[EmptyState] = None
    unevenness_warning: Optional[str] = None


class VerifyRequest(BaseModel):
    video_id: str
    quote_text: str
    start_sec: Optional[float] = None


class VerifyResponse(BaseModel):
    verified: bool
    method: str
    reason: str
    transcript_text: Optional[str] = None  # what the transcript actually says, if located
    start_sec: Optional[float] = None
    similarity: float


_ID = r"[A-Za-z0-9._-]+"


class ProblemReport(BaseModel):
    """A "report a problem" submission. Only these fields are accepted or stored (rule 10)."""
    model_config = ConfigDict(extra="forbid")  # an unexpected field (e.g. an email) is rejected, never stored

    problem_type: Literal[
        "wrong_quote", "wrong_timestamp", "misattributed", "edited_clip", "missing_statement", "other"
    ]
    statement_id: Optional[str] = Field(default=None, max_length=300, pattern=rf"^{_ID}:{_ID}:\d+$")
    candidate_id: Optional[str] = Field(default=None, max_length=120, pattern=rf"^{_ID}$")
    details: str = Field(default="", max_length=2000)

    @field_validator("details")
    @classmethod
    def _strip_details(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def _needs_a_subject(self):
        if not self.statement_id and not self.candidate_id:
            raise ValueError("say which statement or candidate the report is about (statement_id or candidate_id)")
        return self
