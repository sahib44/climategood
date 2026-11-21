"""Ingest job tests. No network: Browserbase, Playwright and HTTP are all faked.

All candidates, channels and videos here are FICTIONAL.
"""
from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from ingest import collect, review
from ingest.allowlist import Allowlist, NotAllowed
from ingest.browserbase_client import BrowserbaseClient
from ingest.common import REPO_ROOT, Paths, load_candidates, read_json, write_json
from ingest.coverage import compute_coverage
from ingest.extract import extract_listing
from ingest.import_manual import import_rows
from ingest.selection import apply_cap, cap_for
from ingest.store import load_incomplete, load_items, validate_item

FIX = Path(__file__).parent / "fixtures" / "ingest"
LISTING = "https://web.archive.org/web/20221101000000/https://example-campaign.org/videos"
FETCHED = datetime(2026, 11, 21, tzinfo=timezone.utc)


def _cand(cid, name):
    return {"id": cid, "name": f"{name} (FICTIONAL)", "party": "Example Party", "result": "won",
            "campaign_period": {"start": "2022-01-01", "end": "2022-11-08"}, "sources": [LISTING]}


@pytest.fixture()
def env(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "ingest").mkdir()
    shutil.copy(REPO_ROOT / "config" / "sources.json", tmp_path / "config" / "sources.json")
    settings = read_json(REPO_ROOT / "ingest" / "settings.json")
    settings["relevance"]["enabled"] = True  # exercise the filter here; the repo setting is tested separately
    write_json(tmp_path / "ingest" / "settings.json", settings)
    write_json(tmp_path / "config" / "candidates.json", {"races": [{
        "race_id": "ex-99-2022", "office": "State Senate (FICTIONAL)", "jurisdiction": "Example State",
        "election_date": "2022-11-08",
        "candidates": [_cand("fictional-a", "Alex Example"), _cand("fictional-b", "Blair Example")]}]})
    paths = Paths(root=tmp_path)
    return SimpleNamespace(paths=paths, allow=Allowlist.load(paths.sources), settings=read_json(paths.settings),
                           candidates=load_candidates(paths.candidates))


def _process(env, html, cid="fictional-a"):
    cand = next(c for c in env.candidates if c["id"] == cid)
    return collect.process_listing(env.paths, env.allow, env.settings, cand, LISTING, html,
                                   fetched_at=FETCHED, session_id="sess-test", screenshot_path=None)


def _snapshot(paths):
    return sorted(json.dumps({k: v for k, v in i.model_dump(mode="json").items() if k != "fetched_at"}, sort_keys=True)
                  for i in load_items(paths))


def _write_transcript(paths, video_id, source="official_captions"):
    write_json(paths.transcripts / f"{video_id}.json", {"video_id": video_id, "transcript_source": source,
               "segments": [{"start": 0.0, "end": 5.0, "text": "fictional caption text for a test"}]})


# ---------- allowlist ----------

@pytest.mark.parametrize("url", [
    "https://evil.example/watch?v=AAAAAAAAAA9",
    "https://youtube.com.evil.example/watch?v=AAAAAAAAAA9",
    "https://www.facebook.com/x/videos/1",
    "https://web.archive.org/web/2022/https://www.tiktok.com/@x/video/1",
    "ftp://youtube.com/watch?v=AAAAAAAAAA1",
    "https://user:pw@www.youtube.com/watch?v=AAAAAAAAAA1",
])
def test_allowlist_blocks_other_domains(env, url):
    with pytest.raises(NotAllowed):
        env.allow.require(url, "link_ok")


def test_allowlist_permissions_follow_the_checked_terms(env):
    assert env.allow.allows("https://www.youtube.com/watch?v=AAAAAAAAAA1", "link_ok")
    assert not env.allow.allows("https://www.youtube.com/@example/videos", "automated_fetch")  # ToS: no bots
    assert env.allow.allows(LISTING, "automated_fetch")
    assert not env.allow.allows("https://www.c-span.org/video/?123", "link_ok")  # terms not verified yet


