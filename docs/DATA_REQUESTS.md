# Data requests (ingest -> backend schema)

Proposed changes to `backend/models.py` for the backend owner (Abhi). Until they land, ingest keeps these fields in its own files (`data/ingest/approved/<candidate_id>/<video_id>.json`, model `ingest/models.py:ProposedItem`) and writes only the current schema to `data/real/`.

## 1. Provenance fields on `Video` (all optional, so seed data still loads)
| field | type | why |
|---|---|---|
| `listing_page_url` | str | the official page the video was found on, so anyone can retrace it |
| `fetched_at` | datetime | when we saw it; old finds can be re-checked |
| `reviewed_by` | str | the person who approved it (rule: every real item is human-verified) |
| `reviewed_at` | datetime | when it was approved |
| `archive_capture_date` | date or null | for Wayback copies of past campaign sites; shown in the attribution line |
| `lower_confidence` | bool | true for `platform_auto_captions`; the UI could show "auto-captions, lower confidence" |

Not requested: `browserbase_session_id` and `screenshot_path` are internal evidence and stay in `data/ingest/`.

## 2. Coverage: "unavailable" videos
Approved videos with no official transcript are not in `data/real/videos.json`, so the backend never counts them as searched. `data/ingest/coverage.json` counts them per candidate as `videos_unavailable_no_transcript`. If you want the UI to say "8 videos searched, 2 more found but without captions", the API's `Coverage` would need an optional `videos_unavailable: int` (label `measured`). Ingest can provide it.

## 3. Transcript paths
`data/real/videos.json` uses `transcript_path: "../transcripts/<video_id>.json"`, the same place `scripts/fetch_transcript.py` writes. That folder is gitignored, so each machine that runs the demo must fetch transcripts first. Tell us if you'd rather commit transcripts for `data/real/` instead.

## 4. Venue may be "Not stated by the publisher"
Many broadcaster and campaign uploads never say where the candidate was speaking. Ingest no longer guesses: an approved video with no stated venue gets `venue: "Not stated by the publisher"`. The frontend (Bill) may want to show that in a muted style rather than as a place name. `published_date` for YouTube videos is the upload date in the candidate's state time zone (from the YouTube Data API).
