"""Proposal cache: one model call per video for all topics, and verification still applies."""
import json

import pipeline
import storage
from llm import FakeProposer, ProposedMoment
from proposal_cache import CachingProposer, cache_path
from models import TranscriptSegment

VIDEO = "fv-vale-townhall"
REAL = "we should only build them if they bring new clean power with them"
FAKE = "I will personally ban every data center in this state"


class CountingProposer(FakeProposer):
    name = "gemini"
    model = "test-model"

    def __init__(self, by_video):
        super().__init__(by_video)
        self.calls = []

    def propose(self, video_id, segments, topics):
        self.calls.append((video_id, sorted(t.id for t in topics)))
        return super().propose(video_id, segments, topics)


def _moments():
    return [
        ProposedMoment(topic_id="clean_power_requirement", start_sec=131.0, end_sec=137.5, reason="real", quote_text=REAL),
        ProposedMoment(topic_id="clean_power_requirement", start_sec=140.0, end_sec=145.0, reason="fake", quote_text=FAKE),
        ProposedMoment(topic_id="moratorium", start_sec=10.0, end_sec=12.0, reason="other topic", quote_text="x y z w"),
    ]


def _segs():
    v = next(v for v in storage.load_videos() if v.id == VIDEO)
    return storage.load_transcript(v).segments


def test_one_call_per_video_covers_every_topic(tmp_path, topics):
    inner = CountingProposer({VIDEO: _moments()})
    cp = CachingProposer(inner, list(topics.values()), cache_dir=tmp_path)
    segs = _segs()
    for t in topics.values():
        cp.propose(VIDEO, segs, [t])
    assert len(inner.calls) == 1
    assert inner.calls[0][1] == sorted(topics)  # asked for ALL topics at once
    assert cache_path(tmp_path, VIDEO).exists()


def test_results_are_filtered_to_the_requested_topic(tmp_path, topics):
    cp = CachingProposer(CountingProposer({VIDEO: _moments()}), list(topics.values()), cache_dir=tmp_path)
    got = cp.propose(VIDEO, _segs(), [topics["moratorium"]])
    assert [m.topic_id for m in got] == ["moratorium"]


def test_new_instance_reads_from_disk_without_calling(tmp_path, topics):
    segs = _segs()
    CachingProposer(CountingProposer({VIDEO: _moments()}), list(topics.values()), cache_dir=tmp_path).propose(
        VIDEO, segs, [topics["moratorium"]])
    inner2 = CountingProposer({VIDEO: []})
    got = CachingProposer(inner2, list(topics.values()), cache_dir=tmp_path).propose(
        VIDEO, segs, [topics["clean_power_requirement"]])
    assert inner2.calls == [] and len(got) == 2


def test_changed_transcript_invalidates_cache(tmp_path, topics):
    segs = _segs()
    inner = CountingProposer({VIDEO: _moments()})
    cp = CachingProposer(inner, list(topics.values()), cache_dir=tmp_path)
    cp.propose(VIDEO, segs, [topics["moratorium"]])
    edited = list(segs) + [TranscriptSegment(start=999.0, end=1000.0, text="a newly added caption line")]
    cp.propose(VIDEO, edited, [topics["moratorium"]])
    assert len(inner.calls) == 2


def test_changed_model_invalidates_cache(tmp_path, topics):
    segs = _segs()
    CachingProposer(CountingProposer({VIDEO: _moments()}), list(topics.values()), cache_dir=tmp_path).propose(
        VIDEO, segs, [topics["moratorium"]])
    other = CountingProposer({VIDEO: _moments()})
    other.model = "a-different-model"
    CachingProposer(other, list(topics.values()), cache_dir=tmp_path).propose(VIDEO, segs, [topics["moratorium"]])
    assert len(other.calls) == 1


def test_failures_propagate_and_are_not_cached(tmp_path, topics):
    class Broken:
        name = "gemini"

        def propose(self, *a):
            raise RuntimeError("quota exceeded")

    cp = CachingProposer(Broken(), list(topics.values()), cache_dir=tmp_path)
    try:
        cp.propose(VIDEO, _segs(), [topics["moratorium"]])
        raise AssertionError("expected the error to propagate")
    except RuntimeError:
        pass
    assert not cache_path(tmp_path, VIDEO).exists()


def test_corrupt_cache_file_is_ignored(tmp_path, topics):
    cache_path(tmp_path, VIDEO).write_text("{not json", encoding="utf-8")
    inner = CountingProposer({VIDEO: _moments()})
    got = CachingProposer(inner, list(topics.values()), cache_dir=tmp_path).propose(
        VIDEO, _segs(), [topics["moratorium"]])
    assert len(inner.calls) == 1 and len(got) == 1


def test_cached_fabrications_are_still_rejected_by_the_pipeline(tmp_path, candidates, videos, topics):
    """A cache is not trusted: a fabricated quote saved on disk must still be dropped."""
    segs = _segs()
    cp = CachingProposer(CountingProposer({VIDEO: _moments()}), list(topics.values()), cache_dir=tmp_path)
    cp.propose(VIDEO, segs, [topics["moratorium"]])  # warm the cache (includes FAKE)
    data = json.loads(cache_path(tmp_path, VIDEO).read_text(encoding="utf-8"))
    assert any(m["quote_text"] == FAKE for m in data["moments"])

    cand = next(c for c in candidates if c.id == "fictional-jordan-vale")
    r = pipeline.build_topic_result(cand, topics["clean_power_requirement"], videos, proposer=cp,
                                    all_candidates=candidates)
    quotes = " ".join(c.statement.quote_text for c in r.cards)
    assert "ban every data center" not in quotes
    assert r.cards and all(c.statement.found_by == "llm" for c in r.cards)
    assert r.mode == "llm"
