"""Look up a freely licensed photo for each candidate on Wikidata / Wikimedia Commons.

    ONRECORD_DATA_DIR=data/real python scripts/fetch_photos.py            # show what would change
    ONRECORD_DATA_DIR=data/real python scripts/fetch_photos.py --write    # save to candidates.json

For every candidate it finds the Wikidata entry of a politician with that exact name, takes
that entry's image (property P18), and reads the author and license from Wikimedia Commons.
It then sets photo_url (a 256px Commons thumbnail, linked, not copied) and photo_credit.

A person must check the printed matches before using --write: a shared name could match the
wrong person. Candidates with no entry, no image, or no clear license are left without a
photo and the site shows their initials. See docs/SOURCES.md (Wikimedia Commons).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import config  # noqa: E402

UA = "FirsthandPhotoLookup/0.1 (civic transparency project)"
POLITICIAN = re.compile(r"politician|senator|representative|governor|legislator|congress", re.I)


try:  # some Python installs ship without root certificates; certifi (a dependency of httpx) has them
    import certifi

    TLS = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # pragma: no cover
    TLS = ssl.create_default_context()


def get(url: str, **params) -> dict:
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers={"User-Agent": UA})
    for wait in (2, 8, 20, None):  # be a polite client: pause between calls, back off when told to
        time.sleep(1.5)
        try:
            with urllib.request.urlopen(req, timeout=20, context=TLS) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            if e.code != 429 or wait is None:
                raise
            time.sleep(wait)


def find_entity(name: str) -> dict | None:
    hits = get("https://www.wikidata.org/w/api.php", action="wbsearchentities", search=name,
               language="en", type="item", limit=5, format="json").get("search", [])
    for hit in hits:
        if hit.get("label", "").lower() == name.lower() and POLITICIAN.search(hit.get("description", "")):
            return hit
    return None


def photo_for(entity_id: str) -> tuple[str, str] | None:
    claims = get("https://www.wikidata.org/w/api.php", action="wbgetclaims", entity=entity_id,
                 property="P18", format="json").get("claims", {}).get("P18", [])
    if not claims:
        return None
    filename = claims[0]["mainsnak"]["datavalue"]["value"]
    pages = get("https://commons.wikimedia.org/w/api.php", action="query", titles=f"File:{filename}",
                prop="imageinfo", iiprop="url|extmetadata", iiurlwidth=256, format="json")["query"]["pages"]
    info = next(iter(pages.values())).get("imageinfo", [{}])[0]
    meta = info.get("extmetadata", {})
    license_name = meta.get("LicenseShortName", {}).get("value")
    if not info.get("thumburl") or not license_name:
        return None
    artist = html.unescape(re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", ""))).strip() or "Unknown author"
    thumb = info["thumburl"].split("?")[0]  # drop Commons' own tracking parameters
    return thumb, f"{artist[:80]}, {license_name}, via Wikimedia Commons"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="save the photos to candidates.json")
    args = ap.parse_args()
    path = config.data_dir() / "candidates.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = data["candidates"] if isinstance(data, dict) else data
    for c in candidates:
        if c.get("fictional"):
            continue
        try:
            entity = find_entity(c["name"])
            found = photo_for(entity["id"]) if entity else None
        except urllib.error.URLError as e:
            print(f"{c['name']}: lookup failed ({e}); left without a photo")
            continue
        if not found:
            print(f"{c['name']}: no photo ({'no image or license' if entity else 'no matching Wikidata entry'})")
            continue
        c["photo_url"], c["photo_credit"] = found
        print(f"{c['name']}: {entity['id']} \"{entity.get('description', '')}\"\n   {found[0]}\n   {found[1]}")
    if args.write:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved {path}")
    else:
        print("Dry run. Check each match is the right person, then re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