def test_social_media_refused_even_if_config_lists_it(env):
    cfg = read_json(env.paths.sources)
    cfg["sources"].append({"domain": "facebook.com", "source_type": "x", "automated_fetch": True, "link_ok": True,
                           "robots_checked_on": "2026-01-01", "terms_checked_on": "2026-01-01"})
    write_json(env.paths.sources, cfg)
    with pytest.raises(NotAllowed):
        Allowlist.load(env.paths.sources).require("https://www.facebook.com/x/videos/1", "link_ok")


# ---------- required fields ----------

@pytest.mark.parametrize("missing", ["published_date", "publisher"])
def test_items_missing_date_or_publisher_are_rejected(missing):
    data = {"video_id": "v", "candidate_id": "c", "video_url": "https://www.youtube.com/watch?v=AAAAAAAAAA1",
            "title": "Forum (FICTIONAL)", "publisher": "Example (fictional)", "published_date": "2022-09-14",
            "listing_page_url": LISTING, "source_type": "campaign_site_archive", "origin": "browserbase",
            "fetched_at": FETCHED}
    data[missing] = None
    item, reasons = validate_item(data)
    assert item is None and any(missing.split("_")[-1] in r for r in reasons)


def test_collection_on_fixture_keeps_only_complete_relevant_items(env):
    counts = _process(env, (FIX / "listing_clean.html").read_text())
    assert counts == {"found": 4, "not_allowlisted": 0, "incomplete": 1, "filtered_out": 1,
                      "out_of_period": 0, "over_cap": 0, "proposed": 2, "already_known": 0}
    items = load_items(env.paths, "fictional-a")
    assert {i.status for i in items} == {"proposed"}
    assert {i.video_url for i in items} == {"https://www.youtube.com/watch?v=AAAAAAAAAA1",
                                           "https://www.youtube.com/watch?v=AAAAAAAAAA2"}
    assert all(i.browserbase_session_id == "sess-test" and i.listing_page_url == LISTING for i in items)
    assert load_incomplete(env.paths, "fictional-a")[0]["reasons"] == ["missing date", "missing publisher"]


# ---------- prompt injection ----------

def test_injection_fixture_does_not_change_extraction(env, tmp_path):
    clean, injected = (FIX / "listing_clean.html").read_text(), (FIX / "listing_injected.html").read_text()
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in injected

    def allowed(found):
        return [f for f in found if env.allow.allows(f["video_url"], "link_ok")]

    assert allowed(extract_listing(injected, LISTING)) == allowed(extract_listing(clean, LISTING))

    _process(env, clean)
    other = Paths(root=tmp_path / "other")
    shutil.copytree(env.paths.root / "config", other.root / "config")
    shutil.copytree(env.paths.root / "ingest", other.root / "ingest")
    collect.process_listing(other, env.allow, env.settings, env.candidates[0], LISTING, injected,
                            fetched_at=FETCHED, session_id="sess-test", screenshot_path=None)
    assert _snapshot(other) == _snapshot(env.paths)
    assert all(i.status == "proposed" and "Official" not in i.publisher for i in load_items(other))


# ---------- cap ----------

def test_per_candidate_cap_is_the_same_for_everyone(env):
    greedy = {**env.candidates[0], "cap": 500, "per_candidate_cap": 500}
    assert cap_for(greedy, env.settings) == cap_for(env.candidates[1], env.settings) == env.settings["per_candidate_cap"]
    items = [{"published_date": f"2022-{m:02d}-01", "video_url": f"https://www.youtube.com/watch?v=AAAAAAAAA{m:02d}"}
             for m in range(1, 13)] * 2
    items = [{**it, "video_url": it["video_url"] + str(n)} for n, it in enumerate(items)]
    kept_a, over_a = apply_cap(items, cap_for(greedy, env.settings))
    kept_b, over_b = apply_cap(list(reversed(items)), cap_for(env.candidates[1], env.settings))
    cap = env.settings["per_candidate_cap"]
    assert len(kept_a) == len(kept_b) == min(cap, len(items)) and kept_a == kept_b  # input order never matters
    assert all(k["published_date"] >= o["published_date"] for k in kept_a for o in over_a)  # newest first


