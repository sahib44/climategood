# Decisions

## D1. Criteria checklist, no score

**Chosen:** a fixed criteria checklist (topics) with verbatim evidence under each one. No score.

**Rejected:**
- **(A) Evidence only.** Free search over everything a candidate said. It's neutral, but voters have no structure: they don't know what to look for, and comparisons between candidates are ad hoc.
- **(B) A labeled advocacy score**, such as "Climate score: 72/100".

**Reasons:**
- **Most positions are conditional.** A candidate might say "build them if they bring new clean power" or "only with local approval." A score has to flatten those conditions into a number, and the conditions are the actual position.
- **A score hides a value judgment in a formula.** How much should ratepayer protection weigh against a moratorium? That is a political choice. Putting it in code makes it look objective when it isn't.
- **The climate impact of data centers depends on the power source.** The same "yes to data centers" can be good or bad for emissions depending on what powers them. A single number can't express that honestly.
- A checklist gives voters structure. They can see which questions a candidate has addressed, and the tool never decides for them which answers are right.

**Option B later:** possible only as an **opt-in** view. It would need named, published criteria and weights, a named author or organization responsible for it, a clear label, and a link to the evidence behind each point. It is **never the default** and is never mixed into the main view.

**Risks we accept and mitigate** (details in TRUST_AND_SAFETY.md):

| Risk | Mitigation |
|---|---|
| Misattribution (wrong speaker in a debate) | Curated official sources per candidate. Human verification before real data ships. Report-a-problem path. |
| Selection bias (which videos we chose) | Coverage counts shown. Curation rules in SOURCES.md. Same rules for every candidate. |
| Context stripping | Preceding and following transcript lines on every card. The full clip is one click away. |
| Coverage asymmetry (incumbents have more footage than challengers) | Per-candidate coverage counts and an unevenness warning. The empty state never implies a position. |
| Deepfakes or edited clips | Official publisher sources only. Link to the original, never re-host. |
| Gemini timestamp or quote errors | Gemini only proposes. Code verifies against the transcript, copies the text from the transcript, and corrects the timestamp to the real one. Fabricated quotes are dropped and tested for. |

## D2. Frontend in plain JavaScript (not TypeScript)

The team mixes Python and JS skills, and we have less than 8 hours. Plain JS + Vite + React has no type-check step to debug, no tsconfig, and is the lowest barrier for whoever picks up a component. The API contract is typed on the backend by pydantic, so the source of truth is still typed. If the project continues after the hackathon, migrate to TS. Vite supports it with no restructuring.

## D3. JSON files, no database

The data is small (tens of videos), mostly hand-curated, and reviewed in git diffs. JSON in `data/` keeps curation visible and reviewable. Revisit when data passes a few hundred videos.

## D4. Never generate transcripts with an LLM

We verify quotes against the transcript. If Gemini made the transcript, verifying Gemini's proposals against it would be circular. Transcripts come only from official captions or publisher-provided transcripts.

## D5. Keyword (no-LLM) mode is first-class

The demo must not depend on an API quota or network. Keyword mode uses the same verifier and the same card format. Only `found_by` differs.

## D6. Near-exact matching threshold

Captions vary slightly (such as "gonna"/"going to" or dropped filler words). Matching rules:
- **Exact** after normalization (lowercase, Unicode NFKC, punctuation stripped, whitespace collapsed). Method: `exact_normalized`.
- **Near-exact:** token similarity (difflib ratio) >= **0.90**, at least 4 tokens, **and** no changed token is a negation or stance word (not, never, support, oppose, ...). Method: `near_exact`.
- In both cases **the quote shown is copied from the transcript**, not from the proposal.
- `POST /verify` (the "check a quote" demo) is strict and accepts `exact_normalized` only.
