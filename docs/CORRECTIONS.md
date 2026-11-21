# Corrections

This is the public log of every change we make to displayed data after a report or our own re-check. The process is in docs/TRUST_AND_SAFETY.md. Add new entries at the top. Never delete an entry.

Rules:
- Never edit a quote's text by hand. If the transcript is wrong, fix the transcript from the official source and run verification again.
- A wrong-words or wrong-speaker report means the statement is removed first and investigated second.
- If we add a missed video, run the pipeline again for every candidate on the affected topics, not just one.

## Entry template

```
### YYYY-MM-DD: <short title>
- Statement or video: <statement id, or video id>
- Candidate: <candidate id>
- Reported by: report form | email | team re-check   (no reporter identity is stored)
- Problem: wrong words | wrong speaker | wrong timestamp | edited or non-official source | missed statement | other
- What we checked: <official video URL at the timestamp, publisher transcript>
- What changed: <removed statement / corrected start_sec / removed video / added video and re-ran topics ...>
- Commit: <hash>
- Checked by: <first person>, re-checked by: <second person>
```

## Log

No corrections yet.
