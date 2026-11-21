# OnRecord

Search a candidate and see what they have **actually said, word for word**, about specific climate issues (starting with data centers), with a clip that starts at the moment they said it. **No score, no rating, no ranking.** Evidence, or "no statement found."

Built at the MTC hackathon, Climate Good track, sponsored by the Rutgers Office of Climate Action.

Read first: [AGENTS.md](AGENTS.md) (hard rules), [docs/PRODUCT.md](docs/PRODUCT.md), [docs/TASKS.md](docs/TASKS.md).

## Status

**Scaffold.** It works end to end on **fictional** seed data in keyword (no-LLM) mode:
- Backend: FastAPI with `/health`, `/candidates`, `/topics`, `/candidates/{id}/topics/{topic_id}`, `/verify`, and `/reports`.
- Verifier: exact and near-exact matching, timestamp correction, and context, hardened for real captions ([Applause], `>>` speaker marks, fillers, numbers, HTML entities). A quote can never span two speakers. Tested.
- Transcript fetch: `scripts/fetch_transcript.py` pulls YouTube creator captions, or parses a publisher's .vtt/.srt file. Tested, plus one live YouTube check.
- Gemini proposer: written against `google-genai` but **not yet exercised against the live API**.
- Frontend: a Vite + React stub that lists candidates with coverage counts.
- Not done: the clip card UI and real data.

## Run

Requires Python 3.11+ and Node 20+.

```bash
cp .env.example .env
```

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
```

```bash
.venv/bin/python -m pytest
```

```bash
.venv/bin/uvicorn main:app --reload --app-dir backend --port 8000
```

In a second terminal:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. The API docs are at http://127.0.0.1:8000/docs.

### Modes
- `ONRECORD_MODE=keyword` (default): phrase matching. Works offline with no API key. This is the demo fallback.
- `ONRECORD_MODE=llm`: Gemini **proposes** moments and code verifies them. Needs `GEMINI_API_KEY`. Falls back to keyword mode on any error.

## Layout

```
AGENTS.md / CLAUDE.md   hard rules (identical, enforced by a test)
backend/                FastAPI, pydantic models, verifier, keyword + LLM proposers
config/topics.json      fixed criteria checklist
data/seed/              FICTIONAL sample data
docs/                   product, decisions, architecture, data format, sources, T&S, tasks, demo
frontend/               Vite + React (plain JS)
scripts/                transcript fetch (YouTube captions or .vtt/.srt files)
tests/                  pytest
```

## Data

Everything in `data/seed/` is **fictional**. Real candidates are added by hand from real public videos. Every displayed quote is checked by a person. See [docs/DATA_FORMAT.md](docs/DATA_FORMAT.md) and [docs/SOURCES.md](docs/SOURCES.md).

## Report a problem

Every card links to `POST /reports`, which writes to a local log, and to a mailto address (`ONRECORD_REPORT_EMAIL`). See [docs/TRUST_AND_SAFETY.md](docs/TRUST_AND_SAFETY.md) for what happens next.
