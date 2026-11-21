"""Fetch an OFFICIAL transcript for one video and write it in the Transcript format.

    # YouTube: looks the video up in <data dir>/videos.json and pulls its caption track
    python scripts/fetch_transcript.py <video_id>
    python scripts/fetch_transcript.py <video_id> --allow-auto     # accept auto-captions if no creator captions

    # Any publisher that offers a caption/transcript FILE (C-SPAN, council sites, ...): .vtt or .srt
    python scripts/fetch_transcript.py <video_id> --file captions.vtt --source official_captions

Writes data/transcripts/<video_id>.json (gitignored) unless --out is given, then prints the
transcript_path / transcript_source to put in videos.json.

Rules (AGENTS.md, docs/SOURCES.md):
- Official captions or publisher transcripts ONLY. There is no LLM option, on purpose:
  verifying quotes against an LLM's own transcript would be circular.
- Captions/transcript text only. Never downloads video or audio.
- Creator captions -> `official_captions`. Auto-captions -> `platform_auto_captions`, and only
  with --allow-auto, because every quote from them must be hand-checked.
- Check the source's terms before adding it.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import config  # noqa: E402
import storage  # noqa: E402
from models import Transcript, TranscriptSegment  # noqa: E402

FILE_SOURCES = ("official_captions", "publisher_transcript", "platform_auto_captions", "hand_transcribed")
LANGS = ["en", "en-US", "en-GB"]

# ---------- caption file parsing (WebVTT / SRT) ----------

_TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
_CUE_TIME = re.compile(rf"({_TS.pattern})\s*-->\s*({_TS.pattern})")
_TAG = re.compile(r"<[^>]+>")  # <c>, <i>, <00:00:01.234> word timings


def _secs(stamp: str) -> float:
    h, m, s, ms = _TS.fullmatch(stamp.strip()).groups()
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_captions(text: str) -> list[TranscriptSegment]:
    """Parse WebVTT or SRT into segments.

    Also undoes YouTube's "rolling" auto-caption format, where each cue repeats the previous
    cue's last line, and drops the ~10 ms transition cues it uses between them.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    segments: list[TranscriptSegment] = []
    prev_lines: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        idx = next((k for k, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue  # WEBVTT header, NOTE, STYLE, or SRT junk
        m = _CUE_TIME.search(lines[idx])
        if not m:
            continue
        start, end = _secs(m.group(1)), _secs(m.group(6))
        cue_lines = [html.unescape(_TAG.sub("", ln)).strip() for ln in lines[idx + 1:]]
        cue_lines = [ln for ln in cue_lines if ln]
        new = [ln for ln in cue_lines if ln not in prev_lines]  # rolling-caption repeats
        if cue_lines:
            prev_lines = cue_lines
        if not new or end - start < 0.05:
            continue
        seg_text = " ".join(new)
        if segments and segments[-1].text == seg_text:  # duplicated cue
            segments[-1] = TranscriptSegment(start=segments[-1].start, end=end, text=seg_text)
            continue
        segments.append(TranscriptSegment(start=start, end=end, text=seg_text))
    return segments


# ---------- YouTube ----------

def youtube_id(url: str) -> str | None:
    u = urlparse(url)
    host = (u.hostname or "").removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        return u.path.lstrip("/").split("/")[0] or None
    if host in ("youtube.com", "youtube-nocookie.com"):
        if u.path == "/watch":
            return parse_qs(u.query).get("v", [None])[0]
        parts = u.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in ("embed", "live", "shorts", "v"):
            return parts[1]
    return None


def fetch_youtube(yt_id: str, allow_auto: bool) -> tuple[list[TranscriptSegment], str]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        sys.exit("Needs youtube-transcript-api: pip install -r backend/requirements.txt")

    api = YouTubeTranscriptApi()
    listing = api.list(yt_id) if hasattr(api, "list") else YouTubeTranscriptApi.list_transcripts(yt_id)
    try:
        tr, source = listing.find_manually_created_transcript(LANGS), "official_captions"
    except Exception:
        if not allow_auto:
            sys.exit(f"{yt_id}: no creator-uploaded English captions. Re-run with --allow-auto to use "
                     "auto-captions (marked platform_auto_captions; hand-check every displayed quote).")
        tr, source = listing.find_generated_transcript(LANGS), "platform_auto_captions"
    segments = []
    for snip in tr.fetch():
        get = snip.get if isinstance(snip, dict) else lambda k: getattr(snip, k)
        text = html.unescape(get("text")).replace("\n", " ").strip()
        if text:
            start = float(get("start"))
            segments.append(TranscriptSegment(start=start, end=round(start + float(get("duration")), 3), text=text))
    return segments, source


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video_id", help="id from videos.json (also used as the output file name)")
    ap.add_argument("--url", help="video URL (default: the url in videos.json)")
    ap.add_argument("--file", type=Path, help="local .vtt/.srt caption file from the publisher")
    ap.add_argument("--source", choices=FILE_SOURCES, help="provenance of --file (required with --file)")
    ap.add_argument("--allow-auto", action="store_true", help="accept YouTube auto-captions")
    ap.add_argument("--out", type=Path, help="output path (default data/transcripts/<video_id>.json)")
    args = ap.parse_args(argv)

    if args.file:
        if not args.source:
            ap.error("--file needs --source (where did this caption file come from?)")
        segments, source = parse_captions(args.file.read_text(encoding="utf-8")), args.source
    else:
        url = args.url
        if not url:
            video = next((v for v in storage.load_videos() if v.id == args.video_id), None)
            if video is None:
                ap.error(f"{args.video_id} is not in {config.data_dir() / 'videos.json'}; pass --url")
            url = video.url
        yt = youtube_id(url)
        if not yt:
            ap.error(f"{url} is not a YouTube URL. Download the publisher's caption file and use "
                     "--file ... --source ... (see docs/SOURCES.md).")
        segments, source = fetch_youtube(yt, args.allow_auto)

    if not segments:
        sys.exit("No caption text found; nothing written.")
    transcript = Transcript(video_id=args.video_id, transcript_source=source, segments=segments)
    out = args.out or REPO_ROOT / "data" / "transcripts" / f"{args.video_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(transcript.model_dump(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    hours = (segments[-1].end - segments[0].start) / 3600
    rel = Path("..") / out.relative_to(REPO_ROOT / "data") if out.is_relative_to(REPO_ROOT / "data") else out
    print(f"Wrote {out} ({len(segments)} segments, ~{hours:.2f} h, {source}).")
    print(f'In videos.json set: "transcript_path": "{rel.as_posix()}" (relative to the data dir), '
          f'"transcript_source": "{source}"')
    if source == "platform_auto_captions":
        print("Auto-captions: a person must check every displayed quote against the video.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
