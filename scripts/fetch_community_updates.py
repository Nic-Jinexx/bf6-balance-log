#!/usr/bin/env python3
"""Collect EA's Battlefield 6 Community Updates into data/community-updates.json.

EA's news listing at /games/battlefield/battlefield-6/news is a Next.js page, so
the whole article list is in the server-rendered `__NEXT_DATA__` payload rather
than behind an API call. That payload is EA's own record: title, slug and
publishing date, straight from the CMS. Reading it is the same principle the
patch tooling already follows -- fetch the raw HTML and read what EA published,
never a summariser's version of it.

The listing pages 13 articles at a time via `?page=N`, and `totalItems` says how
many exist in all, so the loop has a real terminating condition instead of a
guess. There is no "only the ~2 most recent" problem here (the one that forces
the patch bot to run weekly) -- the full back catalogue is reachable.

    python scripts/fetch_community_updates.py            # write the data file
    python scripts/fetch_community_updates.py --check     # compare against EA, exit 1 on drift

`label` is DERIVED, not EA's wording: it is EA's title with the leading
"... Community Update -" removed so it fits a 268px sidebar. It is stored in the
file rather than computed at render time so it can be hand-corrected, and a
re-fetch keeps any label whose `title` has not changed -- the same merge rule
`build_patch_data.py --init --force` uses for hand-added tags. `title` is always
EA's exact wording and is overwritten on every fetch.

Stdlib only, same rule as every other script here.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "community-updates.json")

LISTING = "https://www.ea.com/games/battlefield/battlefield-6/news"
ARTICLE = "https://www.ea.com/games/battlefield/battlefield-6/news/%s"
UA = "Mozilla/5.0 (compatible; bf6balancelog/1.0; +https://bf6balancelog.com)"

NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', re.S)

# EA writes the prefix several ways: "Battlefield 6 - Community Update - X",
# "COMMUNITY UPDATE - X", "BATTLEFIELD LABS - COMMUNITY UPDATE - X", and with an
# en dash instead of a hyphen. Match the phrase itself, not any one spelling.
IS_COMMUNITY_UPDATE = re.compile(r"community\s+update", re.I)
STRIP_PREFIX = re.compile(r"^.*?community\s+update\s*[-‐-―:]\s*", re.I)

# Words that stay lowercase when an ALL-CAPS title is cased down, and tokens that
# must survive it intact. Only applied to titles EA published in full caps.
LOWER_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of",
               "on", "or", "the", "to", "up", "vs", "with"}
KEEP_UPPER = {"BR", "QOL", "AI", "UI", "HUD", "PC", "EA", "TDM", "XP", "REDSEC"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def listing_page(n):
    """One page of EA's news listing, as (items, featured, total)."""
    url = LISTING if n == 1 else "%s?page=%d" % (LISTING, n)
    m = NEXT_DATA.search(fetch(url))
    if not m:
        raise RuntimeError("no __NEXT_DATA__ on %s -- EA changed their page" % url)
    props = json.loads(m.group(1))["props"]["pageProps"]
    # EA renamed this key from newsDataFallback to initialNewsData some time
    # between 2026-08-14 and 2026-08-27; the inner shape (items / featured /
    # totalItems) did not change. Accept either rather than pinning to one name,
    # and fail loudly if a future rename drops both -- a silent empty list here
    # would read as "EA published nothing", which is the wrong conclusion.
    for key in ("initialNewsData", "newsDataFallback"):
        if isinstance(props.get(key), dict):
            data = props[key]
            break
    else:
        raise RuntimeError(
            "no news payload on %s -- pageProps holds %s. EA renamed the key again."
            % (url, ", ".join(sorted(props))))
    return data.get("items") or [], data.get("featured"), data.get("totalItems")


def all_articles():
    """Every BF6 news article EA lists, newest first, deduped by slug."""
    seen, order, total = {}, [], None
    n = 1
    while True:
        items, featured, total = listing_page(n)
        # the featured card is pulled out of the list, so it is only ever on
        # page 1 and would otherwise be the one article the sweep misses
        for art in ([featured] if featured and featured.get("slug") else []) + items:
            if art["slug"] not in seen:
                seen[art["slug"]] = art
                order.append(art["slug"])
        if not items:
            break
        if total and len(seen) >= total:
            break
        if n >= 40:  # backstop: EA's paging is broken rather than the list huge
            raise RuntimeError("paged past 40 pages without reaching totalItems")
        n += 1
        time.sleep(0.3)
    # EA's payload started reporting totalItems as 0 on 2026-09-01, which made
    # this assertion inert: `if total and ...` skips it entirely on a falsy
    # total, so the sweep quietly fell back to "page until EA returns nothing"
    # with nothing left checking the result. Say so out loud rather than let a
    # completeness guarantee lapse unnoticed -- that is the silent-miss mode
    # this script exists to avoid. Not fatal: paging still terminates correctly.
    if total:
        if len(seen) != total:
            raise RuntimeError("collected %d articles, EA says %d" % (len(seen), total))
    else:
        print("warning: EA's payload no longer reports totalItems (got %r), so the"
              " article count cannot be cross-checked. Paged to an empty page and"
              " collected %d article(s)." % (total, len(seen)))
    return [seen[s] for s in order], total


def title_case(text):
    out = []
    for i, word in enumerate(text.split(" ")):
        bare = word.strip("(),.:;!?’'\"")
        if bare.upper() in KEEP_UPPER:
            out.append(word)
        elif i and bare.lower() in LOWER_WORDS:
            out.append(word.lower())
        else:
            out.append(word[:1].upper() + word[1:].lower())
    return " ".join(out)


