"""Rule 1: no score, rating, or ranking anywhere in the API. Fails if one is added."""
import re

from fastapi.testclient import TestClient

import main
import models

FORBIDDEN = re.compile(r"(score|rating|rank|grade|stance|verdict|alignment|percent_aligned|best)", re.I)

client = TestClient(main.app)


def _keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{path}.{k}", k
            yield from _keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v, path)


def _all_api_payloads():
    yield client.get("/health").json()
    yield client.get("/topics").json()
    cands = client.get("/candidates").json()
    yield cands
    for c in cands["candidates"]:
        for t in client.get("/topics").json():
            yield client.get(f"/candidates/{c['candidate']['id']}/topics/{t['id']}").json()
    yield client.post("/verify", json={"video_id": "fv-vale-townhall", "quote_text": "made up words here today"}).json()


def test_api_output_has_no_score_rating_or_ranking_field():
    bad = [path for payload in _all_api_payloads() for path, k in _keys(payload) if FORBIDDEN.search(k)]
    assert bad == [], f"Forbidden judgement fields in API output: {bad}"


def test_models_have_no_score_rating_or_ranking_field():
    bad = []
    for name in dir(models):
        cls = getattr(models, name)
        if isinstance(cls, type) and issubclass(cls, models.BaseModel) and cls is not models.BaseModel:
            bad += [f"{name}.{f}" for f in cls.model_fields if FORBIDDEN.search(f)]
    assert bad == []


def test_openapi_schema_has_no_score_fields():
    props = []

    def walk(o):
        if isinstance(o, dict):
            props.extend(o.get("properties", {}).keys())
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(main.app.openapi())
    assert [p for p in props if FORBIDDEN.search(p)] == []
