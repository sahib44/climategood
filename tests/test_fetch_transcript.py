"""Caption-file parsing for scripts/fetch_transcript.py. All caption text is FICTIONAL."""
import importlib.util
import json

import pytest

import config

_spec = importlib.util.spec_from_file_location("fetch_transcript", config.REPO_ROOT / "scripts" / "fetch_transcript.py")
ft = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ft)

VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:04.500
<v Moderator>&gt;&gt; MODERATOR: First question.

00:00:04.500 --> 00:00:09.250
We need water &amp; energy
disclosure for every facility.
"""

SRT = """1
00:01:02,000 --> 00:01:05,500
Ratepayers should not cover

2
00:01:05,500 --> 00:01:08,000
<i>the cost of new lines.</i>
"""

# YouTube auto-caption VTT: each cue repeats the previous line; 10 ms transition cues.
ROLLING = """WEBVTT

00:00:00.000 --> 00:00:02.000
every<00:00:00.500><c> town</c><00:00:01.000><c> should</c>

00:00:02.000 --> 00:00:02.010
every town should

00:00:02.010 --> 00:00:04.000
every town should
get<00:00:02.500><c> a</c><00:00:03.000><c> vote</c>
"""


def test_parses_vtt_with_entities_and_tags():
    segs = ft.parse_captions(VTT)
    assert [(s.start, s.end) for s in segs] == [(1.0, 4.5), (4.5, 9.25)]
    assert segs[0].text == ">> MODERATOR: First question."
    assert segs[1].text == "We need water & energy disclosure for every facility."


def test_parses_srt():
    segs = ft.parse_captions(SRT)
    assert segs[0].start == 62.0 and segs[1].end == 68.0
    assert segs[1].text == "the cost of new lines."


def test_undoes_rolling_auto_captions():
    segs = ft.parse_captions(ROLLING)
    assert [s.text for s in segs] == ["every town should", "get a vote"]


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=abc123XYZ_-&t=30", "abc123XYZ_-"),
    ("https://youtu.be/abc123XYZ_-?t=5", "abc123XYZ_-"),
    ("https://www.youtube.com/embed/abc123XYZ_-", "abc123XYZ_-"),
    ("https://www.c-span.org/video/?123456-1/debate", None),
])
def test_youtube_id(url, expected):
    assert ft.youtube_id(url) == expected


def test_file_mode_writes_transcript(tmp_path):
    src = tmp_path / "c.srt"
    src.write_text(SRT)
    out = tmp_path / "out.json"
    assert ft.main(["vid-1", "--file", str(src), "--source", "official_captions", "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert data["video_id"] == "vid-1" and data["transcript_source"] == "official_captions"
    assert len(data["segments"]) == 2


def test_file_mode_requires_a_source_and_has_no_llm_option(tmp_path):
    src = tmp_path / "c.srt"
    src.write_text(SRT)
    with pytest.raises(SystemExit):
        ft.main(["vid-1", "--file", str(src)])
    with pytest.raises(SystemExit):
        ft.main(["vid-1", "--file", str(src), "--source", "llm_generated"])


def test_parsed_captions_verify_end_to_end():
    from verify import verify_quote
    segs = ft.parse_captions(VTT)
    r = verify_quote("we need water & energy disclosure for every facility", segs)
    assert r.verified and r.method == "exact_normalized"
    assert r.quote_text == "We need water & energy disclosure for every facility."  # "&" kept
    assert "MODERATOR" not in r.quote_text
    r = verify_quote("we need water and energy disclosure for every facility", segs)
    assert r.method == "near_exact" and "&" in r.quote_text  # shown text is the transcript's
