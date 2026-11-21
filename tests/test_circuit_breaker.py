"""A slow or failing LLM must not freeze a page: fail fast, then skip it for a cooldown."""
import pytest

import circuit_breaker
import config
import pipeline
from circuit_breaker import CircuitBreakerProposer, LLMUnavailable
from llm import ProposedMoment
from proposal_cache import CachingProposer


@pytest.fixture(autouse=True)
def _closed_breaker():
    circuit_breaker.reset()
    yield
    circuit_breaker.reset()


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Flaky:
    """Fails while `failing` is True; counts calls."""
    name = "gemini"
    model = "test-model"

    def __init__(self, failing=True):
        self.failing = failing
        self.calls = 0

    def propose(self, video_id, segments, topics):
        self.calls += 1
        if self.failing:
            raise RuntimeError("503 UNAVAILABLE: high demand")
        return [ProposedMoment(topic_id=topics[0].id, quote_text="q w e r", start_sec=0, end_sec=1, reason="r")]


def _one(topics):
    return [topics["moratorium"]]


def test_failure_opens_breaker_and_later_calls_skip_the_llm(topics):
    inner, clock = Flaky(), Clock()
    cb = CircuitBreakerProposer(inner, cooldown_sec=60, clock=clock)
    with pytest.raises(RuntimeError):
        cb.propose("v1", [], _one(topics))
    for vid in ("v2", "v3", "v4"):
        with pytest.raises(LLMUnavailable):
            cb.propose(vid, [], _one(topics))
    assert inner.calls == 1  # waited on the LLM once, not once per video


def test_breaker_closes_after_cooldown_and_success_resets_it(topics):
    inner, clock = Flaky(), Clock()
    cb = CircuitBreakerProposer(inner, cooldown_sec=60, clock=clock)
    with pytest.raises(RuntimeError):
        cb.propose("v1", [], _one(topics))
    clock.t += 61
    inner.failing = False
    assert cb.propose("v1", [], _one(topics))
    assert not circuit_breaker.is_open("gemini", clock)


def test_breaker_state_carries_across_instances(topics):
    """The API builds a new proposer per request; the cooldown must still apply."""
    clock = Clock()
    with pytest.raises(RuntimeError):
        CircuitBreakerProposer(Flaky(), cooldown_sec=60, clock=clock).propose("v1", [], _one(topics))
    second = Flaky(failing=False)
    with pytest.raises(LLMUnavailable):
        CircuitBreakerProposer(second, cooldown_sec=60, clock=clock).propose("v1", [], _one(topics))
    assert second.calls == 0


def test_pipeline_waits_on_a_failing_llm_once_per_page(candidates, videos, topics):
    inner = Flaky()
    cand = next(c for c in candidates if c.id == "fictional-jordan-vale")  # 3 videos
    r = pipeline.build_topic_result(cand, topics["moratorium"], videos,
                                    proposer=CircuitBreakerProposer(inner), all_candidates=candidates)
    assert inner.calls == 1
    assert r.cards and all(c.statement.found_by == "keyword" for c in r.cards)


def test_cached_answers_are_served_while_breaker_is_open(tmp_path, topics):
    inner, clock = Flaky(failing=False), Clock()
    cached = CachingProposer(CircuitBreakerProposer(inner, cooldown_sec=60, clock=clock),
                             list(topics.values()), cache_dir=tmp_path)
    cached.propose("v1", [], _one(topics))  # warm the cache
    inner.failing = True
    with pytest.raises(RuntimeError):
        CachingProposer(CircuitBreakerProposer(inner, cooldown_sec=60, clock=clock),
                        list(topics.values()), cache_dir=tmp_path).propose("v2", [], _one(topics))
    assert circuit_breaker.is_open("gemini", clock)
    assert cached.all_moments("v1", [])  # still answered from disk
    assert inner.calls == 2  # the warm-up and the failure; the cached answer made no call


def test_breaker_keeps_cache_keys_unchanged(topics):
    from proposal_cache import cache_key
    inner = Flaky(failing=False)
    assert cache_key(CircuitBreakerProposer(inner), [], list(topics.values())) == cache_key(inner, [], list(topics.values()))


def test_gemini_client_gets_a_timeout_and_no_sdk_retries(monkeypatch):
    genai = pytest.importorskip("google.genai")
    seen = {}

    class FakeClient:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setenv("GEMINI_TIMEOUT_SEC", "7")
    from llm import GeminiProposer
    GeminiProposer(api_key="not-a-real-key")
    opts = seen["http_options"]
    assert opts.timeout == 7000
    assert opts.retry_options.attempts == config.LLM_ATTEMPTS == 1