def derive_label(title):
    """EA's title minus the '... Community Update -' prefix, for the sidebar.

    Falls back to the whole title when EA writes one with no trailing subject,
    because an empty sidebar row is worse than a long one.
    """
    label = STRIP_PREFIX.sub("", title).strip()
    if not label:
        label = title.strip()
    label = re.sub(r"\s+", " ", label)
    # EA is inconsistent about caps; a shouting sidebar row is a rendering
    # problem, not a quote, so only the derived label is cased down.
    if label.upper() == label and re.search(r"[A-Z]{2}", label):
        label = title_case(label)
    return label


def collect():
    articles, _total = all_articles()
    updates = []
    for art in articles:
        if not IS_COMMUNITY_UPDATE.search(art.get("title") or ""):
            continue
        updates.append({
            "date": art["publishingDate"][:10],
            "title": art["title"].strip(),
            "label": derive_label(art["title"]),
            "slug": art["slug"],
            "url": ARTICLE % art["slug"],
        })
    # oldest first in the file so a new one appends; the renderer reverses it
    updates.sort(key=lambda u: (u["date"], u["slug"]))
    # the count EA's own totalItems used to confirm; report what was actually
    # read so the file records a real number even while totalItems reads 0
    return updates, len(articles)


def load_existing():
    if not os.path.isfile(OUT):
        return {"updates": []}
    with open(OUT, "r", encoding="utf-8") as fh:
        return json.load(fh)


KEEP_FIELDS = ("keep", "keep_note")


def kept(entry):
    """True for an entry marked to survive EA dropping it from the listing."""
    return bool(entry.get("keep"))


def write(updates, total):
    existing = {u["slug"]: u for u in load_existing().get("updates") or []}
    for u in updates:
        old = existing.get(u["slug"])
        if not old:
            continue
        # keep a hand-corrected label, but only while EA's title is unchanged
        if old.get("title") == u["title"] and old.get("label"):
            u["label"] = old["label"]
        # a keep decision is ours, not EA's, so it survives every re-fetch
        for field in KEEP_FIELDS:
            if old.get(field) is not None:
                u[field] = old[field]
    # EA delists articles whose pages are still live. Dropping one here would
    # remove a working link from the sidebar on EA's say-so alone, and an
    # absence from a listing is an observation, not proof the article is gone
    # -- the same reasoning releases.json applies to `removed`. An entry marked
    # `keep` is re-inserted; everything else still tracks EA exactly.
    live = {u["slug"] for u in updates}
    for slug, old in existing.items():
        if slug not in live and kept(old):
            updates.append(old)
    updates.sort(key=lambda u: (u["date"], u["slug"]))
    doc = {
        "_comment": "EA's Battlefield 6 Community Updates, read from EA's own news"
                    " listing payload. Regenerate with scripts/fetch_community_updates.py."
                    " Rendered as the Community Updates block at the foot of the sidebar,"
                    " by scripts/build_pages.py.",
        "_source": LISTING,
        "_date": "EA's publishingDate, date part only -- it is what EA's own listing"
                 " prints. The timezone offsets in the payload are inconsistent"
                 " (+08:00, +01:00, -07:00, Z) and shifting to UTC would move some"
                 " articles off the date EA shows.",
        "_title": "EA's exact wording. `label` is DERIVED from it for the sidebar"
                  " and may be hand-corrected; a re-fetch keeps a hand-edited label"
                  " while the title is unchanged.",
        "_scanned": "%d BF6 news articles scanned, %d are Community Updates"
                    % (total or 0, len(updates)),
        "updates": updates,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def check(updates):
    have = {u["slug"]: u for u in load_existing().get("updates") or []}
    live = {u["slug"]: u for u in updates}
    problems = []
    for slug in sorted(set(live) - set(have)):
        problems.append("NEW on ea.com, not in the data file: %s  %s"
                        % (live[slug]["date"], live[slug]["title"]))
    delisted = []
    for slug in sorted(set(have) - set(live)):
        line = "%s  %s" % (have[slug].get("date"), have[slug].get("title"))
        if kept(have[slug]):
            delisted.append(line)
        else:
            problems.append("in the data file, no longer listed by EA: " + line)
    for slug in sorted(set(have) & set(live)):
        for field in ("date", "title"):
            if have[slug].get(field) != live[slug][field]:
                problems.append("%s: %s drifted\n    ours: %r\n    EA:   %r"
                                % (slug, field, have[slug].get(field), live[slug][field]))
    if delisted:
        print("kept though EA no longer lists them (%d) -- their pages are still"
              " live; see keep_note in the data file:" % len(delisted))
        for line in delisted:
            print("  " + line)
    if problems:
        print("Community Updates out of date -- %d problem(s):" % len(problems))
        for p in problems:
            print("  " + p)
        print("\nRun: python scripts/fetch_community_updates.py")
        return 1
    print("Community Updates: %d listed by EA, %d kept, all matching ea.com."
          % (len(live), len(delisted)))
    return 0


def main():
    check_only = "--check" in sys.argv
    try:
        updates, total = collect()
    except (urllib.error.URLError, RuntimeError) as exc:
        print("error: could not read EA's news listing: %s" % exc)
        return 1
    if not updates:
        # the silent-miss mode: a page that loads but yields nothing means EA
        # restructured it, and reporting success here would hide that
        print("error: 0 Community Updates found in %s articles -- EA's listing"
              " changed shape. Fix the extractor, do not work around it." % total)
        return 1
    if check_only:
        return check(updates)
    write(updates, total)
    print("wrote %s -- %d Community Updates, %s articles scanned"
          % (os.path.relpath(OUT, ROOT), len(updates), total))
    print("  oldest: %s  %s" % (updates[0]["date"], updates[0]["title"]))
    print("  newest: %s  %s" % (updates[-1]["date"], updates[-1]["title"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
