import json

import config


def test_agents_and_claude_md_are_identical():
    a = (config.REPO_ROOT / "AGENTS.md").read_text()
    c = (config.REPO_ROOT / "CLAUDE.md").read_text()
    assert a == c, "AGENTS.md and CLAUDE.md must have the same content"


def test_seed_data_is_marked_fictional():
    seed = config.REPO_ROOT / "data" / "seed"
    for c in json.loads((seed / "candidates.json").read_text())["candidates"]:
        assert c["fictional"] is True and "FICTIONAL" in c["name"]
    for v in json.loads((seed / "videos.json").read_text())["videos"]:
        assert v["fictional"] is True and v["transcript_source"] == "fictional"
        assert v["url"].startswith("https://example.org/")


def test_no_llm_generated_transcript_source_allowed():
    import models
    allowed = models.TranscriptSource.__args__
    assert not any("llm" in s or "gemini" in s or "generated" in s for s in allowed)


def test_env_is_gitignored():
    ignore = (config.REPO_ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in ignore
    # Real transcripts are committed (demo never re-fetches from YouTube); local Gemini caches are not.
    assert "data/transcripts/*.proposals.json" in ignore
