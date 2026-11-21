"""Real data is demo-ready: every approved video in data/real has a committed, valid transcript.

Transcripts are committed so the demo machine never has to re-fetch from YouTube, which
rate-limits caption requests. If a video is added to data/real/videos.json without its
transcript, this fails instead of the video silently dropping out of "videos searched".
"""
from pathlib import Path

import pytest

import config
import storage

REAL = config.REPO_ROOT / "data" / "real"
pytestmark = pytest.mark.skipif(not (REAL / "videos.json").exists(), reason="no real data yet")


def _videos():
    return storage.load_videos(REAL)


def test_every_real_video_has_a_committed_transcript():
    missing = [v.id for v in _videos() if not (REAL / v.transcript_path).exists()]
    assert missing == [], f"no transcript file for: {missing}"


def test_real_transcripts_are_valid_and_match_their_source():
    for v in _videos():
        t = storage.load_transcript(v, REAL)
        assert t is not None and t.segments, v.id
        assert t.transcript_source == v.transcript_source, v.id
        assert t.transcript_source in {"official_captions", "publisher_transcript",
                                       "platform_auto_captions", "hand_transcribed"}, v.id


def test_no_gemini_cache_or_stray_files_are_committed():
    folder = REAL / ".." / "transcripts"
    expected = {Path(v.transcript_path).name for v in _videos()}
    tracked = {p.name for p in folder.resolve().glob("*.json") if not p.name.endswith(".proposals.json")}
    assert tracked - expected == set(), f"transcripts not referenced by data/real: {tracked - expected}"


def _caches():
    folder = (REAL / ".." / "transcripts").resolve()
    return sorted(p for p in folder.glob("*.proposals.json") if not p.name.startswith("fv-"))


def test_committed_gemini_caches_hold_only_verified_quotes():
    """Rule: never store invented quotes for real people. A cache is Gemini output, so every
    proposal in a committed cache must match its transcript word for word."""
    import json

    from models import TranscriptSegment
    from verify import verify_quote

    bad = []
    for p in _caches():
        d = json.loads(p.read_text(encoding="utf-8"))
        t = json.loads((p.parent / p.name.replace(".proposals.json", ".json")).read_text(encoding="utf-8"))
        segs = [TranscriptSegment(**s) for s in t["segments"]]
        bad += [(p.name, m["topic_id"]) for m in d["moments"]
                if not verify_quote(m["quote_text"], segs, proposed_start=m["start_sec"]).verified]
    assert bad == [], f"unverified (possibly invented) quotes in committed caches: {bad}"


def test_committed_gemini_caches_are_hits_for_the_default_model():
    """If topics, the prompt or the default model change, these caches go stale and the demo
    would call Gemini again. Regenerate them (and re-run the test above) when that happens."""
    import json
    import os

    from models import TranscriptSegment
    from proposal_cache import cache_key

    class Default:
        name = "gemini"
        model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    topics = storage.load_topics()
    stale = []
    for p in _caches():
        d = json.loads(p.read_text(encoding="utf-8"))
        t = json.loads((p.parent / p.name.replace(".proposals.json", ".json")).read_text(encoding="utf-8"))
        segs = [TranscriptSegment(**s) for s in t["segments"]]
        if cache_key(Default(), segs, topics) != d["key"]:
            stale.append(p.name)
    assert stale == [], f"stale Gemini caches: {stale}"
