"""Write the API's GET responses to frontend/public/snapshot/ as static JSON.

The static (Vercel) build has no backend, so it reads these files instead (see src/api.js).
The responses come from the real FastAPI app: nothing here is hand-written.

Run from the repo root:
    ONRECORD_DATA_DIR=data/real .venv/bin/python frontend/scripts/snapshot_api.py

The site shows real data only, so snapshot data/real (not the fictional data/seed).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "public" / "snapshot"

# The snapshot is taken from the same app the hosted site runs (api/index.py). With no API key
# it never calls Gemini: it serves the committed, verified proposal caches, else keyword matches.
os.environ.pop("GEMINI_API_KEY", None)
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "api"))

from fastapi.testclient import TestClient  # noqa: E402

from index import app  # noqa: E402

client = TestClient(app)


def save(route: str) -> object:
    res = client.get("/api" + route)
    res.raise_for_status()
    path = OUT / (route.strip("/") + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res.json(), indent=1) + "\n", encoding="utf-8")
    return res.json()


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    save("/health")
    topics = save("/topics")
    candidates = save("/candidates")["candidates"]
    for c in candidates:
        for t in topics:
            save(f"/candidates/{c['candidate']['id']}/topics/{t['id']}")
    print(f"wrote {len(candidates)} candidates x {len(topics)} topics to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
