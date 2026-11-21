import pytest

import storage


@pytest.fixture(autouse=True)
def seed_data(monkeypatch):
    """All tests run against the FICTIONAL seed data in keyword mode."""
    monkeypatch.setenv("ONRECORD_DATA_DIR", "data/seed")
    monkeypatch.setenv("ONRECORD_MODE", "keyword")


@pytest.fixture
def candidates():
    return storage.load_candidates()


@pytest.fixture
def videos():
    return storage.load_videos()


@pytest.fixture
def topics():
    return {t.id: t for t in storage.load_topics()}


@pytest.fixture
def transcript():
    def _get(video_id):
        v = next(v for v in storage.load_videos() if v.id == video_id)
        return storage.load_transcript(v).segments
    return _get
