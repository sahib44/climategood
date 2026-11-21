"""Pipeline behaviour: LLM proposals are verified, formatting is neutral, empty state is honest."""
import re

import pipeline
from llm import FakeProposer, ProposedMoment


def _cand(candidates, cid):
    return next(c for c in candidates if c.id == cid)


def test_fabricated_llm_proposal_is_dropped_and_real_one_kept(candidates, videos, topics):
    fake = FakeProposer({"fv-vale-townhall": [
        ProposedMoment(topic_id="clean_power_requirement", start_sec=131.0, end_sec=137.5, reason="real",
                       quote_text="we should only build them if they bring new clean power with them"),
        ProposedMoment(topic_id="clean_power_requirement", start_sec=140.0, end_sec=145.0, reason="fabricated",
                       quote_text="I will personally ban every data center in this state"),
    ]})
    r = pipeline.build_topic_result(_cand(candidates, "fictional-jordan-vale"), topics["clean_power_requirement"],
                                    videos, proposer=fake, all_candidates=candidates)
    quotes = [c.statement.quote_text for c in r.cards]
    assert len(quotes) == 1
    assert "ban every data center" not in " ".join(quotes)
    card = r.cards[0].statement
    assert card.found_by == "llm" and card.verified and card.label == "measured"


def test_llm_wrong_timestamp_is_corrected_in_card(candidates, videos, topics):
    fake = FakeProposer({"fv-vale-townhall": [
        ProposedMoment(topic_id="water_energy_disclosure", start_sec=5.0, end_sec=9.0, reason="off",
                       quote_text="Any project should have to tell us how much water and energy it uses every year."),
    ]})
    r = pipeline.build_topic_result(_cand(candidates, "fictional-jordan-vale"), topics["water_energy_disclosure"],
                                    videos, proposer=fake, all_candidates=candidates)
    s = r.cards[0].statement
    assert s.start_sec == 143.0 and s.timestamp_corrected


def test_llm_failure_falls_back_to_keyword(candidates, videos, topics):
    class Broken:
        name = "gemini"

        def propose(self, *a):
            raise RuntimeError("quota exceeded")

    r = pipeline.build_topic_result(_cand(candidates, "fictional-jordan-vale"), topics["moratorium"],
                                    videos, proposer=Broken(), all_candidates=candidates)
    assert r.cards and all(c.statement.found_by == "keyword" for c in r.cards)


def _shape(obj):
    """Structure of a JSON value with values erased: keys and types only."""
    if isinstance(obj, dict):
        return {k: _shape(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_shape(obj[0])] if obj else []
    return type(obj).__name__


def test_two_parties_get_identical_output_format(candidates, videos, topics):
    a = _cand(candidates, "fictional-jordan-vale")
    b = _cand(candidates, "fictional-casey-morrow")
    assert a.party != b.party
    ra = pipeline.build_topic_result(a, topics["moratorium"], videos, all_candidates=candidates)
    rb = pipeline.build_topic_result(b, topics["moratorium"], videos, all_candidates=candidates)
    assert ra.cards and rb.cards
    da, db = ra.model_dump(mode="json"), rb.model_dump(mode="json")
    assert _shape(da) == _shape(db)
    # Same labels/methods vocabulary for both
    for d in (da, db):
        for card in d["cards"]:
            assert card["statement"]["label"] == "measured"
            assert card["statement"]["topic_match_label"] == "modeled"


def test_party_swap_does_not_change_output(candidates, videos, topics):
    a = _cand(candidates, "fictional-jordan-vale")
    swapped = a.model_copy(update={"party": "Placeholder Party B"})
    r1 = pipeline.build_topic_result(a, topics["ratepayer_protection"], videos, all_candidates=candidates)
    r2 = pipeline.build_topic_result(swapped, topics["ratepayer_protection"], videos, all_candidates=candidates)
    assert r1.cards == r2.cards


def test_all_matches_in_chronological_order(candidates, videos, topics):
    r = pipeline.build_topic_result(_cand(candidates, "fictional-jordan-vale"), topics["ratepayer_protection"],
                                    videos, all_candidates=candidates)
    assert len(r.cards) == 2  # every match, no "best" selection
    dates = [(c.source.published_date, c.statement.start_sec) for c in r.cards]
    assert dates == sorted(dates)
    for c in r.cards:
        assert c.source.url and c.source.publisher and c.source.published_date and c.source.venue


POSITION_WORDS = re.compile(r"\b(support|supports|oppose|opposes|against|favor|favors|position is|likely|probably|silent|refus)",
                            re.I)


def test_zero_matches_returns_empty_state_with_coverage_not_a_position(candidates, videos, topics):
    q = _cand(candidates, "fictional-taylor-quinn")
    r = pipeline.build_topic_result(q, topics["moratorium"], videos, all_candidates=candidates)
    assert r.cards == []
    assert r.coverage.videos_searched == 1 and r.coverage.hours_searched == 0.5
    assert r.coverage.label == "measured"
    assert r.empty_state.message == "No statement found in the 1 video we searched."
    assert r.empty_state.suggested_question.endswith("?")
    assert not POSITION_WORDS.search(r.empty_state.message)


def test_all_suggested_questions_are_neutral(topics):
    for t in topics.values():
        assert t.suggested_question.endswith("?")
        assert not re.search(r"\b(why do you|don't you|shouldn't you|admit|refuse)\b", t.suggested_question, re.I)


def test_unevenness_warning_when_coverage_differs(candidates, videos, topics):
    r = pipeline.build_topic_result(candidates[0], topics["moratorium"], videos, all_candidates=candidates)
    assert r.unevenness_warning and "uneven" in r.unevenness_warning
