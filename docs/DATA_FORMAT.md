# Data format

Source of truth: `backend/models.py` (pydantic). Samples: `data/seed/` (**FICTIONAL**) and `config/topics.json`.

Layout of a data dir (`ONRECORD_DATA_DIR`, default `data/seed`; real data → `data/real`):

```
<data dir>/
  candidates.json      {"candidates": [Candidate, ...]}
  videos.json          {"videos": [Video, ...]}
  transcripts/<video_id>.json   Transcript
```

Real transcripts live in `data/transcripts/` and are committed, so the demo machine never has to re-fetch them (YouTube rate-limits caption requests). Add new ones with `scripts/fetch_transcript.py`. Gemini caches (`*.proposals.json`) stay local and gitignored. Curated `candidates.json`/`videos.json` are committed.

## Candidate
| field | type | notes |
|---|---|---|
| id | str | slug, stable |
| name | str | |
| office | str | e.g. "State Senate, District 14" |
| party | str | **display only**; pipeline never reads it |
| jurisdiction | str | |
| election_date | date (YYYY-MM-DD) | |
| sources | list[str] | official channels/pages we curate from |
| fictional | bool | `true` only in seed data |
| current_position | str, optional | **display only**; the office or job they hold now. Shown in search results and on their page |
| photo_url | str, optional | **display only**; a photo we are licensed to show (rule 12). Without it the site shows initials |
| photo_credit | str, optional | required with `photo_url`: who made it and its license |

## Video
| field | type | notes |
|---|---|---|
| id | str | |
| candidate_id | str | |
| title | str | as published |
| publisher | str | official publisher name (shown on cards) |
| url | str | official URL; we link/embed at a timestamp, never re-host |
| published_date | date | |
| venue | str | where it was said |
| duration_sec | int | used for "hours searched" |
| transcript_path | str | relative to the data dir |
| transcript_source | enum | `official_captions`, `publisher_transcript`, `platform_auto_captions`, `hand_transcribed`, `fictional`. **No LLM-generated option exists.** |
| fictional | bool | |

## Transcript
```json
{"video_id": "...", "transcript_source": "official_captions",
 "segments": [{"start": 131.0, "end": 137.5, "text": "exact caption text"}]}
```

## Topic (`config/topics.json`, fixed checklist)
| field | type | notes |
|---|---|---|
| id | str | |
| label | str | shown to voters |
| description | str | |
| example_phrases | list[str] | keyword-mode matching (normalized, whole-word sequence) |
| suggested_question | str | neutral question for the empty state (addition to the original spec) |

## Statement (clip card)
| field | type | notes |
|---|---|---|
| id | str | `<video_id>:<topic_id>:<start_ms>` |
| candidate_id, topic_id, video_id | str | |
| quote_text | str | **copied from the transcript**, never from Gemini |
| video_url | str | |
| start_sec, end_sec | float | true transcript timestamps (corrected if a proposal was off) |
| context_before, context_after | str | transcript text immediately before/after (1 segment each side) |
| verified | bool | always `true` in API output; unverified proposals are dropped |
| verification_method | `exact_normalized` \| `near_exact` \| `none` | see DECISIONS.md D6 |
| label | `measured` \| `modeled` \| `assumed` | the quote: `measured` once verified |
| topic_match_label | same | that the quote is *about* the topic: `modeled` (keyword/LLM judgement) |
| found_by | `llm` \| `keyword` | |
| timestamp_corrected | bool | proposal timestamp was off by > 3 s |

Sample: `data/seed/statements.sample.json`.

## API wrappers
- `ClipCard = {statement, source: {title, publisher, published_date, venue, url, transcript_source}}`
- `TopicResult = {candidate, topic, coverage: {videos_searched, hours_searched, label}, mode, cards[], empty_state?, unevenness_warning?}`

## Adding real data (Owner C)
1. Only official sources (docs/SOURCES.md). Record publisher, date, venue, duration.
2. Fetch the official transcript; never generate it.
3. Run the pipeline; **watch every displayed clip at its timestamp** and confirm speaker + words. A second person re-checks.
4. Commit `candidates.json`/`videos.json` in small commits: `data: add <candidate> <n> videos`.
