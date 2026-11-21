"""No-LLM mode: phrase matching against each topic's example_phrases.

Produces the same ProposedMoment shape as the LLM, so the same verifier and card
format apply. Works offline and with no quota: the demo fallback.
"""
from __future__ import annotations

from typing import Sequence

from llm import ProposedMoment
from models import Topic, TranscriptSegment
from verify import _TURN, clean_caption_text, normalize_text


def _contains(hay: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return n > 0 and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


class KeywordProposer:
    name = "keyword"

    def propose(self, video_id: str, segments: Sequence[TranscriptSegment], topics: Sequence[Topic]) -> list[ProposedMoment]:
        out: list[ProposedMoment] = []
        for topic in topics:
            phrases = [normalize_text(p) for p in topic.example_phrases]
            for seg in segments:
                # Propose each speaker turn separately so a quote never mixes two speakers.
                for piece in clean_caption_text(seg.text).split(_TURN):
                    seg_norm = normalize_text(piece)
                    hit = next((p for p in phrases if _contains(seg_norm, p)), None)
                    if hit:
                        out.append(ProposedMoment(
                            topic_id=topic.id, quote_text=piece.strip(), start_sec=seg.start, end_sec=seg.end,
                            reason=f"contains phrase '{' '.join(hit)}'",
                        ))
        return out