# ---------- review gate ----------

def test_unapproved_items_never_reach_data_real(env):
    _process(env, (FIX / "listing_clean.html").read_text())
    forum, debate = sorted(load_items(env.paths, "fictional-a"), key=lambda i: i.published_date)
    for i in (forum, debate):
        _write_transcript(env.paths, i.video_id)
    review.decide(env.paths, env.allow, forum, "reject", "Test Reviewer", reason="wrong speaker")
    review.decide(env.paths, env.allow, debate, "needs_fix", "Test Reviewer", reason="check date")
    review.publish_real(env.paths, env.candidates)
    assert read_json(env.paths.real_dir / "videos.json")["videos"] == []

    fixed = load_items(env.paths, "fictional-a", ("proposed",))[0]
    review.decide(env.paths, env.allow, fixed, "approve", "Test Reviewer", venue="Example Hall", duration_sec=5400)
    review.publish_real(env.paths, env.candidates)
    videos = read_json(env.paths.real_dir / "videos.json")["videos"]
    assert [v["id"] for v in videos] == [debate.video_id]
    assert videos[0]["fictional"] is False and videos[0]["transcript_source"] == "official_captions"
    approved = load_items(env.paths, "fictional-a", ("approved",))[0]
    assert approved.review.reviewer == "Test Reviewer" and approved.review.reviewed_at
    rejected = load_items(env.paths, "fictional-a", ("rejected",))[0]
    assert rejected.review.reason == "wrong speaker"


def test_review_requires_reason_and_reviewer(env):
    _process(env, (FIX / "listing_clean.html").read_text())
    item = load_items(env.paths, "fictional-a")[0]
    with pytest.raises(review.ReviewError):
        review.decide(env.paths, env.allow, item, "reject", "Test Reviewer", reason="")
    with pytest.raises(review.ReviewError):
        review.decide(env.paths, env.allow, item, "approve", " ", venue="Hall", duration_sec=60)
    assert load_items(env.paths, "fictional-a", ("proposed",))  # nothing moved


def test_approved_item_without_transcript_is_not_searched(env):
    _process(env, (FIX / "listing_clean.html").read_text())
    item = load_items(env.paths, "fictional-a")[0]
    done = review.decide(env.paths, env.allow, item, "approve", "Test Reviewer", venue="Example Hall", duration_sec=3720)
    assert done.transcript_status == "no_transcript"
    review.publish_real(env.paths, env.candidates)
    assert read_json(env.paths.real_dir / "videos.json")["videos"] == []
    cov = read_json(env.paths.coverage)["candidates"]["fictional-a"]
    assert cov["videos_searched"] == 0 and cov["hours_searched"] == 0
    assert cov["videos_unavailable_no_transcript"] == 1

    _write_transcript(env.paths, item.video_id)  # transcript fetched later -> searched after publish
    review.publish_real(env.paths, env.candidates)
    assert len(read_json(env.paths.real_dir / "videos.json")["videos"]) == 1
    assert read_json(env.paths.coverage)["candidates"]["fictional-a"]["videos_searched"] == 1


# ---------- coverage ----------

