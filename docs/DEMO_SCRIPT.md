# Demo script (3:00)

Setup before going on: backend running in **keyword mode** with real data (`ONRECORD_DATA_DIR=data/real`), frontend open, a second tab ready on `/verify` demo, fabricated quote pasted in clipboard.

| Time | Beat | What to say / do |
|---|---|---|
| 0:00–0:30 | **The voter and the before** | "Meet a voter in [county] who keeps hearing every candidate say they're 'for clean energy'. A data center is proposed near their town. To find out what candidates actually committed to, they'd scroll campaign sites, read paraphrases in the news, and scrub through 90-minute debate videos — for every candidate. Most people give up." |
| 0:30–1:05 | **Search a candidate** | Pick Candidate 1 → topic "Protects ratepayers from data center costs". Point at: verbatim quote, the line before and after, date · venue · publisher, "Watch at 41:12" opens the official video at that second. Point at coverage: "8 videos, 11.5 hours searched." Point at labels: quote = measured, topic match = modeled. |
| 1:05–1:30 | **Same format, other party** | Switch to Candidate 2 (other party), same topic. "Identical layout, same pipeline, no score, no color. We show *all* matches in date order — we don't pick the best one." |
| 1:30–1:55 | **No statement found** | Candidate 3, topic "Water and energy use disclosure". "No statement found in the 4 videos we searched" + the suggested question. "Silence isn't a position. We tell you what we searched and what you could ask." Point at the unevenness warning if shown. |
| 1:55–2:25 | **Fabricated quote rejected, live** | Using the FICTIONAL seed candidate (say so on stage; never invent words for a real person), paste a fabricated quote, then a one-word negation flip of a real seed line ("would not support" → "would support"), into the verify box. It's **rejected**; show the reason. "Gemini can only *propose* moments. Our code checks every word against the official transcript and drops anything that isn't there. The text you see is copied from the transcript, never from the AI." |
| 2:25–3:00 | **Limits and humans** | "Limits: we only see videos we've curated, captions can be wrong, and coverage is uneven — so we show coverage. Every card has 'Report a problem'; a human checks the original video, fixes or removes it, and logs the correction publicly. No accounts, no tracking. Thanks." |

## Fallbacks
- Gemini down / quota out → already in keyword mode; nothing changes on screen.
- Wi-Fi down → backend + frontend are local; video links won't open, so have one screenshot of the official player at the timestamp.
- Never demo with fictional seed data presented as real. If showing seed data, say "fictional placeholder data".
