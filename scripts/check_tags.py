#!/usr/bin/env python3
"""Cross-check every patch line against every item, and fail on anything unreviewed.

The gap this closes
-------------------
`items` tagging only ever ran during `build_patch_data.py --init`. That means a
patch logged before an item existed never gets re-scanned when the item is added
later, and a new patch is only matched against whatever auto-tagging happens to
catch. Both directions leak silently: on 2026-08-05 the classes and modes shipped
with 141 patch lines that named them and pointed nowhere, and nothing in the
build complained.

How it works
------------
Every item's name and aliases are matched against every bullet's text and its
heading trail. Each (line, item) match is one of three things:

  tagged     - the slug is already in the entry's `items`. Nothing to do.
  rejected   - the pair is recorded in data/tag-decisions.json with a reason.
  UNREVIEWED - neither. This is what --check fails on.

So the noise is paid for once. "Assault" matching every assault rifle is
recorded as rejected the first time and never asked again, while a genuinely new
pairing -- a new patch naming an existing item, or a new item named by old
patches -- has nowhere to hide.

Decisions are keyed by a hash of EA's exact bullet text, not by array index, so
they survive `build_patch_data.py --init` renumbering entries.

Matching
--------
Boundaries treat a hyphen as part of a word, so "tank" does not match
"anti-tank" and "recon" does not match "counter-recon". This is deliberately
stricter than the auto-tagger, because a review queue full of junk is a review
queue nobody reads. Items can narrow it further with `tag_deny`, a list of
phrases masked out of the text before matching: the Assault class denies
"assault rifle" and "assault ladder", which are different things wearing the
same word.

Usage
-----
    python scripts/check_tags.py              # report, exit 0
    python scripts/check_tags.py --check      # report, exit 1 if anything unreviewed
    python scripts/check_tags.py --branch modes
    python scripts/check_tags.py --terms "rail cover,lpvo"   # dry-run a branch
                                                             # that has no items yet
Stdlib only, same rule as every other script here.
"""
import argparse
import collections
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECISIONS = os.path.join(ROOT, "data", "tag-decisions.json")


# --------------------------------------------------------------------------
# text handling
# --------------------------------------------------------------------------

def normalise(text):
    """EA mixes curly and straight quotes, and NBSPs turn up in pasted copy.
    Fold them so an alias written with a straight apostrophe still matches."""
    text = unicodedata.normalize("NFKC", text or "")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'),
                 ("”", '"'), ("–", "-"), ("—", "-"),
                 (" ", " ")):
        text = text.replace(a, b)
    return text


def boundary(term):
    """Word boundary that counts a hyphen as part of the word.

    Plain \\b treats a hyphen as a break, which is how "tank" would tag every
    "anti-tank" line. That footgun is documented on the Main Battle Tank item;
    this makes it not a footgun.
    """
    return r"(?<![\w-])" + re.escape(term) + r"(?![\w-])"


def entry_key(version, heading, text):
    """Stable id for one bullet.

    Not the array index: `build_patch_data.py --init` renumbers entries, which
    would silently re-point every recorded decision. Not the text alone either
    -- 1.3.1.0 prints the identical damage line under both the SLM-93A and
    9K93 IGLA sub-headings, so text-only keys collide and one rejection would
    silence two different bullets. Version plus heading trail plus text is
    unique, and all three are guarded verbatim by build_patch_data.py --check.
    """
    raw = "%s\x1f%s\x1f%s" % (version, normalise(heading), normalise(text))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_items():
    items = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "items", "*.json"))):
        d = json.loads(open(path, encoding="utf-8").read())
        # "Support" as a bare word is ordinary English and matches 30+ lines
        # about DLSS support, bot support and support for capture points. Such
        # an item sets "tag_name": false and carries the phrasings that really
        # do mean the class ("support soldier", "playing support") as aliases.
        terms = list(d.get("aliases") or [])
        if d.get("tag_name", True):
            terms = [d["name"]] + terms
        terms = [normalise(t).strip() for t in terms if str(t).strip()]
        if not terms:
            continue
        rx = re.compile("|".join(boundary(t) for t in sorted(set(terms), key=len, reverse=True)),
                        re.I)
        deny = [re.compile(boundary(normalise(p)), re.I) for p in (d.get("tag_deny") or [])]
        items.append({
            "slug": d["slug"], "name": d["name"], "branch": d.get("branch"),
            "rx": rx, "deny": deny,
        })
    return items


def load_patches():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "patches", "*.json"))):
        d = json.loads(open(path, encoding="utf-8").read())
        for i, e in enumerate(d.get("entries") or []):
            heading = " > ".join(e.get("heading") or [])
            out.append({
                "version": d["version"], "index": i, "path": path, "entry": e,
                "text": e.get("text", ""),
                "heading": heading,
                "key": entry_key(d["version"], heading, e.get("text", "")),
            })
    return out


def load_decisions():
    if not os.path.isfile(DECISIONS):
        return {"_comment": "", "rejected": {}}
    return json.loads(open(DECISIONS, encoding="utf-8").read())


# --------------------------------------------------------------------------
# matching
# --------------------------------------------------------------------------

def matches(item, text, heading):
    """True when the item is named, after masking out its denied phrases."""
    for hay in (text, heading):
        hay = normalise(hay)
        for d in item["deny"]:
            hay = d.sub(lambda m: " " * len(m.group(0)), hay)
        if item["rx"].search(hay):
            return True
    return False