def test_coverage_counts_match_items(env):
    _process(env, (FIX / "listing_clean.html").read_text(), "fictional-a")
    _process(env, (FIX / "listing_clean.html").read_text(), "fictional-a")  # re-run: no double counting
    forum = sorted(load_items(env.paths, "fictional-a"), key=lambda i: i.published_date)[0]
    _write_transcript(env.paths, forum.video_id)
    review.decide(env.paths, env.allow, forum, "approve", "Test Reviewer", venue="Example Library", duration_sec=3720)
    cov = compute_coverage(env.paths, env.candidates)["candidates"]
    a = cov["fictional-a"]["by_source_type"]["campaign_site_archive"]
    items = load_items(env.paths, "fictional-a")
    assert a["proposed"] == sum(i.status == "proposed" for i in items) == 1
    assert a["approved_searched"] == 1 and cov["fictional-a"]["videos_searched"] == 1
    assert cov["fictional-a"]["hours_searched"] == round(3720 / 3600, 2)
    assert a["incomplete"] == len(load_incomplete(env.paths, "fictional-a")) == 1
    assert a["filtered_out"] == 1
    assert cov["fictional-b"] == {"videos_searched": 0, "hours_searched": 0.0, "videos_unavailable_no_transcript": 0,
                                  "listings_sent_to_manual": 0, "by_source_type": {}, "label": "measured"}


# ---------- manual CSV ----------

def test_manual_rows_get_the_same_checks(env):
    rows = [
        {"candidate_id": "fictional-b", "video_url": "https://youtu.be/BBBBBBBBBB1", "title": "Town hall (FICTIONAL)",
         "publisher": "Example Channel (fictional)", "published_date": "2022-10-02", "venue": "Example Hall",
         "duration_sec": "3600", "listing_page_url": "", "added_by": "Test Person", "notes": ""},
        {"candidate_id": "fictional-b", "video_url": "https://www.youtube.com/watch?v=BBBBBBBBBB2", "title": "Forum",
         "publisher": "", "published_date": "2022-10-03", "venue": "", "duration_sec": "", "listing_page_url": "",
         "added_by": "Test Person", "notes": ""},
        {"candidate_id": "fictional-b", "video_url": "https://www.facebook.com/x/videos/1", "title": "Clip",
         "publisher": "x", "published_date": "2022-10-03", "venue": "", "duration_sec": "", "listing_page_url": "",
         "added_by": "Test Person", "notes": ""},
    ]
    counts = import_rows(env.paths, env.allow, env.settings, env.candidates, rows)
    assert counts["proposed"] == 1 and counts["rejected"] == 2
    item = load_items(env.paths, "fictional-b")[0]
    assert item.status == "proposed" and item.origin == "manual"
    assert item.video_url == "https://www.youtube.com/watch?v=BBBBBBBBBB1"


# ---------- Browserbase session ----------

class FakeSDK:
    def __init__(self):
        self.created, self.released = [], []
        self.sessions = self

    def create(self, **kw):
        self.created.append(kw)
        return SimpleNamespace(id=f"s{len(self.created)}", connect_url="wss://fake")

    def update(self, session_id, **kw):
        self.released.append((session_id, kw.get("status")))


def test_timeout_closes_the_session():
    sdk = FakeSDK()
    client = BrowserbaseClient(sdk=sdk, project_id="p", timeout_sec=0.05)
    with client.session() as h:
        time.sleep(0.3)  # a hung page
        assert h.timed_out.is_set()
        assert sdk.released == [("s1", "REQUEST_RELEASE")]  # released by the timer, not the exit
    assert sdk.released == [("s1", "REQUEST_RELEASE")]  # exactly once
    assert sdk.created[0]["api_timeout"] >= 60 and sdk.created[0]["keep_alive"] is False


def test_session_released_on_error_and_never_longer_than_cap():
    sdk = FakeSDK()
    client = BrowserbaseClient(sdk=sdk, project_id="p", timeout_sec=840)
    with pytest.raises(RuntimeError):
        with client.session(timeout_sec=99_999):
            raise RuntimeError("page crashed")
    assert sdk.released == [("s1", "REQUEST_RELEASE")]
    assert sdk.created[0]["api_timeout"] == 840


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def fetch(self, url, shot):
        return self.pages[url]


