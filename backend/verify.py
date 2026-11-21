"""Verbatim verification. The heart of rule 2 (AGENTS.md).

Given a PROPOSED quote (from Gemini or keyword mode) and the official transcript:
- find it in the transcript (exact after normalization, or near-exact; see DECISIONS.md D6)
- if found: return the TRANSCRIPT's words (never the proposal's), the TRUE timestamps
  (nearest occurrence to the proposed time), and surrounding context
- if not found: reject. Rejected proposals are never shown.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional, Sequence

import config
from models import TranscriptSegment

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def normalize_token(tok: str) -> str:
    tok = unicodedata.normalize("NFKC", tok).lower()
    tok = tok.replace("’", "'").replace("‘", "'")
    return _NON_ALNUM.sub("", tok)


def normalize_text(text: str) -> list[str]:
    return [n for n in (normalize_token(t) for t in text.split()) if n]


@dataclass
class _Tok:
    norm: str
    orig: str
    seg: int


@dataclass
class VerificationResult:
    verified: bool
    method: str  # exact_normalized | near_exact | none
    similarity: float
    reason: str
    quote_text: Optional[str] = None  # transcript words for the located span
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None
    context_before: str = ""
    context_after: str = ""
    timestamp_corrected: bool = False


def _tokenize(segments: Sequence[TranscriptSegment]) -> list[_Tok]:
    toks: list[_Tok] = []
    for i, seg in enumerate(segments):
        for orig in seg.text.split():
            n = normalize_token(orig)
            if n:
                toks.append(_Tok(n, orig, i))
    return toks


def _span_result(
    toks: list[_Tok], i: int, j: int, segments: Sequence[TranscriptSegment],
    proposed_start: Optional[float], method: str, similarity: float, verified: bool, reason: str,
) -> VerificationResult:
    """Build a result for transcript tokens [i, j)."""
    first_seg, last_seg = toks[i].seg, toks[j - 1].seg
    ctx_first = max(0, first_seg - config.CONTEXT_SEGMENTS)
    ctx_last = min(len(segments) - 1, last_seg + config.CONTEXT_SEGMENTS)
    before = [t.orig for t in toks[:i] if t.seg >= ctx_first]
    after = [t.orig for t in toks[j:] if t.seg <= ctx_last]
    start = segments[first_seg].start
    corrected = proposed_start is not None and abs(proposed_start - start) > config.TIMESTAMP_TOLERANCE_SEC
    return VerificationResult(
        verified=verified, method=method, similarity=round(similarity, 4), reason=reason,
        quote_text=" ".join(t.orig for t in toks[i:j]),
        start_sec=start, end_sec=segments[last_seg].end,
        context_before=" ".join(before), context_after=" ".join(after),
        timestamp_corrected=corrected,
    )


def _distance(toks: list[_Tok], i: int, segments, proposed_start: Optional[float]) -> float:
    if proposed_start is None:
        return 0.0
    return abs(segments[toks[i].seg].start - proposed_start)


def verify_quote(
    quote: str,
    segments: Sequence[TranscriptSegment],
    proposed_start: Optional[float] = None,
    allow_near: bool = True,
) -> VerificationResult:
    q = normalize_text(quote)
    if len(q) < config.MIN_QUOTE_TOKENS:
        return VerificationResult(False, "none", 0.0, f"quote shorter than {config.MIN_QUOTE_TOKENS} words")
    toks = _tokenize(segments)
    norms = [t.norm for t in toks]
    n = len(q)

    # 1) exact normalized match; choose occurrence nearest the proposed timestamp
    exact = [i for i in range(len(norms) - n + 1) if norms[i:i + n] == q]
    if exact:
        i = min(exact, key=lambda k: _distance(toks, k, segments, proposed_start))
        return _span_result(toks, i, i + n, segments, proposed_start, "exact_normalized", 1.0, True,
                            "exact match after normalization")

    # 2) near-exact
    k = max(1, n // 10)
    best: Optional[tuple[float, float, int, int]] = None  # (ratio, -distance, i, j)
    qset = set(q)
    for size in range(max(1, n - k), n + k + 1):
        for i in range(0, len(norms) - size + 1):
            window = norms[i:i + size]
            if len(qset.intersection(window)) < 0.5 * len(qset):
                continue
            sm = SequenceMatcher(None, q, window, autojunk=False)
            if sm.quick_ratio() < (best[0] if best else 0.5):
                continue
            r = sm.ratio()
            cand = (r, -_distance(toks, i, segments, proposed_start), i, i + size)
            if best is None or cand[:2] > best[:2]:
                best = cand

    if best is None:
        return VerificationResult(False, "none", 0.0, "not found in transcript")
    ratio, _, i, j = best
    window = norms[i:j]
    if ratio < config.NEAR_EXACT_THRESHOLD:
        r = _span_result(toks, i, j, segments, proposed_start, "none", ratio, False,
                         f"not verbatim: closest passage similarity {ratio:.2f} < {config.NEAR_EXACT_THRESHOLD}")
        return r
    changed: set[str] = set()
    for op, a1, a2, b1, b2 in SequenceMatcher(None, q, window, autojunk=False).get_opcodes():
        if op != "equal":
            changed.update(q[a1:a2])
            changed.update(window[b1:b2])
    critical = changed & config.CRITICAL_TOKENS
    if critical:
        return _span_result(toks, i, j, segments, proposed_start, "none", ratio, False,
                            f"not verbatim: changes meaning-critical word(s) {sorted(critical)}")
    if not allow_near:
        return _span_result(toks, i, j, segments, proposed_start, "none", ratio, False,
                            "strict mode: only exact matches accepted")
    return _span_result(toks, i, j, segments, proposed_start, "near_exact", ratio, True,
                        f"near-exact match (similarity {ratio:.2f} >= {config.NEAR_EXACT_THRESHOLD})")
