"""Vercel entry point: serves the FastAPI backend at /api/* next to the static frontend.

The backend itself is unchanged (backend/main.py). This file only mounts it under /api, so the
site and the API share one origin and no CORS setup is needed. See vercel.json.

Hosted limits, on purpose:
- Data is data/real. A candidate's videos count as searched only once their transcripts are in
  the deployed files; until then the API truthfully reports 0 videos searched.
- Keyword (no-LLM) mode unless ONRECORD_MODE and GEMINI_API_KEY are set on the Vercel project.
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

from main import app as backend  # noqa: E402

app = FastAPI(title="Firsthand (hosted)", docs_url=None, redoc_url=None, openapi_url=None)


@app.post("/api/reports")
def reports_not_hosted():
    raise HTTPException(501, "Reports are not stored on the hosted site. Use the email link.")


app.mount("/api", backend)