def test_run_resumes_blocks_go_manual_and_budget_stops(env):
    sdk = FakeSDK()
    client = BrowserbaseClient(sdk=sdk, project_id="p", timeout_sec=840)
    pages = {LISTING: (403, "<html>Forbidden</html>")}
    kw = dict(candidates=env.candidates, settings=env.settings, allow=env.allow, budget_minutes=55,
              client_factory=lambda: client, fetcher_factory=lambda h: FakeFetcher(pages))
    totals = collect.run(env.paths, **kw)
    assert totals["blocked"] == 2 and totals["proposed"] == 0
    assert "blocked: http 403" in env.paths.manual_queue.read_text()
    created = len(sdk.created)
    collect.run(env.paths, **kw)  # resume: blocked listings are not retried
    assert len(sdk.created) == created

    pages[LISTING] = (200, (FIX / "listing_clean.html").read_text())
    collect.run(env.paths, **{**kw, "budget_minutes": 0, "force": True})  # no budget -> no session
    assert len(sdk.created) == created


def test_dry_run_touches_nothing(env, capsys):
    rows = collect.plan(env.paths, env.allow, env.candidates, env.settings, collect.Progress(env.paths))
    assert {r["action"] for r in rows} == {"fetch"}
    example = load_candidates(REPO_ROOT / "config" / "candidates.example.json")
    rows = collect.plan(env.paths, env.allow, example, env.settings, collect.Progress(env.paths))
    assert all(r["action"] == "skip" for r in rows)
    assert not env.paths.ingest_dir.exists()


def test_session_call_matches_installed_browserbase_sdk():
    """Our fake must not drift from the real SDK (`timeout` there is the HTTP timeout, not the session's)."""
    import inspect

    sessions = pytest.importorskip("browserbase.resources.sessions")
    sdk = FakeSDK()
    with BrowserbaseClient(sdk=sdk, project_id="p", timeout_sec=840).session():
        pass
    create = inspect.signature(sessions.SessionsResource.create).parameters
    update = inspect.signature(sessions.SessionsResource.update).parameters
    assert set(sdk.created[0]) <= set(create) and "api_timeout" in sdk.created[0]
    assert {"status", "project_id"} <= set(update)


def test_click_to_play_embed_in_component_props_is_found():
    # FICTIONAL markup in the shape of an Astro island (the embed URL lives in a JSON prop).
    html = ('<astro-island component-url="/_astro/VideoPopup.js" props="{&quot;embedSrc&quot;:[0,&quot;'
            'https://www.youtube-nocookie.com/embed/CCCCCCCCCC1?rel=0&amp;playsinline=1&quot;],'
            '&quot;title&quot;:[0,&quot;Example spot (FICTIONAL)&quot;]}"></astro-island>'
            '<div data-x="https://evil.example/embed/CCCCCCCCCC2"></div>')
    found = extract_listing(html, LISTING)
    assert [(f["video_url"], f["title"]) for f in found] == [
        ("https://www.youtube.com/watch?v=CCCCCCCCCC1", "Example spot (FICTIONAL)")]


def test_filter_disabled_keeps_every_video_for_everyone(env):
    env.settings["relevance"]["enabled"] = False
    counts = _process(env, (FIX / "listing_clean.html").read_text())
    assert counts["filtered_out"] == 0 and counts["proposed"] == 3
    assert {i.relevance_keyword for i in load_items(env.paths, "fictional-a")} == {"(filter disabled)"}


def test_manual_rows_follow_the_same_format_filter(env):
    row = {"candidate_id": "fictional-b", "video_url": "https://youtu.be/BBBBBBBBBB3", "title": "Sunrise spot (FICTIONAL)",
           "publisher": "Example Channel (fictional)", "published_date": "2022-10-02", "venue": "", "duration_sec": "",
           "listing_page_url": "", "added_by": "Test Person", "notes": ""}
    assert import_rows(env.paths, env.allow, env.settings, env.candidates, [row])["proposed"] == 0  # filter on
    env.settings["relevance"]["enabled"] = False
    assert import_rows(env.paths, env.allow, env.settings, env.candidates, [row])["proposed"] == 1


