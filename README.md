# Battlefield 6 — Balance Change Log

A categorized, searchable log of every official BF6 balance change (weapons, vehicles,
gadgets, maps, REDSEC), sourced from EA's own patch note pages.

**Live:** https://bf6balancelog.com

## When the bot flags a new patch

`check-patches.yml` runs daily and opens a GitHub issue tagged `new-patch` when EA
ships an update this repo doesn't have yet.

1. Open the flagged issue — it names the version.
2. Ask Claude (or Claude Code) to pull that patch's notes and extract the
   balance-relevant changes.
3. Add the new entries to `index.html`, plus a row in the Patch Index table.
4. Add the version to `data/known_versions.json`.
5. Push to `main` — the live site updates automatically.
