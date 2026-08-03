#!/usr/bin/env python3
"""Fetch an EA Battlefield 6 Game Update page and extract every changelog bullet.

Output is one JSON record per bullet, carrying EA's exact wording plus the
heading trail it appeared under. This is the raw material for
data/patches/<version>.json; it never rewrites or summarises a line.

Scrape rules that are easy to get wrong, all learned the hard way:
  * Anchor on the CHANGELOG heading and stop at "This announcement may change".
    Stopping on "EA app for Windows" truncates at the site nav; not stopping at
    all swallows the page footer and inflates counts.
  * EA writes section labels three different ways: real <h2> tags (REDSEC),
    <p><strong>WEAPONS:</strong></p> paragraphs, and bare map-name headings that
    the bullets beneath never repeat. Track all three or map bullets get lost.
  * forums.ea.com 403s this fetcher. Use ea.com.

stdlib only, same rule as the rest of scripts/.

Usage:
    python scripts/fetch_patch.py 1.4.1.5           # print a summary
    python scripts/fetch_patch.py 1.4.1.5 --json    # dump the records
    python scripts/fetch_patch.py --all             # every known version
"""
import argparse
import html as H
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE = REPO_ROOT / "data" / "patch-source"
KNOWN = REPO_ROOT / "data" / "known_versions.json"

URL_PATTERNS = [
    "https://www.ea.com/games/battlefield/battlefield-6/news/battlefield-6-game-update-{d}",
    "https://www.ea.com/games/battlefield/battlefield-6/news/battlefield-6-update-{d}",
    "https://www.ea.com/games/battlefield/battlefield-6/news/battlefield-6-update-notes-{d}",
]

STOP_MARKER = "This announcement may change"
TAG = re.compile(r"<[^>]+>")

# A heading-ish label: EA's section names are shouty, and its map headings are
# short Title Case strings sitting alone in their own paragraph.
SECTIONISH = re.compile(r"^[A-Z0-9][A-Z0-9 &/'\-\.]*:?$")

# EA repeats its section names as an in-page nav list at the top of the
# changelog. Each of those <li>s wraps a <button>, which is the only reliable
# way to tell them apart from content: matching on text instead dropped two
# real "Manhattan Bridge" lines out of a bare map list in 1.2.1.0, because that
# map name also appeared as a heading elsewhere on the page.
NAV_LI = re.compile(r"^\s*<(?:button|a)\b[^>]*>.*?</(?:button|a)>\s*$", re.I | re.S)


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


VERSION_RE = re.compile(r"^\d+(?:\.\d+){1,3}$")


def check_version(version):
    """Versions become filenames and URL fragments, so validate before use."""
    if not VERSION_RE.match(version):
        raise SystemExit(
            "refusing to use %r as a version: expected digits and dots, e.g. 1.4.1.5"
            % version)
    return version


def page_for(version, refresh=False):
    """Return (html, source). Cached under data/patch-source/ so a re-run is
    free and so the exact bytes a record was built from stay auditable."""
    check_version(version)
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{version}.html"
    if cached.exists() and not refresh:
        return cached.read_text(encoding="utf-8"), "cache"
    dashed = version.replace(".", "-")
    last = None
    for pattern in URL_PATTERNS:
        url = pattern.format(d=dashed)
        try:
            body = fetch(url)
        except Exception as exc:  # noqa: BLE001 - try the next slug
            last = f"{url}: {exc}"
            continue
        if "CHANGELOG" in body.upper():
            cached.write_text(body, encoding="utf-8")
            return body, url
        last = f"{url}: fetched but no CHANGELOG heading"
    raise SystemExit(f"could not fetch {version} - {last}")


def text_of(chunk):
    return re.sub(r"\s+", " ", H.unescape(TAG.sub(" ", chunk))).strip()


def changelog_region(body):
    upper = body.upper()
    start = upper.find("CHANGELOG")
    if start < 0:
        raise SystemExit("no CHANGELOG heading found")
    stop = body.find(STOP_MARKER)
    return body[start:stop if stop > start else len(body)]


def extract(body):
    """Every <li> in the changelog region, with the heading trail above it."""
    region = changelog_region(body)
    token = re.compile(
        r"<(h[1-6])[^>]*>(.*?)</\1>"      # real headings
        r"|<li[^>]*>(.*?)</li>"           # bullets
        r"|<p[^>]*>(.*?)</p>",            # paragraph pseudo-headings
        re.I | re.S,
    )
    levels = {}
    para_head = None
    rows = []
    dropped = []
    for m in token.finditer(region):
        if m.group(1):
            level = int(m.group(1)[1])
            label = text_of(m.group(2))
            if not label:
                continue
            levels[level] = label
            for deeper in [k for k in levels if k > level]:
                del levels[deeper]
            para_head = None
        elif m.group(3) is not None:
            if NAV_LI.match(m.group(3)):
                dropped.append(text_of(m.group(3)))
                continue  # EA's in-page nav, not patch content
            body_text = text_of(m.group(3))
            if not body_text:
                continue
            trail = [levels[k] for k in sorted(levels)]
            if para_head:
                trail.append(para_head)
            rows.append({"heading": trail, "text": body_text})
        else:
            label = text_of(m.group(4))
            if label and len(label) < 90 and SECTIONISH.match(label):
                para_head = label.rstrip(":")
    extract.last_dropped = dropped
    return rows


def summarise(version, rows):
    from collections import Counter
    counts = Counter(" > ".join(r["heading"]) or "(no heading)" for r in rows)
    print(f"{version}: {len(rows)} bullet(s)")
    for label, n in counts.most_common():
        print(f"   {n:>4}  {label}")
    # Never drop content silently - a nav item that is actually a patch note
    # has to be visible in the output, not inferred from a count that moved.
    dropped = getattr(extract, "last_dropped", [])
    if dropped:
        print(f"   dropped {len(dropped)} nav item(s): "
              + ", ".join(repr(d) for d in dropped[:8]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="re-download, ignore cache")
    args = ap.parse_args()

    if args.all:
        versions = json.loads(KNOWN.read_text())["versions"]
    elif args.version:
        versions = [args.version]
    else:
        ap.error("give a version or --all")

    out = {}
    for version in versions:
        body, source = page_for(version, refresh=args.refresh)
        rows = extract(body)
        out[version] = rows
        if not args.json:
            summarise(version, rows)
            if source != "cache":
                print(f"   source: {source}")
    if args.json:
        json.dump(out, sys.stdout, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
