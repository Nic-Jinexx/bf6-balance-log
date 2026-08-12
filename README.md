# Battlefield 6 — Patch Notes

Every line of every official Battlefield 6 patch note, quoted from EA and sorted by category —
weapons, vehicles, gadgets, maps, REDSEC, progression, UI, audio, Portal and AI — with each line
linked to the things it names. Nothing summarized, nothing left out.

**Live:** https://bf6balancelog.com

Every weapon, attachment, vehicle, gadget, map, mode and class gets its own page carrying every
patch note that names it, plus what the game itself says about it: in-game description, stats, and
where captured, the full customisation detail — a vehicle's loadout and both faction variants, and
a class's training paths. Every update also links out to EA's own translation of it, in the twelve
languages EA genuinely translates.

The sidebar ends with **Community Updates** — every community post EA has published, linked to
ea.com. Those posts are not mirrored here and never become patch lines; the log stays a verbatim
mirror of the Game Updates. They are linked because EA sometimes changes the game without a
changelog line, and the community post is the only place they say so.

## How it is built

No framework and no dependencies; the build is a few stdlib-only Python scripts. Run them in order,
and run every `--check` before committing:

```bash
python scripts/fetch_patch.py <version>        # cache EA's page, extract every bullet
python scripts/build_patch_data.py --init      # -> data/patches/<version>.json
python scripts/render_patches.py               # fill the generated regions of index.html
python scripts/build_pages.py                  # item pages, sitemap, search index

python scripts/fetch_community_updates.py      # -> data/community-updates.json (sidebar block)

python scripts/build_patch_data.py --check     # every EA bullet still present, verbatim
python scripts/render_patches.py --check       # index.html matches the data
python scripts/build_pages.py --check          # generated pages are fresh
python scripts/check_tags.py --check           # no patch line names an item untagged
```

`data/patches/*.json` is the source of truth. Each entry's `text` is EA's exact wording and is
guarded by `--check`, which re-reads EA's page and fails if a line is missing or altered. The
`section` and `items` fields are editorial and meant to be corrected by hand.

`check_tags.py` is the coverage net. Tagging used to happen only when a patch was first imported,
so a patch logged before an item existed was never re-scanned once that item was added. It now
matches every item against every bullet in both directions and fails on any pair that is neither
tagged nor recorded as a reviewed rejection, so neither a new patch nor a new item can slip past.

Two GitHub Actions: one runs all four checks on every push, and a weekly one detects new EA patch
versions and opens an issue. The weekly one deliberately does not write content.
