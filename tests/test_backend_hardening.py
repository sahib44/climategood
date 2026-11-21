"""/health drop rate, coverage edge cases, and /reports validation."""
import json

import pytest
from fastapi.testclient import TestClient

import config
import main
import pipeline
from llm import FakeProposer, ProposedMoment
from models import Candidate, Coverage, Video

client = TestClient(main.app)
REAL = "we should only build them if they bring new clean power with them"


@pytest.fixture(autouse=True)
def _fresh_stats():
    pipeline.reset_llm_proposal_stats()
    yield
    pipeline.reset_llm_proposal_stats()


# ---------- drop rate ----------

def _run_llm(candidates, videos, topics, moments):
    cand = next(c for c in candidates if c.id == "fictional-jordan-vale")
    return pipeline.build_topic_result(cand, topics["clean_power_requirement"], videos,
                                       proposer=FakeProposer({"fv-vale-townhall": moments}), all_candidates=candidates)


def test_health_reports_drop_rate(candidates, videos, topics):
    _run_llm(candidates, videos, topics, [
        ProposedMoment(topic_id="clean_power_requirement", start_sec=131.0, end_sec=137.5, reason="r", quote_text=REAL),
        ProposedMoment(topic_id="clean_power_requirement", start_sec=140.0, end_sec=145.0, reason="r",
                       quote_text="I will personally ban every data center in this state"),
    ])
    s = client.get("/health").json()["llm_proposals"]
    assert (s["proposed"], s["verified"], s["dropped"], s["drop_rate"]) == (2, 1, 1, 0.5)
    assert s["label"] == "modeled"


def test_refresh_does_not_double_count(candidates, videos, topics):
    m = [ProposedMoment(topic_id="clean_power_requirement", start_sec=131.0, end_sec=137.5, reason="r", quote_text=REAL)]
    _run_llm(candidates, videos, topics, m)
    _run_llm(candidates, videos, topics, m)
    assert pipeline.llm_proposal_stats()["proposed"] == 1


def test_keyword_mode_is_not_counted_and_empty_stats_have_no_rate(candidates, videos, topics):
    cand = next(c for c in candidates if c.id == "fictional-jordan-vale")
    pipeline.build_topic_result(cand, topics["moratorium"], videos, all_candidates=candidates)  # keyword
    s = pipeline.llm_proposal_stats()
    assert s["proposed"] == 0 and s["drop_rate"] is None


# ---------- coverage edge cases ----------

def _cand(cid):
    return Candidate(id=cid, name=cid, office="o", party="p", jurisdiction="j", election_date="2026-11-03")


def _video(vid, cid, sec):
    return Video(id=vid, candidate_id=cid, title="t", publisher="p", url="https://example.org/" + vid,
                 published_date="2026-01-01", venue="v", duration_sec=sec,
                 transcript_path="transcripts/fv-vale-radio.json", transcript_source="fictional")


def test_zero_videos_gives_zero_coverage_and_an_honest_empty_state(topics):
    r = pipeline.build_topic_result(_cand("nobody-yet"), topics["moratorium"], [], all_candidates=[_cand("nobody-yet")])
    assert r.coverage.videos_searched == 0 and r.coverage.hours_searched == 0.0
    assert r.cards == []
    assert "not searched any videos" in r.empty_state.message
    assert "0 videos" not in r.empty_state.message


def test_short_clip_is_not_rounded_down_to_zero_hours():
    cov = pipeline.coverage_for("c", [_video("clip", "c", 120)])  # 2 minutes
    assert cov.videos_searched == 1 and cov.hours_searched == 0.03


def test_unevenness_with_a_zero_coverage_candidate():
    w = pipeline.unevenness_warning([("A", Coverage(videos_searched=3, hours_searched=2.0)),
                                     ("B", Coverage(videos_searched=0, hours_searched=0.0))])
    assert w and "0 videos (0.0 h) for B" in w


def test_no_warning_when_everyone_has_zero():
    assert pipeline.unevenness_warning([("A", Coverage(videos_searched=0, hours_searched=0.0)),
                                        ("B", Coverage(videos_searched=0, hours_searched=0.0))]) is None


# ---------- /reports validation ----------

@pytest.fixture
def reports(tmp_path, monkeypatch):
    path = tmp_path / "reports.jsonl"
    monkeypatch.setattr(config, "REPORTS_PATH", path)
    return path


def _post(**body):
    return client.post("/reports", json={"problem_type": "wrong_quote", **body})


def test_frontend_shaped_report_is_accepted(reports):
    r = _post(statement_id="fv-vale-debate:moratorium:2464000", candidate_id="fictional-jordan-vale", details="  ")
    assert r.status_code == 200
    assert json.loads(reports.read_text())["details"] == ""  # whitespace stripped


@pytest.mark.parametrize("body, why", [
    ({}, "no statement or candidate"),
    ({"candidate_id": "nobody"}, "unknown candidate"),
    ({"statement_id": "no-such-video:moratorium:1"}, "unknown video"),
    ({"statement_id": "fv-vale-debate:no_such_topic:1"}, "unknown topic"),
    ({"statement_id": "not a statement id"}, "bad format"),
    ({"statement_id": "fv-vale-debate:moratorium:2464000", "candidate_id": "fictional-casey-morrow"}, "wrong candidate"),
    ({"candidate_id": "fictional-jordan-vale", "email": "me@example.org"}, "extra field"),
    ({"candidate_id": "fictional-jordan-vale", "details": "x" * 2001}, "too long"),
])
def test_bad_reports_are_rejected_and_not_stored(reports, body, why):
    r = _post(**body)
    assert r.status_code == 422, why
    assert not reports.exists()
