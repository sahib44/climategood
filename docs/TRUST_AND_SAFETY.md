# Trust and safety

## Misuse cases and mitigations

| Misuse | How it happens | Mitigation |
|---|---|---|
| **Cherry-picking** | A user screenshots one card to "prove" a position, ignoring others | We show **all** matches chronologically, never a "best" quote. Every card carries its date, so later statements are visible next to earlier ones. Cards include context lines. |
| **Selective curation** (by us) | Our team picks flattering or damaging videos | Same curation rules for every candidate (SOURCES.md). Coverage counts public on every page. Unevenness warning. Video list is in git: anyone can see what was searched. |
| **Context stripping** | Quote shown without the condition attached ("…if they bring clean power") | `context_before`/`context_after` on every card; one click to the full official video at that second. |
| **Edited clips / deepfakes** | Someone submits a manipulated video as a source | Official publisher sources only; never social reposts. We link to the original host, never re-host. Report-a-problem flag `edited_clip`. |
| **LLM fabrication** | Gemini invents or alters a quote or timestamp | Gemini only proposes; verifier drops anything not in the transcript and copies text and timestamps from the transcript itself. Tested. |
| **Silence read as a position** | "They never mentioned it, so they oppose it" | Empty state says only what we searched and offers a neutral question. No inference text anywhere. |
| **Election-season misuse** | Screenshots of OnRecord used in attack ads or mailers implying an endorsement/verdict | No scores or verdicts exist to screenshot. Every card shows source and date. Footer: "OnRecord does not rate or endorse candidates." Pages are reproducible from public data. |
| **Coverage asymmetry** | Incumbent has 40 hours of floor video, challenger has 2 | Per-candidate coverage + unevenness warning. Suggested question helps voters fill gaps directly. |
| **Harassment / non-public figures** | Adding private citizens who spoke at a town hall | Only declared candidates. Quotes only from the candidate; other speakers appear only as context lines. |

## When data is wrong or missing: the human process

1. **Intake.** A report arrives via `POST /reports` (stored in `data/reports/reports.jsonl`, local only) or the mailto link. No reporter identity is required or stored.
2. **Triage (within 24h during election season).** Whoever is on-call (Owner C during the hackathon) opens the cited video at the timestamp.
3. **Check against the original.** Compare the card's `quote_text` to the official video audio and the publisher's transcript.
4. **Decide and act:**
   - *Wrong words / wrong speaker:* remove the statement immediately (delete from data, commit with `fix(data): remove misattributed statement <id>`), then investigate the transcript.
   - *Wrong timestamp:* correct `start_sec` and re-run verification.
   - *Edited or non-official source:* remove the video from `videos.json`; record why in the commit.
   - *Missing statement (we missed something):* add the video if it meets SOURCES.md rules and re-run the pipeline for **all** candidates' topics affected (same treatment).
5. **Log the correction** in `docs/CORRECTIONS.md` (create on first use): date, what changed, why. Corrections are public.
6. **Never** edit a quote's text by hand to "fix" it. If the transcript is wrong, fix the transcript from the official source, then re-verify.
