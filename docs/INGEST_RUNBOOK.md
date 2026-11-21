# Ingest runbook

The ingest job finds official videos for a fixed list of past-election candidates. It is an offline batch job; nothing in it runs when a voter uses the site. Every item it finds stays in a "proposed" state until a person approves it. Only approved items with an official transcript reach `data/real/`, which the backend reads with `ONRECORD_DATA_DIR=data/real`.

```
config/candidates.json ─► collect ─► data/ingest/proposed ─► review (a person) ─► data/real/videos.json
     (a person picks)     │                                    │
                          ├─► blocked / not scrapable ─► manual_queue.csv ─► import_manual ─┘
                          └─► every drop logged in data/ingest/log.jsonl, counted in coverage.json
```

## One-time setup

1. Install the ingest dependencies. No local browser is needed: Playwright connects to Browserbase's remote browser.

```bash
.venv/bin/pip install -r ingest/requirements.txt
```

2. Put `BROWSERBASE_API_KEY` and `BROWSERBASE_PROJECT_ID` in `.env`. Never commit them.
3. Fill in `config/candidates.json` from `config/candidates.example.json`. A person applies the selection rule: 3 completed races at the same office level, 2 candidates per race from different parties, both winners and losers. The script never picks people.
4. For each listing URL, check that its domain is in `config/sources.json` with dated robots.txt and terms checks. If it isn't, check it and add it (see docs/SOURCES.md) before running.

## Collect

Always dry-run first. It uses no network, opens no session, and writes nothing:

```bash
.venv/bin/python -m ingest.collect --dry-run
```

Each listing URL shows one of these actions:
- `fetch`: Browserbase will load it.
- `manual`: we may link to it but not scrape it (for example YouTube), so it goes to the manual CSV.
- `refuse`: not allowed (social media, or robots.txt and terms not checked yet).
- `skip`: a placeholder value, or already done.

Then run one candidate at a time:

```bash
.venv/bin/python -m ingest.collect --candidate <candidate_id>
```

The free Browserbase plan gives about 1 browser hour in total. The job:
- Opens one session per candidate. Each session is capped at 14 minutes and released by our timer even if a page hangs.
- Stops before starting a session if less than 3 minutes of the budget is left (`--budget-minutes`, default 55).
- Records progress in `data/ingest/progress.json`. Re-running skips listings that are done or blocked, so a crash never re-spends minutes. `--force` re-runs them.

The same steps run for every candidate: allowlist check, block check, screenshot (local evidence only), deterministic extraction (no LLM, so page text can't act as an instruction), required date and publisher, the format filter on the title (switched off since 2026-11-21, so campaign videos count too; see `ingest/settings.json`), the campaign period, and then the cap. Manual CSV rows get exactly the same checks. The cap is 12 per candidate, newest first, with no per-candidate override.

## Review

```bash
.venv/bin/python -m ingest.review --reviewer "<your name>"
```

For each item, open the video URL and check the speaker, date, publisher and venue against the official page. Then choose one:
- **approve**: you'll be asked for the venue and duration if they're missing. Your name and the time are recorded.
- **reject**: give a reason. The item moves to `data/ingest/rejected/`.
- **needs fix**: give a reason. The item stays in the queue.

After each session, the review tool rebuilds `data/real/` and `data/ingest/coverage.json`.

Then fetch an official transcript for each approved video, and publish again:

```bash
.venv/bin/python scripts/fetch_transcript.py <video_id> --url <video_url>
```

```bash
.venv/bin/python -m ingest.review --publish
```

Then run the pipeline and **watch every displayed clip at its timestamp**; a second person re-checks it (docs/DATA_FORMAT.md, "Adding real data").

## Manual CSV fallback

Use the manual CSV for anything in `data/ingest/manual_queue.csv`, any site whose terms forbid scraping, and any item that `collect` rejected as incomplete (see `data/ingest/rejected/<candidate_id>/incomplete-*.json` for the URL it found).

Start from what collect already found: this pre-fills one row per incomplete find (URL, title as found, listing page) and leaves every fact blank for a person to copy from the official video page. Re-running never overwrites rows you've filled.

```bash
.venv/bin/python -m ingest.prefill_manual --oembed
```

`--oembed` also fills each YouTube row's title and publisher (the uploading channel) from YouTube's public oEmbed endpoint and flags unavailable videos. Dates, venue and duration are always left for a person.

Then fill upload dates and durations from the official YouTube Data API (needs `YOUTUBE_API_KEY` in `.env`; 3 requests for about 120 rows):

```bash
.venv/bin/python -m ingest.youtube_metadata
```

Dates are the upload date in the candidate's state time zone. Venue is never filled automatically: if the video doesn't say where it was recorded, leave it blank and approval records "Not stated by the publisher".

For videos collect didn't find (debates on a broadcaster's channel, for example), add rows by hand. To start an empty file instead:

```bash
cp ingest/manual_template.csv data/ingest/manual_rows.csv
```

Fill in one row per video: link and metadata only, never a video file. `added_by` is required. Then import the rows:

```bash
.venv/bin/python -m ingest.import_manual data/ingest/manual_rows.csv
```

Rows get the same allowlist check, required fields, campaign period and cap, and then go through the same review step.

## Re-check links

```bash
.venv/bin/python -m ingest.verify_links
```

It flags approved items whose link no longer loads, whose date changed, or whose domain left the allowlist. It writes `data/ingest/link_check.json` and exits 1 if anything is flagged. A flagged item is handled like a problem report (docs/TRUST_AND_SAFETY.md): check the original, then fix or remove it, and log the change in docs/CORRECTIONS.md.

## When things go wrong

| Situation | What to do |
|---|---|
| A site blocks us, or shows a CAPTCHA or login wall | The job logs it, puts the URL in `manual_queue.csv` and moves on. **Do not** retry with other settings, proxies or stealth. A person adds its videos by manual CSV if its terms allow linking. |
| A video is private or removed | Reject it with the reason "private" or "removed". It's counted as rejected in coverage. |
| No official captions or transcript | Approve the video if it is otherwise correct. It is marked `no_transcript`, counted as **unavailable** in coverage, and not searched. **Never** generate a transcript with an LLM. A person may hand-transcribe a passage (`transcript_source: hand_transcribed`) only if a second person checks it against the video. |
| Only platform auto-captions | Fetch them with `--allow-auto`. They're marked lower confidence; hand-check every quote shown from them. |
| Campaign site from a past election is offline | Use its Internet Archive copy (`web.archive.org/web/<timestamp>/<url>`). The capture date is part of the attribution. |
| The budget ran out mid-run | Re-run later with a fresh budget, or a higher `--budget-minutes` if minutes remain. Progress resumes where it stopped. |
| Coverage is very uneven between candidates | Don't fix it by dropping videos. Show it: the backend's unevenness warning and the suggested question exist for this. |

## What gets committed

Committed: `data/real/`, `data/ingest/approved/`, `data/ingest/coverage.json`, and any change to `config/` (in its own reviewed commit).

Never committed (gitignored): `.env`, `data/transcripts/`, `data/ingest/{evidence,proposed,rejected}/`, `log.jsonl`, `progress.json`, `manual_queue.csv`, `link_check.json`, `manual_rows.csv`.
