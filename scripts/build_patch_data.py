#!/usr/bin/env python3
"""Turn the cached EA changelog pages into data/patches/<version>.json.

One record per EA bullet. The record carries EA's exact wording, the heading
trail it appeared under, the log category it renders in, and the item slugs it
mentions. Nothing here rewrites a line: `text` is byte-for-byte what EA
published, and --check proves it stays that way.

    python scripts/build_patch_data.py --init            # create missing files
    python scripts/build_patch_data.py --init --force    # regenerate, losing edits
    python scripts/build_patch_data.py --check           # verify against EA's page

Once a file exists it is the source of truth and is meant to be hand-corrected:
fix a wrong `section`, add a missed slug to `items`. --check only guards `text`
and completeness, so edits to the other fields survive.

stdlib only.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_patch import extract, page_for  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
PATCHES = REPO_ROOT / "data" / "patches"
ITEMS = REPO_ROOT / "data" / "items"
KNOWN = REPO_ROOT / "data" / "known_versions.json"

# EA's heading -> the category the line renders under on the site.
# Anything unmapped lands in "misc", which renders inside the collapsed
# "Everything else" block rather than being dropped.
SECTION_MAP = {
    "PLAYER": "player",
    "WEAPONS": "weapons",
    "NEW WEAPONS": "weapons",
    "WEAPON BALLISTIC CHANGES": "weapons",
    "RECOIL CONSISTENCY CHANGES": "weapons",
    "VEHICLES": "vehicles",
    "NEW VEHICLE": "vehicles",
    "GADGETS": "gadgets",
    "NEW GADGETS": "gadgets",
    "MAPS & MODES": "maps",
    "MAPS AND MODES": "maps",
    "MAP & MODES": "maps",
    "MAP": "maps",
    "GAUNTLET": "maps",
    "COMPETITIVE": "maps",
    "PROGRESSION": "progression",
    "BATTLE PASS & PROGRESSION": "progression",
    "CALL-INS": "gadgets",
    "STRIKE PACKAGES": "gadgets",
    "LOOT": "maps",
    "UI & HUD": "ui",
    "UI&HUD": "ui",
    "AUDIO": "audio",
    "PORTAL": "portal",
    "AI": "ai",
    "BOTS": "ai",
    # No category of their own, by decision 2026-08-03 - these render in the
    # collapsed per-patch block.
    "SETTINGS": "misc",
    "NETWORK": "misc",
    "SINGLE PLAYER": "misc",
    "STABILITY": "misc",
    "VFX & VIDEO": "misc",
}

# Headings that are a specific piece of kit rather than a category. The heading
# both picks the category and tags the item.
ITEM_HEADINGS = {
    "MBT-LAW": ("gadgets", "mbt-law"),
    "SS26": ("gadgets", "ss26"),
    "RPG-7V2": ("gadgets", "rpg-7v2"),
    "T-UGS": ("gadgets", None),
    "M16A4": ("weapons", "m16a4"),
    "RPK-74M": ("weapons", "rpk-74m"),
    "AK-205": ("weapons", "ak-205"),
}

SUMMARY_RE = re.compile(r"^MAJOR UPDATES FOR ", re.I)
NEWCONTENT_RE = re.compile(r"^(NEW CONTENT|NEW MAP)\b", re.I)


def load_items():
    out = {}
    for path in sorted(ITEMS.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        out[d["slug"]] = d
    return out


def build_patterns(items):
    pats = {}
    for slug, item in items.items():
        forms = [item["name"]] + (item.get("aliases") or [])
        alts = []
        for form in forms:
            core = re.sub(r"[^A-Za-z0-9]+", " ", form).strip()
            if len(core) < 2:
                continue
            alts.append(r"[\s\-\./]*".join(re.escape(c) for c in core.split()))
        if alts:
            # Trailing s? so a plural still matches: EA writes "Anti-Tank Mines"
            # and "stun grenades", which otherwise slip past the word boundary.
            pats[slug] = re.compile(
                r"(?<![A-Za-z0-9])(?:"
                + "|".join(sorted(alts, key=len, reverse=True))
                + r")s?(?![A-Za-z0-9])", re.I)
    return pats


def match_slugs(text, pats):
    """Slugs named in `text`, with contained matches dropped.

    "M4A1 SLAM" also matches the M4A1 carbine, and "EOD Bot Arm" matches the
    EOD Bot. Whenever one item's match sits entirely inside another's, only the
    longer one is a real mention.
    """
    spans = []
    for slug, rx in pats.items():
        for m in rx.finditer(text):
            spans.append((m.start(), m.end(), slug))
    keep = set()
    for start, end, slug in spans:
        covered = any(
            other != slug and o_start <= start and end <= o_end
            and (o_end - o_start) > (end - start)
            for o_start, o_end, other in spans
        )
        if not covered:
            keep.add(slug)
    return keep


def classify(heading):
    """(section, redsec, item_slug_from_heading) for a heading trail."""
    trail = [h for h in heading if h.upper().rstrip(":") != "CHANGELOG"]
    redsec = any(h.upper().startswith("REDSEC") for h in trail)
    trail = [h for h in trail if not h.upper().startswith("REDSEC")]

    slug = None
    section = None
    # Walk deepest-first so a per-item heading wins over its parent category.
    for label in reversed(trail):
        key = label.rstrip(":").upper()
        if key in ITEM_HEADINGS:
            sec, slug = ITEM_HEADINGS[key]
            section = section or sec
            continue
        if SUMMARY_RE.match(key):
            return "summary", redsec, slug
        if NEWCONTENT_RE.match(key):
            section = section or "maps"
            continue
        if key in SECTION_MAP and section is None:
            section = SECTION_MAP[key]
    return section or "misc", redsec, slug


def records_for(version, items, pats, refresh=False):
    body, _ = page_for(version, refresh=refresh)
    rows = extract(body)
    out = []
    for row in rows:
        section, redsec, heading_slug = classify(row["heading"])
        text = row["text"]
        slugs = match_slugs(text, pats)
        if heading_slug:
            slugs.add(heading_slug)
        rec = {
            "text": text,
            "heading": row["heading"],
            "section": section,
            "items": sorted(slugs),
        }
        if redsec:
            rec["redsec"] = True
        out.append(rec)
    return out


def init(versions, items, pats, force=False, refresh=False):
    PATCHES.mkdir(parents=True, exist_ok=True)
    for version in versions:
        target = PATCHES / f"{version}.json"
        if target.exists() and not force:
            print(f"{version}: exists, skipping (use --force to regenerate)")
            continue

        # Carry hand-made corrections across a regenerate. Auto-tagging only
        # sees the names EA happens to use, so slugs added by hand - and any
        # corrected section - would otherwise be lost every time this reruns.
        previous = {}
        if target.exists():
            for old in json.loads(target.read_text(encoding="utf-8"))["entries"]:
                previous[old["text"]] = old

        recs = records_for(version, items, pats, refresh=refresh)
        kept = 0
        for rec in recs:
            old = previous.get(rec["text"])
            if not old:
                continue
            merged = sorted(set(rec["items"]) | set(old.get("items", [])))
            if merged != rec["items"]:
                kept += 1
            rec["items"] = merged
            if old.get("section_manual"):
                rec["section"] = old["section"]
                rec["section_manual"] = True
        if kept:
            print(f"{version}: kept hand-added tags on {kept} entr(ies)")
        payload = {
            "_comment": (
                "Generated by scripts/build_patch_data.py from the cached EA page in "
                "data/patch-source/. 'text' is EA's exact wording and must stay that "
                "way - scripts/build_patch_data.py --check re-reads EA's page and "
                "fails if any bullet is missing or altered. 'section' and 'items' are "
                "meant to be hand-corrected and are not overwritten by --check."),
            "version": version,
            "entries": recs,
        }
        target.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"{version}: wrote {len(recs)} entries")


def check(versions, items, pats):
    problems = 0
    for version in versions:
        target = PATCHES / f"{version}.json"
        if not target.exists():
            print(f"{version}: MISSING {target.relative_to(REPO_ROOT)}")
            problems += 1
            continue
        stored = json.loads(target.read_text(encoding="utf-8"))["entries"]
        body, _ = page_for(version)
        ea = [r["text"] for r in extract(body)]
        have = [e["text"] for e in stored]

        # Multisets, not sets: EA does repeat a bullet verbatim within one patch
        # (1.2.2.0 ships "Improved reload rattle sound effects for the B36A4."
        # twice). Plain membership would call a dropped duplicate a pass.
        ea_counts, have_counts = Counter(ea), Counter(have)
        missing = ea_counts - have_counts
        extra = have_counts - ea_counts
        if missing or extra:
            problems += 1
            print(f"{version}: {sum(missing.values())} missing, "
                  f"{sum(extra.values())} not in EA's page")
            for t, n in list(missing.items())[:5]:
                print(f"    MISSING x{n}: {t[:100]}")
            for t, n in list(extra.items())[:5]:
                print(f"    EXTRA   x{n}: {t[:100]}")
        else:
            print(f"{version}: {len(have)}/{len(ea)} bullets present verbatim")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--version", action="append")
    args = ap.parse_args()

    versions = args.version or json.loads(KNOWN.read_text())["versions"]
    items = load_items()
    pats = build_patterns(items)

    if args.init:
        init(versions, items, pats, force=args.force, refresh=args.refresh)
    if args.check:
        sys.exit(1 if check(versions, items, pats) else 0)
    if not args.init and not args.check:
        ap.error("pass --init or --check")


if __name__ == "__main__":
    main()
