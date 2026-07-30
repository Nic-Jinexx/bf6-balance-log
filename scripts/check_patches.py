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
    # forums.ea.com was dropped 2026-07-30. It 403s a plain "Mozilla/5.0" UA, and
    # with a full browser UA it returns a 20 KB client-side-rendered shell with no
    # article links in it at all — so the regex could never match there. Keeping it
    # only produced a permanent failure to log every run.
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


def warn(message: str) -> None:
    """Surface a non-fatal problem loudly.

    Inside Actions this emits a `::warning::` annotation, so a dead or
    restructured source shows up on the run summary instead of hiding behind a
    green checkmark that looks identical to a clean run.
    """
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::warning::{message}")
    else:
        print(f"WARNING: {message}", file=sys.stderr)


def version_key(v: str):
    return [int(x) for x in v.split(".")]


def main() -> None:
    known = json.loads(KNOWN_PATH.read_text())
    known_versions = set(known["versions"])

    found_versions: set[str] = set()
    errors = []
    for url in SOURCES:
        try:
            versions = extract_versions(fetch(url))
        except Exception as e:  # noqa: BLE001 - report and keep going
            errors.append(f"{url}: {e}")
            continue

        print(f"{url} -> {len(versions)} version(s)")
        if not versions:
            # Fetched fine but matched nothing. Almost always means EA restructured
            # the page or moved it behind client-side rendering. This is the silent
            # -miss case: without a warning it reads exactly like "no new patches".
            warn(f"{url} fetched OK but yielded no version numbers - regex may be stale")
        found_versions |= versions

    # Always report per-source failures. Previously these were only printed when
    # *every* source failed, so one dead source out of several passed unnoticed.
    for err in errors:
        warn(f"source failed to fetch - {err}")

    if errors and not found_versions:
        # Every source failed (network hiccup, EA changed the page, etc.).
        # Don't report a false "nothing new" — skip this run without flagging.
        warn("every source failed - skipping this run rather than reporting 'nothing new'")
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
