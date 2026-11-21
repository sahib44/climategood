# Sources and usage rules

**Rule zero: link only.** We store metadata and transcript text needed for verification. We never download, re-host, re-encode, or clip video. Playback always happens in the publisher's own player (embed or link at a timestamp).

**Every source must be checked by a human before it is added.** The notes below are starting points, not legal advice, and terms change. Record who checked it and when in `videos.json` (`transcript_source` + a note in the PR).

| Source type | Examples | Transcript source | Usage notes (verify before use) |
|---|---|---|---|
| C-SPAN | Debates, floor speeches, hearings | C-SPAN's published captions/transcripts | C-SPAN's video library policy has historically allowed **non-commercial** use with **attribution**. **This must be verified at c-span.org before use** (check current terms for the specific content). Link to c-span.org at the timestamp. |
| Official government video | Legislature/council floor sessions, public hearings | Official captions or minutes | Generally public record, but host sites (e.g., Granicus) have their own terms. Link only. |
| Campaign channels | Candidate's official YouTube, campaign site videos | YouTube official/creator captions | Campaign content: owned by the campaign, governed by the platform's ToS. Embed via the platform's official embed player only. Prefer creator-uploaded captions over auto-captions; note which in `transcript_source`. |
| News / debate broadcasters | Local TV debates, newspaper-hosted forums | Publisher transcript or captions | Copyrighted by the publisher. Link/embed only; quote short excerpts. Check each outlet's embed policy. |
| Local events | Town halls, forums by civic groups, local access TV | Organizer-provided captions/transcript | Rules vary per organizer. Get permission if terms are unclear. If no official transcript exists, a human may hand-transcribe the relevant passage (`transcript_source: hand_transcribed`) and a second person checks it against the video. |
| Social media clips | Short reposts, excerpts | — | **Not accepted** as a source. Too easy to edit or strip context. Find the full original instead. |

## Transcript provenance values

`transcript_source` must be one of:
- `official_captions`: captions uploaded by the publisher
- `publisher_transcript`: a transcript document published by the publisher
- `platform_auto_captions`: platform auto-captions (allowed, but flagged in the UI as lower confidence; prefer to hand-check every displayed quote)
- `hand_transcribed`: typed by a team member from the official video, checked by a second person
- `fictional`: seed data only

**Never** `llm_generated`. See DECISIONS.md D4.

## Gemini and data

Only public transcripts of public statements are sent to Gemini. Per Google's terms at time of writing, free-tier inputs may be used to improve Google's products (verify current terms), so never send anything non-public (internal notes, reports from users, unreleased material).

## Ingest allowlist: checks on record

`config/sources.json` is the allowlist, and `ingest/allowlist.py` enforces it in code. A domain is usable only after a person (or an agent, confirmed by a person) has checked **both** robots.txt and the terms, and dated both. Each domain has two separate permissions:
- `automated_fetch`: Browserbase may load its pages (`ingest/collect.py`).
- `link_ok`: we may store links to its videos and play them in its own player (manual CSV adds need this).

Social media domains are refused in code whatever the config says. What we take from every source is the same: page metadata (title, date, publisher, URL) and published captions or transcripts. We never take video or audio. Screenshots of listing pages are local review evidence only (`data/ingest/evidence/`, gitignored) and are never published.

| Source | robots.txt (checked 2026-11-21) | Terms (checked 2026-11-21) | What we do | Attribution shown |
|---|---|---|---|---|
| Internet Archive Wayback Machine (`web.archive.org`) | web.archive.org serves no robots.txt (404). archive.org/robots.txt disallows only `/control/` and `/report/`. | [archive.org/about/terms](https://archive.org/about/terms): access is for scholarship and research; do not interfere with servers or resources; use must be noninfringing or fair use; cite the Archive. No clause against automated access. | `automated_fetch` and `link_ok`. One page at a time, no parallel load. Record the capture date from the archive URL. | "Archived copy from the Internet Archive Wayback Machine, captured {date}." |
| YouTube (`youtube.com`, `youtu.be`) | Disallows `/results`, `/api/`, `/youtubei/`, `/timedtext_video` and others for all agents. | [youtube.com/t/terms](https://www.youtube.com/t/terms) (dated 2023-12-15): no access by automated means (robots, scrapers) except search engines or with written permission. Videos may be shown through the embeddable player. | `link_ok` only. **Never scraped.** Channel pages go to the manual CSV. Clips play through the official embed at a timestamp. Link re-checks use YouTube's public oEmbed endpoint. | "Video published by {publisher} on YouTube, {date}." |
| C-SPAN (`c-span.org`) | Disallows **everything** for named AI agents (ClaudeBot, anthropic-ai, GPTBot, CCBot and others). | **Not verified.** The terms page returned HTTP 403 to both our fetcher and the in-app browser. | **Not usable yet** (`link_ok` false, no terms date). A person must read the terms in their own browser, record them here and in `config/sources.json`, and then add videos only by manual CSV. Never automated. | "Video from C-SPAN, {date}." (once allowed) |

**News broadcasters' YouTube uploads** (added 2026-11-21) are covered by the YouTube row: link-only, played in YouTube's embed player, which respects each uploader's embed setting. The publisher shown is the uploading station or paper (from YouTube's public oEmbed endpoint, confirmed by a person). Only news organizations count; independent creators, talk/opinion shows and re-uploads do not. The exact search method is recorded in `config/candidates.json` under `broadcaster_search`.

**Past-election campaign sites** are often offline. Use the Internet Archive copy, and give the `web.archive.org/web/<timestamp>/<original URL>` form in `config/candidates.json`. The timestamp in the URL is the capture date we show. Live campaign sites and legislature or government video archives are added per candidate: check that exact domain's robots.txt and terms, add a row above and an entry in `config/sources.json`, then run the job. If a site forbids scraping, set `automated_fetch: false` and add its videos through `ingest/manual_template.csv` (link and metadata only).

**Open question (not ingest's code):** `scripts/fetch_transcript.py` reads YouTube caption tracks with `youtube-transcript-api`, which is automated access to YouTube. Given the terms above, the team should decide whether to keep that, or have a person download the publisher's caption file (.vtt/.srt) from the video page and use `--file`.
