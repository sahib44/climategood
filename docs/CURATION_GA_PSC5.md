# Curation log: Georgia PSC District 5 (2026)

Real data lives in `data/real/`. Run the app with `ONRECORD_DATA_DIR=data/real`.

## Why this race

Data centers and power bills were a central question in every District 5 debate, and the Atlanta Press Club recorded each debate in full, with closed captions. PSC seats are elected statewide.

Edwards (D) won the general election on 2026-11-03. That outcome doesn't affect what we show: the app shows only what each candidate said on the record.

## Candidates (2 D, 2 R)

| id | Name | Party | Debates |
|---|---|---|---|
| shelia-edwards | Shelia Edwards | Democratic | Dem primary, general |
| angelia-pressley | Angelia Pressley | Democratic | Dem primary |
| josh-tolbert | Josh Tolbert | Republican | GOP primary, GOP runoff, general |
| bobby-mehan | Bobby Mehan | Republican | GOP primary, GOP runoff |

These are not included yet. Each would be a one-line add, since they appear in debates we already list:
- Craig Cupid (D), in the Dem primary debate
- Carolyn Roddy (R), in the GOP primary debate
- Thomas Blooming (L), who was on the general ballot for a time. We found no debate video for him.

Coverage is uneven: Tolbert appears in 3 videos and Pressley in 1. The app's unevenness warning will show, and that is intended.

## Videos (official publisher only)

Every video is from the Atlanta Press Club Loudermilk-Young Debate Series. GPB presents it and PBS streams it. All four debates were taped at the GPB studios in Atlanta.

| Debate | Published | Duration | Candidates | PBS URL | Transcript file |
|---|---|---|---|---|---|
| Dem primary | 2026-04-28 | 27:17 (1637 s) | Edwards, Pressley (and Cupid) | https://www.pbs.org/video/georgia-psc-district-5-democrats-atlanta-press-club-debate-wcvb65/ | `data/transcripts/ga-psc5-dem-primary.json` |
| GOP primary | 2026-04-28 | 26:47 (1607 s) | Tolbert, Mehan (and Roddy) | https://www.pbs.org/video/georgia-district-5-republicans-atlanta-press-club-debate-lzjm6s/ | `data/transcripts/ga-psc5-gop-primary.json` |
| GOP runoff | 2026-05-31 | 27:19 (1639 s) | Tolbert, Mehan | https://www.pbs.org/video/georgia-psc-district-5-republicans-i-atlanta-press-club-debates-fwtu5x/ | `data/transcripts/ga-psc5-gop-runoff.json` |
| General | 2026-10-12 | 26:47 (1607 s) | Edwards, Tolbert | https://www.pbs.org/video/public-service-commission-district-5-i-atlanta-press-club-debate-9swviv/ | `data/transcripts/ga-psc5-general.json` |

The title, date and duration of each video were copied from its PBS page on 2026-11-21. `transcript_source` is set to `official_captions` because each PBS page lists closed captions supplied by the publisher.

## Open items

- [ ] **Fetch the transcripts (A).** These are PBS pages, not YouTube, so `fetch_transcript.py` can't fetch them from the URL alone. APC also posts the debates on its YouTube Debate channel. If you find the matching uploads, put their URLs in place of these and run `python scripts/fetch_transcript.py <id> --out data/transcripts/ga-psc5-<debate>.json`. Otherwise, save the publisher's caption file and run `--file <captions.vtt> --source official_captions`. Each debate needs only one transcript file, which its candidate entries share.
- [ ] **Speaker attribution (A + C).** Each transcript contains several candidates and the moderators, and `verify.py` checks the words, not who said them. Before a card goes live, a person confirms on the video that the quote is the card's candidate speaking and not an opponent or a moderator. The code may need a speaker-range filter.
- [ ] **Check the terms (C).** Confirm the PBS/GPB embed and link terms before the demo, and record who checked them and when, here and in the PR.
- [ ] **Check the dates (C).** One AJC photo caption dates a GOP primary debate to 2026-03-31, while PBS lists 2026-04-28. Keep the PBS date unless the video shows otherwise.
- [ ] **Check the durations (C).** The GOP primary and the general debate both show 26:47 on PBS. Confirm both in the player.
- [ ] **Hand-verify every displayed quote** against the video. A second person re-checks.

No quotes from real people are written anywhere in this repo. Every quote comes from the official transcript and is checked by a person.
