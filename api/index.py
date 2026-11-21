"""Vercel entry point: serves the FastAPI backend at /api/* next to the static frontend.

The backend itself is unchanged (backend/main.py). This file only mounts it under /api, so the
site and the API share one origin and no CORS setup is needed. See vercel.json.

Hosted limits, on purpose:
- Data is data/real. A candidate's videos count as searched only once their transcripts are in
  the deployed files; until then the API truthfully reports 0 videos searched.
- Gemini is never called unless GEMINI_API_KEY is set on the Vercel project. Without a key the
  API serves the committed, already-verified Gemini proposals (data/transcripts/*.proposals.json)
  and uses keyword matching for any video that has no cached proposals.
- POST /reports is refused: the hosted filesystem is read-only and temporary, so a report
  written there would be lost while the voter is told it was received. The site shows the
  "report a problem" email link instead (rule 9 keeps a working report path).
"""
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
# The hosted site shows the real, human-approved data (data/real), never the fictional seed set.
os.environ.setdefault("ONRECORD_DATA_DIR", "data/real")

os.environ.setdefault("ONRECORD_MODE", "llm")
# A placeholder address on a reserved domain (.example can never be registered), so a report
# sent from the demo cannot reach a stranger. Set ONRECORD_REPORT_EMAIL on Vercel for a real inbox.
os.environ.setdefault("ONRECORD_REPORT_EMAIL", "reports@firsthand.example")

import llm  # noqa: E402


class CachedOnlyProposer:
    """Stands in for Gemini when there is no API key. The proposal cache answers for every video
    it has; for any other video this raises, and the pipeline falls back to keyword matching.
    The name and model match the real proposer so the committed caches are recognised."""
    name = "gemini"
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    def propose(self, video_id, segments, topics):
        raise RuntimeError("no GEMINI_API_KEY on the hosted site and no cached proposals for this video")


if not os.getenv("GEMINI_API_KEY"):
    llm.get_proposer = CachedOnlyProposer

from main import app as backend  # noqa: E402

app = FastAPI(title="Firsthand (hosted)", docs_url=None, redoc_url=None, openapi_url=None)


@app.post("/api/reports")
def reports_not_hosted():
    raise HTTPException(501, "Reports are not stored on the hosted site. Use the email link.")


app.mount("/api", backend)
