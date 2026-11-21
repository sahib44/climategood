"""STUB (Owner A, hours 1-3): fetch an OFFICIAL transcript for one video.

Usage (planned):
    python scripts/fetch_transcript.py <video_id>

Writes data/transcripts/<video_id>.json in the Transcript format (docs/DATA_FORMAT.md).

Rules:
- Official captions or publisher transcripts ONLY. Never generate a transcript with an LLM
  (verification against the LLM's own output would be circular).
- Do not download video or audio. Captions/transcript text only.
- Check the source's terms first (docs/SOURCES.md).

Candidate approaches:
- YouTube: creator-uploaded captions via the YouTube Data API captions endpoint
  (needs OAuth for download) or a captions library; mark auto-captions as
  `platform_auto_captions`.
- C-SPAN: published transcript text on the video page; verify current terms at c-span.org.
- Anything else: hand-transcribe the relevant passage (`hand_transcribed`) and have
  a second person check it against the video.
"""
import sys


def main(video_id: str) -> None:
    raise NotImplementedError(f"fetch_transcript not implemented yet (video {video_id}); see docstring")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