def sweep(items, patches, decisions):
    rejected = decisions.get("rejected") or {}
    unreviewed, tagged, denied, ghosts = [], 0, 0, []
    for p in patches:
        have = set(p["entry"].get("items") or [])
        named = set()
        for item in items:
            if matches(item, p["text"], p["heading"]):
                named.add(item["slug"])
                if item["slug"] in have:
                    tagged += 1
                elif "%s|%s" % (p["key"], item["slug"]) in rejected:
                    denied += 1
                else:
                    unreviewed.append((p, item["slug"]))
        # tagged but never named: legitimate for hand-attached lines (EA writes
        # "knife" and means a specific melee weapon), so this informs, never fails.
        for slug in sorted(have - named):
            ghosts.append((p, slug))
    return unreviewed, tagged, denied, ghosts


def continuations(items, patches, min_run=2):
    """Runs of untagged bullets that name nothing, following a tagged bullet.

    EA writes a gadget's name once and then lists its changes as bare bullets:
    1.3.1.0 has "Updated the RPG so it now deals..." followed by six lines that
    read "Damage against tanks has been updated to 390", "Increased the maximum
    number of mines that can be placed from 6 to 9", and so on. Those name no
    item, so the match sweep cannot see them, and they reach no page.

    A single untagged bullet after a tagged one means nothing -- under a flat
    "GADGETS" heading consecutive bullets are usually unrelated, and requiring
    a run of at least `min_run` cuts the noise by an order of magnitude while
    keeping the real blocks. Reported, never failed on: this is a heuristic and
    plenty of untagged bullets legitimately name nothing.
    """
    named = {}
    for p in patches:
        named[id(p)] = any(matches(it, p["text"], p["heading"]) for it in items)

    out, i = [], 0
    while i < len(patches) - 1:
        prev = patches[i]
        carried = prev["entry"].get("items") or []
        if not carried:
            i += 1
            continue
        run, j = [], i + 1
        while j < len(patches):
            cur = patches[j]
            if (cur["version"] != prev["version"] or cur["heading"] != prev["heading"]
                    or cur["entry"].get("items") or named[id(cur)]):
                break
            run.append(cur)
            j += 1
        if len(run) >= min_run:
            out.append((prev, carried, run))
            i = j
        else:
            i += 1
    return out


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any (line, item) pair is unreviewed")
    ap.add_argument("--branch", help="only report items from this branch")
    ap.add_argument("--terms", help="comma-separated ad-hoc terms, for a branch "
                                    "whose item files do not exist yet")
    ap.add_argument("--quiet", action="store_true", help="counts only")
    ap.add_argument("--continuations", action="store_true",
                    help="also list untagged bullets that follow a tagged one "
                         "under the same heading, which is how EA writes a "
                         "gadget's name once and then lists its changes")
    args = ap.parse_args()

    patches = load_patches()

    if args.terms:
        terms = [t.strip() for t in args.terms.split(",") if t.strip()]
        item = {"slug": "(ad-hoc)", "name": ",".join(terms), "branch": None,
                "rx": re.compile("|".join(boundary(t) for t in terms), re.I),
                "deny": []}
        hits = [p for p in patches if matches(item, p["text"], p["heading"])]
        print("ad-hoc sweep for: %s\n%d line(s)\n" % (", ".join(terms), len(hits)))
        for p in hits:
            print("[%s #%d] sec=%s items=%s" % (p["version"], p["index"],
                                                p["entry"].get("section"),
                                                p["entry"].get("items")))
            print("    HEAD: %s" % p["heading"])
            print("    %s\n" % p["text"][:300])
        return 0

    items = load_items()
    if args.branch:
        items = [i for i in items if i["branch"] == args.branch]
        if not items:
            print("no items in branch %r" % args.branch)
            return 1

    decisions = load_decisions()
    unreviewed, tagged, denied, ghosts = sweep(items, patches, decisions)

    print("items:      %d" % len(items))
    print("patch lines: %d" % len(patches))
    print("matches already tagged:   %d" % tagged)
    print("matches reviewed and set aside: %d" % denied)
    print("tags with no name match (hand-attached, informational): %d" % len(ghosts))
    print("UNREVIEWED: %d" % len(unreviewed))

    if unreviewed and not args.quiet:
        by_slug = collections.defaultdict(list)
        for p, slug in unreviewed:
            by_slug[slug].append(p)
        print("\nUnreviewed (line names the item but is not tagged to it, and no "
              "decision is recorded):")
        for slug in sorted(by_slug):
            print("\n  %s  -- %d line(s)" % (slug, len(by_slug[slug])))
            for p in by_slug[slug]:
                print("    [%s #%d] %s" % (p["version"], p["index"], p["key"]))
                print("        %s" % p["text"][:150])

    if args.continuations:
        carry = continuations(items, patches)
        n = sum(len(r) for _, _, r in carry)
        print("\nPossible continuation blocks: %d block(s), %d bullet(s). Each is a "
              "run of untagged bullets naming no item, directly after a tagged one "
              "under the same heading." % (len(carry), n))
        for prev, carried, run in carry:
            print("\n  [%s #%d] %s <- tagged %s"
                  % (prev["version"], prev["index"], prev["heading"], ",".join(carried)))
            print("      %s" % prev["text"][:120])
            for cur in run:
                print("    #%-4d %s" % (cur["index"], cur["text"][:120]))

    if unreviewed:
        print("\nEach one is either a tag to add (edit data/patches/<version>.json) "
              "or a rejection to record in data/tag-decisions.json with a reason.")

    if args.check and unreviewed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
