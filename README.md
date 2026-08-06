# Battlefield 6 — Patch Notes

Every line of every official Battlefield 6 patch note, quoted from EA and sorted by category —
weapons, vehicles, gadgets, maps, REDSEC, progression, UI, audio, Portal and AI — with each line
linked to the weapons, vehicles, gadgets and maps it names. Nothing summarized, nothing left out.

**Live:** https://bf6balancelog.com

Each linked item gets its own page carrying every patch note that names it, plus what the game
itself says about it: in-game description, stats, and for vehicles the full customisation loadout
and both faction variants. Every update also links out to EA's own translation of it, in the twelve
languages EA genuinely translates.

## How it is built

No framework and no dependencies; the build is a few stdlib-only Python scripts. Run them in order,
and run every `--check` before committing:

```bash
python scripts/fetch_patch.py <version>        # cache EA's page, extract every bullet
python scripts/build_patch_data.py --init      # -> data/patches/<version>.json
python scripts/render_patches.py               # fill the generated regions of index.html
python scripts/build_pages.py                  # item pages, sitemap, search index

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