def test_signup_form_captcha_is_not_a_block_but_a_challenge_page_is():
    from ingest.extract import looks_blocked

    article = "<p>" + "Example campaign news (FICTIONAL). " * 80 + "</p>"
    signup = f'<html><title>Example for Governor</title><body>{article}<form><div class="g-recaptcha"></div></form></body></html>'
    assert looks_blocked(200, signup) is None
    assert looks_blocked(200, f'<html><title>Donate</title><body>{article}<input type="password"></body></html>') is None
    assert looks_blocked(200, '<html><title>Just a moment...</title><body>Checking your browser</body></html>') == "bot challenge"
    assert looks_blocked(200, '<html><title>Example</title><body><div class="g-recaptcha"></div></body></html>') == "captcha"
    assert looks_blocked(429, "") == "http 429"


def test_embed_inside_framework_page_data_is_found():
    # FICTIONAL Next.js-style page data with an escaped iframe embed code.
    blob = ('{"props":{"blocks":[{"variant":"VIDEO","headline":"\\u003ch2\\u003eExample remarks (FICTIONAL)\\u003c/h2\\u003e",'
            '"embedCode":"\\u003ciframe src=\\"https://www.youtube.com/embed/DDDDDDDDDD1?si=x\\" title=\\"YouTube video player\\"\\u003e"}]}}')
    html = f'<script id="__NEXT_DATA__" type="application/json">{blob}</script>'
    found = extract_listing(html, LISTING)
    assert [(f["video_url"], f["title"]) for f in found] == [
        ("https://www.youtube.com/watch?v=DDDDDDDDDD1", "Example remarks (FICTIONAL)")]


