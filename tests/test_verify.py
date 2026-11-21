"""Rule 2: verbatim only. All quotes here are from FICTIONAL seed transcripts."""
from verify import verify_quote


def test_quote_in_transcript_is_accepted(transcript):
    segs = transcript("fv-vale-townhall")
    r = verify_quote("we should only build them if they bring new clean power", segs, proposed_start=131.0)
    assert r.verified
    assert r.method == "exact_normalized"
    assert r.start_sec == 131.0


def test_normalization_ignores_case_punctuation_and_curly_quotes(transcript):
    segs = transcript("fv-vale-townhall")
    r = verify_quote("I DON’T want families paying higher electric bills!!", segs)
    assert r.verified
    # Text shown comes from the transcript, not from the proposal.
    assert r.quote_text == "I don't want families paying higher electric bills"


def test_fabricated_quote_is_rejected(transcript):
    segs = transcript("fv-vale-townhall")
    r = verify_quote("Data centers are the future and we should build as many as possible", segs)
    assert not r.verified
    assert r.method == "none"


def test_negation_flip_is_rejected_even_though_nearly_identical(transcript):
    segs = transcript("fv-vale-debate")
    real = "On the moratorium question, I would not support a statewide moratorium right now."
    flipped = "On the moratorium question, I would support a statewide moratorium right now."
    assert verify_quote(real, segs).verified
    r = verify_quote(flipped, segs)
    assert not r.verified
    assert "critical" in r.reason


def test_near_exact_accepts_caption_noise_but_shows_transcript_words(transcript):
    segs = transcript("fv-vale-radio")
    # One harmless dropped word ("new") in a long quote
    proposal = "Utility customers should not be stuck with the cost of transmission lines for these facilities"
    r = verify_quote(proposal, segs)
    assert r.verified and r.method == "near_exact"
    assert "new transmission lines" in r.quote_text


def test_too_short_quote_is_rejected(transcript):
    assert not verify_quote("clean power", transcript("fv-vale-townhall")).verified


def test_real_quote_with_wrong_timestamp_is_corrected(transcript):
    segs = transcript("fv-vale-townhall")
    r = verify_quote("how much water and energy it uses every year", segs, proposed_start=9999.0)
    assert r.verified
    assert r.start_sec == 143.0  # true timestamp from the transcript
    assert r.timestamp_corrected


def test_context_includes_surrounding_lines(transcript):
    segs = transcript("fv-vale-townhall")
    r = verify_quote("I don't want families paying higher electric bills", segs)
    assert "new clean power with them." in r.context_before
    assert r.context_after.startswith("so a data center can plug in.")
    assert "how much water" in r.context_after


def test_strict_mode_rejects_near_matches(transcript):
    segs = transcript("fv-vale-radio")
    proposal = "Utility customers should not be stuck with the cost of transmission lines for these facilities"
    assert not verify_quote(proposal, segs, allow_near=False).verified
