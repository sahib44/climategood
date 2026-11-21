# 8-hour plan (3 people)

**Owners:** **A** = backend/pipeline · **B** = frontend · **C** = data curation, docs, demo

Rule for every block: `pytest` green before merging; small commits; never commit `.env`.

## Hour 0–1: Setup and schema
- [ ] **All:** clone, read AGENTS.md (10 min, the rules are the product), run `pytest` and both dev servers.
- [ ] **A:** confirm `backend/models.py` matches DATA_FORMAT.md; adjust fields together with C.
- [ ] **B:** confirm Vite app fetches `/candidates`; sketch clip card + empty state + coverage bar on paper.
- [ ] **C:** pick 3–5 real candidates across parties for one race/region; start a list of official video URLs per candidate (SOURCES.md rules).

## Hour 1–3: Transcript fetch, keyword mode, verification, tests
- [ ] **A:** implement `scripts/fetch_transcript.py` for official captions (YouTube creator captions / C-SPAN transcript) → `data/transcripts/<video_id>.json`. Never LLM-generate.
- [ ] **A:** harden `verify.py` on real caption quirks (`[Applause]`, `>>` speaker marks, numbers). Add a test per quirk.
- [ ] **A:** keyword mode end-to-end on real transcripts.
- [ ] **B:** candidate picker + topic checklist UI; call `/candidates/{id}/topics/{topic_id}`.
- [ ] **C:** for each video: verify it's the official publisher, record `published_date`, `venue`, `duration_sec`, `transcript_source`. Tune `example_phrases` in `config/topics.json` (reviewed change).

## Hour 3–5: Gemini proposals + UI clip cards
- [ ] **A:** wire `GeminiProposer` (`ONRECORD_MODE=llm`), structured JSON output; cache proposals to `data/transcripts/<video_id>.proposals.json`; fallback to keyword on any error/quota. Log drop rate (proposed vs verified) — show it in `/health` as `modeled` stat.
- [ ] **B:** clip card: quote (verbatim), context before/after (muted), date · venue · publisher, "Watch at 12:34" link/embed at `start_sec`, labels `measured`/`modeled`. Same component for every candidate.
- [ ] **C:** hand-verify every displayed quote against the video for the first 2 candidates. Write `CORRECTIONS.md` template.

## Hour 5–6: Coverage, empty state, report-a-problem
- [ ] **A:** coverage + unevenness edge cases (0 videos, 0 hours); `/reports` validation.
- [ ] **B:** coverage line on every candidate page; unevenness banner; empty state with suggested question; "Report a problem" (mailto + POST form).
- [ ] **C:** write neutral suggested questions review (no loaded wording); check each topic's empty-state text.

## Hour 6–7: Real data
- [ ] **C (lead), A, B help:** 3–5 real candidates across parties, **15–30 hand-verified videos**. Every displayed quote checked by a second person. Remove fictional seed from the demo data dir (`ONRECORD_DATA_DIR=data/real`).
- [ ] **A:** run full pipeline on all; spot-check timestamps.

## Hour 7–8: Demo polish and rehearsal
- [ ] **B:** visual polish, mobile check, footer ("OnRecord does not rate or endorse candidates").
- [ ] **C:** run DEMO_SCRIPT.md twice with a timer; prepare offline fallback (keyword mode, local data).
- [ ] **A:** freeze `main`; tag `demo`.

## Stretch goals (only if everything above is done)
- [ ] **Snowflake side-quest:** load transcripts + verified statements into Snowflake; use Cortex Search for phrase recall across candidates — still verified by our code before display.
- [ ] **Browserbase side-quest:** headless browser to collect official video metadata/caption links from campaign and C-SPAN pages (respecting robots/ToS) → feeds C's curation queue, human approves.
- [ ] **Public-data panel** next to each topic (e.g., utility rate filings, state data center siting rules, grid interconnection queue) — context only, **no verdicts**, every number labeled measured/modeled/assumed with source.
- [ ] **"Ask this" generator:** fixed per-topic question templates filled with candidate name/office (no LLM-written questions).
