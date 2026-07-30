#!/usr/bin/env python3
"""
Checks EA's official Battlefield 6 sources for Game Update version numbers
that aren't in data/known_versions.json yet.

This script does NOT write balance entries — it only detects that a new
patch exists and reports it, because deciding what counts as a "balance
change" vs. a bug fix needs editorial judgment. It writes GitHub Actions
outputs (`found`, `versions`) that the workflow uses to open an issue.

No third-party dependencies (stdlib only) so the Action runs fast with
no pip install step.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SOURCES = [
    "https://www.ea.com/games/battlefield/battlefield-6/news",
    "https://forums.ea.com/category/battlefield-en/blog/battlefield-game-info-hub-en",
]

# Matches battlefield-6-game-update-1-4-1-0 / battlefield-6-update-1-1-1-0 /
# battlefield-6-update-notes-1-0-1-0 style slugs used across ea.com and forums.ea.com
VERSION_RE = re.compile(
    r"battlefield-6-(?:game-update|update-notes|update)-(\d+-\d+-\d+-\d+)"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWN_PATH = REPO_ROOT / "data" / "known_versions.json"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_versions(html: str) -> set[str]:
    return {m.group(1).replace("-", ".") for m in VERSION_RE.finditer(html)}


def write_output(name: str, value: str) -> None:
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"{name}={value}")


def version_key(v: str):
    return [int(x) for x in v.split(".")]


def main() -> None:
    known = json.loads(KNOWN_PATH.read_text())
    known_versions = set(known["versions"])

    found_versions: set[str] = set()
    errors = []
    for url in SOURCES:
        try:
            html = fetch(url)
            found_versions |= extract_versions(html)
        except Exception as e:  # noqa: BLE001 - report and keep going
            errors.append(f"{url}: {e}")

    if errors and not found_versions:
        # Every source failed to fetch (network hiccup, EA changed the page, etc.)
        # Don't report a false "nothing new" — just skip this run quietly.
        print("All sources failed to fetch:", "; ".join(errors), file=sys.stderr)
        write_output("found", "false")
        return

    new_versions = sorted(found_versions - known_versions, key=version_key)

    if not new_versions:
        print("No new patches found.")
        write_output("found", "false")
        return

    print("New patch(es) detected:", ", ".join(new_versions))
    write_output("found", "true")
    write_output("versions", ",".join(new_versions))


if __name__ == "__main__":
    main()
