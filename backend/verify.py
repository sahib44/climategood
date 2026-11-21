"""Verbatim verification. The heart of rule 2 (AGENTS.md).

Given a PROPOSED quote (from Gemini or keyword mode) and the official transcript:
- find it in the transcript (exact after normalization, or near-exact; see DECISIONS.md D6)
- if found: return the TRANSCRIPT's words (never the proposal's), the TRUE timestamps
  (nearest occurrence to the proposed time), and surrounding context
- if not found: reject. Rejected proposals are never shown.

Real captions are messy. Handled here (one test per quirk in tests/test_caption_quirks.py):
- HTML entities (&amp; &#39;) are unescaped.
- Non-speech annotations ([Applause], (laughter), [crowd cheering]) are removed.
- Speaker marks (">>", ">> MODERATOR:", "SPEAKER 2:") are removed, and each one starts a new
  speaker turn. A quote may never span two turns: that would put one person's words in
  another's mouth.
- Fillers (uh, um, ...) are ignored for matching but kept in the displayed transcript text.
- "10%" and "10 percent" match; single number words ("ten") match digits.
- Near-exact matches may never differ on a number.
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional, Sequence

import config
from models import TranscriptSegment

_NON_ALNUM = re.compile(r"[^0-9a-z]+")
# [Applause], (laughter), [crowd cheering], [inaudible]: short, letters only.
_ANNOTATION = re.compile(r"[\[(]\s*[A-Za-z][A-Za-z '\-]{0,38}\s*[\])]")
# ">>" optionally followed by a short capitalized label and a colon: ">> MODERATOR:", ">> Sen. Lee:".
_TURN_MARK = re.compile(r">>+\s*(?:[A-Z][A-Za-z.'\-]*(?:\s+[A-Z][A-Za-z.'\-]*){0,3}\s*:)?")
# Role labels at the start of a caption line, without ">>".
_ROLE_LABEL = re.compile(r"^\s*(?:MODERATOR|NARRATOR|ANNOUNCER|INTERVIEWER|HOST|SPEAKER\s*\d+|Q|A)\s*:", re.I)
_TURN = "\u241e"  # internal marker: a speaker turn starts here

FILLERS = {"uh", "um", "uhm", "umm", "er", "erm", "ah", "hmm", "mm"}
_NUMBER_WORDS = {
    w: str(i) for i, w in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
        "fifteen sixteen seventeen eighteen nineteen twenty".split())
}
_NUMBER_WORDS.update({w: str(10 * i) for i, w in enumerate(
    "_ _ _ thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"})
_NUMBER_WORDS.update({"hundred": "100", "thousand": "1000"})


def clean_caption_text(text: str) -> str:
    """Unescape entities, drop annotations, and replace speaker marks with a turn marker."""
    text = html.unescape(text)
    text = _ROLE_LABEL.sub(f" {_TURN} ", text)
    text = _TURN_MARK.sub(f" {_TURN} ", text)
    text = _ANNOTATION.sub(" ", text)
    return text


def normalize_token(tok: str) -> str:
    tok = unicodedata.normalize("NFKC", tok).lower()
    tok = tok.replace("’", "'").replace("‘", "'").replace("%", "percent")
    n = _NON_ALNUM.sub("", tok)
    return _NUMBER_WORDS.get(n, n)


def _merge_percent(norms: list[str]) -> list[str]:
    """'10' 'percent' -> '10percent' so it equals '10%'."""
    out: list[str] = []
    for n in norms:
        if n == "percent" and out and out[-1].isdigit():
            out[-1] += "percent"
        else:
            out.append(n)
    return out


def normalize_text(text: str) -> list[str]:
    """Normalized tokens used for matching (fillers and speaker marks dropped)."""
    norms = [normalize_token(t) for t in clean_caption_text(text).split() if t != _TURN]
    return _merge_percent([n for n in norms if n and n not in FILLERS])


@dataclass
class _Tok:
    norm: str
    orig: str
    seg: int
    turn: int = 0
    filler: bool = False


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
    turn = 0
    for i, seg in enumerate(segments):
        for orig in clean_caption_text(seg.text).split():
            if orig == _TURN:
                turn += 1
                continue
            n = normalize_token(orig)
            if not n:  # punctuation-only ("&", "--"): not matched, but kept for display
                toks.append(_Tok("", html.unescape(orig), i, turn, True))
                continue
            if n == "percent" and toks and toks[-1].norm.isdigit() and toks[-1].turn == turn:
                toks[-1].norm += "percent"
                toks[-1].orig += " " + orig
                continue
            toks.append(_Tok(n, html.unescape(orig), i, turn, n in FILLERS))
    return toks


def _span_result(
    toks: list[_Tok], i: int, j: int, segments: Sequence[TranscriptSegment],
    proposed_start: Optional[float], method: str, similarity: float, verified: bool, reason: str,
) -> VerificationResult:
    """Build a result for transcript tokens [i, j)."""
    if toks[i].turn != toks[j - 1].turn:
        verified, method = False, "none"
        reason = "not verbatim: the passage spans a speaker change"
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
    all_toks = _tokenize(segments)
    pos = [k for k, t in enumerate(all_toks) if not t.filler]  # match space -> token position
    toks = [all_toks[k] for k in pos]
    norms = [t.norm for t in toks]
    n = len(q)

    def result(i: int, j: int, method: str, sim: float, ok: bool, reason: str) -> VerificationResult:
        # Map back to full token positions so fillers inside the span are still displayed.
        return _span_result(all_toks, pos[i], pos[j - 1] + 1, segments, proposed_start, method, sim, ok, reason)

    # 1) exact normalized match within one speaker turn; nearest the proposed timestamp
    exact = [i for i in range(len(norms) - n + 1)
             if norms[i:i + n] == q and toks[i].turn == toks[i + n - 1].turn]
    if exact:
        i = min(exact, key=lambda k: _distance(toks, k, segments, proposed_start))
        return result(i, i + n, "exact_normalized", 1.0, True, "exact match after normalization")

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
            if toks[i].turn != toks[i + size - 1].turn:
                cand = (r - 1.0, *cand[1:])  # never prefer a window that spans speakers
            if best is None or cand[:2] > best[:2]:
                best = cand

    if best is None or best[0] < 0:
        return VerificationResult(False, "none", 0.0, "not found in transcript")
    ratio, _, i, j = best
    window = norms[i:j]
    if ratio < config.NEAR_EXACT_THRESHOLD:
        return result(i, j, "none", ratio, False,
                      f"not verbatim: closest passage similarity {ratio:.2f} < {config.NEAR_EXACT_THRESHOLD}")
    changed: set[str] = set()
    for op, a1, a2, b1, b2 in SequenceMatcher(None, q, window, autojunk=False).get_opcodes():
        if op != "equal":
            changed.update(q[a1:a2])
            changed.update(window[b1:b2])
    critical = (changed & config.CRITICAL_TOKENS) | {c for c in changed if any(ch.isdigit() for ch in c)}
    if critical:
        return result(i, j, "none", ratio, False,
                      f"not verbatim: changes meaning-critical word(s) {sorted(critical)}")
    if not allow_near:
        return result(i, j, "none", ratio, False, "strict mode: only exact matches accepted")
    return result(i, j, "near_exact", ratio, True,
                  f"near-exact match (similarity {ratio:.2f} >= {config.NEAR_EXACT_THRESHOLD})")
