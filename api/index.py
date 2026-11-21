"""Vercel entry point: serves the FastAPI backend at /api/* next to the static frontend.

The backend itself is unchanged (backend/main.py). This file only mounts it under /api, so the
site and the API share one origin and no CORS setup is needed. See vercel.json.

Hosted limits, on purpose:
- Keyword (no-LLM) mode unless ONRECORD_MODE and GEMINI_API_KEY are set on the Vercel project.
- POST /reports is refused: the hosted filesystem is read-only and temporary, so a report
  written there would be lost while the voter is told it was received. The site shows the
  "report a problem" email link instead (rule 9 keeps a working report path).
"""
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app as backend  # noqa: E402

app = FastAPI(title="Firsthand (hosted)", docs_url=None, redoc_url=None, openapi_url=None)


@app.post("/api/reports")
def reports_not_hosted():
    raise HTTPException(501, "Reports are not stored on the hosted site. Use the email link.")


app.mount("/api", backend)
