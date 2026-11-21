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
