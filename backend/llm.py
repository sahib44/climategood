"""The ONLY place that talks to an LLM.

The LLM PROPOSES candidate moments. It never writes the quote shown: every proposal goes
through verify.verify_quote, which copies text and timestamps from the transcript.
Proposals are "modeled" until verified.
"""
from __future__ import annotations

import json
import os
from typing import Protocol, Sequence

from pydantic import BaseModel

from models import Topic, TranscriptSegment


class ProposedMoment(BaseModel):
    topic_id: str
    quote_text: str
    start_sec: float
    end_sec: float
    reason: str


class Proposals(BaseModel):
    moments: list[ProposedMoment]


class MomentProposer(Protocol):
    name: str

    def propose(self, video_id: str, segments: Sequence[TranscriptSegment], topics: Sequence[Topic]) -> list[ProposedMoment]:
        ...


class FakeProposer:
    """Test double: returns canned proposals per video_id (may include fabricated ones)."""
    name = "fake"

    def __init__(self, by_video: dict[str, list[ProposedMoment]]):
        self.by_video = by_video

    def propose(self, video_id, segments, topics):
        return list(self.by_video.get(video_id, []))


PROMPT = """You find moments in a transcript where the speaker addresses specific topics.
Rules:
- Copy quote_text EXACTLY from the transcript lines below. Do not paraphrase, fix grammar, or merge distant lines.
- start_sec/end_sec must be the timestamps of the lines you copied.
- Return every relevant moment, not just the best one. If none, return an empty list.
- Do not judge or summarize the speaker's position. "reason" is one short factual sentence on why the moment is about the topic.

Topics:
{topics}

Transcript (each line: [start_sec] text):
{transcript}
"""


class GeminiProposer:
    """Gemini via the google-genai SDK. Only public transcripts may be sent (docs/SOURCES.md)."""
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        from google import genai  # lazy: tests and keyword mode don't need the SDK
        from google.genai import types

        import config

        # Fail fast: a slow or overloaded model must never freeze a page. One attempt with a hard
        # timeout; on error the pipeline falls back to keyword mode for that video.
        self.client = genai.Client(
            api_key=api_key or os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(
                timeout=int(config.llm_timeout_sec() * 1000),  # milliseconds
                retry_options=types.HttpRetryOptions(attempts=config.LLM_ATTEMPTS),
            ),
        )
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def propose(self, video_id, segments, topics):
        topics_txt = "\n".join(f"- {t.id}: {t.label}. {t.description}" for t in topics)
        transcript_txt = "\n".join(f"[{s.start:.1f}] {s.text}" for s in segments)
        resp = self.client.models.generate_content(
            model=self.model,
            contents=PROMPT.format(topics=topics_txt, transcript=transcript_txt),
            config={"response_mime_type": "application/json", "response_schema": Proposals, "temperature": 0},
        )
        parsed = getattr(resp, "parsed", None)
        if isinstance(parsed, Proposals):
            return parsed.moments
        return Proposals(**json.loads(resp.text)).moments


def get_proposer() -> MomentProposer:
    return GeminiProposer()
