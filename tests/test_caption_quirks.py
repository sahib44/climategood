"""Real caption quirks the verifier must handle. All text here is FICTIONAL, written for tests."""
from keyword_match import KeywordProposer
from models import Topic, TranscriptSegment as S
from verify import verify_quote


def segs(*texts, step=5.0):
    return [S(start=i * step, end=(i + 1) * step, text=t) for i, t in enumerate(texts)]


def test_applause_and_laughter_annotations_are_ignored():
    t = segs("we have to make the data centers pay [Applause] for their own grid upgrades (laughter) today")
    r = verify_quote("we have to make the data centers pay for their own grid upgrades", t)
    assert r.verified and r.method == "exact_normalized"
    assert "Applause" not in r.quote_text


def test_multiword_annotation_is_ignored():
    t = segs("every town deserves [crowd cheering] a real vote on these projects")
    assert verify_quote("every town deserves a real vote on these projects", t).verified


def test_speaker_marks_are_not_part_of_the_quote():
    t = segs(">> MODERATOR: Next question.", ">> I would require disclosure of water use for every facility")
    r = verify_quote("I would require disclosure of water use for every facility", t)
    assert r.verified and r.quote_text.startswith("I would")
    assert ">>" not in r.quote_text and "MODERATOR" not in r.context_before


def test_quote_spanning_a_speaker_change_is_rejected():
    # The moderator asks, the candidate answers; stitching them together would misattribute words.
    t = segs(">> MODERATOR: Should the state ban new data centers", ">> CANDIDATE: I think we need more study")
    r = verify_quote("should the state ban new data centers I think", t)
    assert not r.verified


def test_role_label_without_chevrons_starts_a_new_turn():
    t = segs("MODERATOR: would you support a pause on approvals", "SPEAKER 2: yes for one year")
    assert not verify_quote("would you support a pause on approvals yes for one year", t).verified


def test_fillers_are_ignored_for_matching_but_still_shown():
    t = segs("I, uh, would require um new clean power for every new facility")
    r = verify_quote("I would require new clean power for every new facility", t)
    assert r.verified and r.method == "exact_normalized"
    assert "uh," in r.quote_text and "um" in r.quote_text  # transcript words, verbatim


def test_percent_sign_matches_spoken_percent():
    t = segs("cut the rate increase by 10% for residential customers")
    assert verify_quote("cut the rate increase by 10 percent for residential customers", t).verified
    assert verify_quote("cut the rate increase by ten percent for residential customers", t).verified


def test_near_exact_never_allows_a_changed_number():
    t = segs("we should cap new data center connections at 500 megawatts until the grid study is finished")
    r = verify_quote("we should cap new data center connections at 900 megawatts until the grid study is finished", t)
    assert not r.verified and "critical" in r.reason


def test_html_entities_are_unescaped():
    t = segs("water &amp; energy use should be public, and that&#39;s not negotiable")
    r = verify_quote("water & energy use should be public, and that's not negotiable", t)
    assert r.verified
    assert "&amp;" not in r.quote_text


def test_all_caps_captions_match():
    t = segs("WE WILL NOT APPROVE ANY PROJECT WITHOUT A PUBLIC HEARING")
    assert verify_quote("We will not approve any project without a public hearing", t).verified


def test_keyword_mode_proposes_one_speaker_at_a_time():
    topic = Topic(id="t", label="t", description="t", example_phrases=["public hearing"], suggested_question="q")
    t = segs(">> MODERATOR: about the public hearing >> CANDIDATE: every project needs a public hearing first")
    props = KeywordProposer().propose("v", t, [topic])
    assert [p.quote_text for p in props] == ["about the public hearing", "every project needs a public hearing first"]
    assert all(verify_quote(p.quote_text, t).verified for p in props)