def test_prefill_leaves_facts_blank_and_never_overwrites(env):
    from ingest.prefill_manual import prefill
    import csv as _csv

    _process(env, (FIX / "listing_clean.html").read_text())  # one incomplete find (no date/publisher)
    assert prefill(env.paths) == (0, 1)
    out = env.paths.ingest_dir / "manual_rows.csv"
    rows = list(_csv.DictReader(out.open()))
    assert rows[0]["video_url"] == "https://www.youtube.com/watch?v=AAAAAAAAAA4"
    assert all(rows[0][k] == "" for k in ("publisher", "published_date", "venue", "duration_sec", "added_by"))
    rows[0]["published_date"] = "2022-11-01"
    with out.open("w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    assert prefill(env.paths) == (1, 0)
    assert list(_csv.DictReader(out.open()))[0]["published_date"] == "2022-11-01"


def test_playlist_embed_is_not_a_video():
    from ingest.extract import canonical_video_url
    assert canonical_video_url("https://www.youtube.com/embed/videoseries?list=PLxxxx") is None


def test_oembed_fills_title_and_publisher_but_never_dates(env):
    from ingest.prefill_manual import fill_from_oembed, prefill
    import csv as _csv

    _process(env, (FIX / "listing_clean.html").read_text())
    prefill(env.paths)
    fake = lambda url: (200, json.dumps({"title": "Town hall replay (FICTIONAL)", "author_name": "Example Channel (fictional)",
                                         "author_url": "https://www.youtube.com/@example"}))
    assert fill_from_oembed(env.paths, get=fake) == 1
    row = list(_csv.DictReader((env.paths.ingest_dir / "manual_rows.csv").open()))[0]
    assert row["publisher"] == "Example Channel (fictional)" and row["published_date"] == "" and row["duration_sec"] == ""
    assert fill_from_oembed(env.paths, get=lambda u: (404, "")) == 0  # filled rows are left alone


def test_youtube_api_fills_local_date_and_duration_only(env):
    from ingest.youtube_metadata import fill
    import csv as _csv

    rows = [{"candidate_id": "fictional-a", "video_url": "https://www.youtube.com/watch?v=EEEEEEEEEE1", "title": "Forum (FICTIONAL)",
             "publisher": "Example Channel (fictional)", "published_date": "", "venue": "", "duration_sec": "",
             "listing_page_url": "", "added_by": "", "notes": ""},
            {"candidate_id": "fictional-a", "video_url": "https://www.youtube.com/watch?v=EEEEEEEEEE2", "title": "Gone (FICTIONAL)",
             "publisher": "Example Channel (fictional)", "published_date": "", "venue": "", "duration_sec": "",
             "listing_page_url": "", "added_by": "", "notes": ""}]
    out = env.paths.ingest_dir / "manual_rows.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    calls = []

    def fake(url):
        calls.append(url)
        # 02:30 UTC on Sept 13 is the evening of Sept 12 in Kansas (Central time).
        return 200, json.dumps({"items": [{"id": "EEEEEEEEEE1", "snippet": {"publishedAt": "2022-09-13T02:30:00Z",
                                "channelTitle": "Example Channel (fictional)"}, "contentDetails": {"duration": "PT1H2M3S"}}]})

    cands = [{**c, "jurisdiction": "Kansas"} for c in env.candidates]
    counts = fill(env.paths, cands, get=fake, key="test-key")
    assert counts == {"rows_checked": 2, "filled": 1, "unavailable": 1, "channel_mismatch": 0} and len(calls) == 1
    got = list(_csv.DictReader(out.open()))
    assert got[0]["published_date"] == "2022-09-12" and got[0]["duration_sec"] == "3723" and got[0]["venue"] == ""
    assert "VIDEO UNAVAILABLE" in got[1]["notes"]


def test_approval_without_venue_says_not_stated(env):
    _process(env, (FIX / "listing_clean.html").read_text())
    item = load_items(env.paths, "fictional-a")[0]
    done = review.decide(env.paths, env.allow, item, "approve", "Test Reviewer", venue="", duration_sec=600)
    assert done.venue == review.VENUE_NOT_STATED


def test_batch_approval_skips_opponent_titles_and_is_marked_unwatched(env):
    from ingest.models import ProposedItem
    from ingest.store import save_item

    cands = [{**env.candidates[0], "id": "fa", "name": "Alex Alder", "race_id": "r1"},
             {**env.candidates[1], "id": "fb", "name": "Blair Birch", "race_id": "r1"}]

    def item(cid, n, title):
        return ProposedItem(video_id=f"{cid}-{n}", candidate_id=cid, video_url=f"https://www.youtube.com/watch?v=FFFFFFFFF{n:02d}",
                            title=title, publisher="Example TV (fictional)", published_date="2022-10-01", duration_sec=600,
                            listing_page_url="https://www.youtube.com/@example", source_type="publisher_channel",
                            origin="manual", fetched_at=FETCHED)

    for it in (item("fa", 1, "Alder talks taxes (FICTIONAL)"),
               item("fa", 2, "Birch attacks Alder on schools (FICTIONAL)"),   # names the opponent -> person
               item("fa", 3, "Alder-Birch debate (FICTIONAL)"),               # debate naming both -> batch
               item("fb", 4, "Birch on water (FICTIONAL)")):
        save_item(env.paths, it)
    result = review.batch_approve(env.paths, env.allow, cands, "Test Reviewer")
    assert result["batch_approved"] == 3 and result["left_for_a_person"] == 1
    left = load_items(env.paths, states=("proposed",))
    assert [i.video_id for i in left] == ["fa-2"]
    approved = load_items(env.paths, states=("approved",))
    assert all(i.review.method == "batch_not_watched" and "not watched" in i.review.reason for i in approved)
