import json

from fastapi.testclient import TestClient

import config
import main

client = TestClient(main.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["mode"] == "keyword"


def test_candidates_include_coverage():
    body = client.get("/candidates").json()
    assert len(body["candidates"]) == 3
    for c in body["candidates"]:
        assert c["coverage"]["videos_searched"] >= 1
        assert c["coverage"]["label"] == "measured"
    assert body["unevenness_warning"]


def test_verify_endpoint_rejects_fabricated_and_accepts_real():
    fake = client.post("/verify", json={"video_id": "fv-morrow-forum",
                                        "quote_text": "I promise to shut down every data center"}).json()
    assert fake["verified"] is False
    real = client.post("/verify", json={"video_id": "fv-morrow-forum",
                                        "quote_text": "I would oppose a moratorium because it sends the wrong signal"}).json()
    assert real["verified"] is True and real["start_sec"] == 610.0


def test_unknown_candidate_404():
    assert client.get("/candidates/nobody/topics/moratorium").status_code == 404


def test_report_problem_writes_local_log_without_user_data(tmp_path, monkeypatch):
    path = tmp_path / "reports.jsonl"
    monkeypatch.setattr(config, "REPORTS_PATH", path)
    r = client.post("/reports", json={"problem_type": "wrong_timestamp", "statement_id": "x", "details": "off by 10s"})
    assert r.status_code == 200
    entry = json.loads(path.read_text().strip())
    assert set(entry) == {"received_at", "problem_type", "statement_id", "candidate_id", "details"}
