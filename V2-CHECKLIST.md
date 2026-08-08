# V2 Checklist

Everything currently unfilled, wrong, or worth deciding. Counts are from a full scan of
`data/items/*.json` (249 items) on **Aug 7, 2026**, after the Compatible-attachments removal.

Anything marked **TBD** renders as a visible TBD on the live page. Anything marked *(by design)*
is correct as-is and listed only so it isn't mistaken for a gap.

---

## 0. Do this first — stale rules in `CLAUDE.md`

The "Compatible attachments" section is gone from every weapon page, but `CLAUDE.md` still carries
three hard rules describing it as live. A future session will read those and rebuild what we just
removed.

- [ ] Delete or mark superseded: **"Attachment compatibility lives on the weapon-attachment pairing,
      never on the attachment"** — the `slots` / `slots_present` two-tier rule.
- [ ] Delete or mark superseded: **"A locked tile is still compatible."**
- [ ] Keep but re-scope: **"Optics, Barrels and Magazines are family index pages, not leaves."**
      Still true — the 98 attachment pages are untouched. Only the weapon-side section went away.
- [ ] Note that `compatibility` blocks still sit in 11 weapon JSON files, unread by any renderer.

---

## 1. TBD values — 84 across 20 items

### Vehicles — 75 TBDs, the big one

Every vehicle has a `description.text` TBD, and 7 of 11 have undescribed loadout option tiles.
Per the existing rule, name-only tiles are recorded deliberately; the TBD is the description.

| Vehicle | TBDs | Breakdown |
|---|---|---|
| Infantry Fighting Vehicle | 19 | 1 description + 18 loadout options |
| Armored Transport | 15 | 1 description + 14 loadout options |
| Main Battle Tank | 12 | 1 description + 11 loadout options |
| Mobile Anti-Air | 8 | 1 description + 7 loadout options |
| Attack Helicopter | 7 | 1 description + 6 loadout options |
| Scout Helicopter | 7 | 1 description + 6 loadout options |
| Patrol Boat | 3 | 1 description + 2 loadout options |
| Attack Jet | 1 | description only |
| Fighter Jet | 1 | description only |
| Light Ground Transport | 1 | description only |
| Transport Helicopter | 1 | description only |

- [ ] Fill the 11 vehicle `description.text` values
- [ ] Fill the 64 loadout option descriptions (read off each vehicle's own customisation screen —
      **never share text between vehicles**, per the per-vehicle rule)

### Weapons — 5 TBDs

- [ ] `availability` for the five melee items: **Combat Knife, EOD Bot Arm, Ice Axe, Serrated Blade,
      Sledgehammer**

### Modes — 2 TBDs

- [ ] `description.text` for **King of the Hill** and **Rush**

### Classes — 1 TBD

- [ ] `documented_paths` for **Assault** — the two training paths EA names but no capture covers

### Attachments — 1 TBD

- [ ] `description.text` for **Magnifier**

---

## 2. Missing images — 101

- [ ] **98 attachment pages** have no image at all. Every page under `/attachments/` is text-only.
      Biggest single visual gap on the site.
- [ ] **King of the Hill** and **Rush** — the only two modes without one
- **Wake Island** — no image, *(by design)*: it's in `scheduled` for the Aug 18 Top Gun update and
      must not be treated as shipped

Vehicle faction variants are all present — both NATO and Pax Armata images resolve for all 11.

---

## 3. Missing `Added in` — 117 items

`data/releases.json` is the only source for this row. 131 slugs are recorded; these are not:

- [ ] **94 attachments** (of 98)
- [ ] **11 vehicles** (all of them)
- [ ] **7 modes** — Breakthrough, Conquest, Domination, Escalation, King of the Hill, Rush,
      Team Deathmatch
- [ ] **4 classes** — Assault, Engineer, Recon, Support
- [ ] **1 gadget** — Long-Range Launcher

Most of these shipped at launch (`1.0.1.0`), whose entry already warns it is *"not an exhaustive
launch roster."* Filling it is mostly a matter of confirming which were launch content and adding
them to that release's `added` array.

---

## 4. Decisions to make (not defects)

- [ ] **The `summary` section gap.** 58 EA "Major Updates for X" lines are joined into one untagged
      paragraph, so **50 tag pairs across 38 items never reach their item page**. The text is on the
      front page verbatim — only the per-item view loses it. Fixing it changes how that quote reads,
      so it's your call. Pre-existing and documented.
- [ ] **80 items have zero tagged patch lines** — 70 attachments, 6 weapons, 2 gadgets, 1 map,
      1 vehicle. Not a defect: EA simply hasn't named them. `check_tags.py` reports 0 unreviewed, so
      coverage is genuinely clean.
- [ ] **`releases.json` `removed` array** — the single entry has no `slug`, only `entries`. Worth a
      look to confirm that's the intended shape.

---

## 5. Performance (from the Aug 7 review)

- [ ] **Convert 23 map PNGs to JPEG.** They average 356 KB and top out at 965 KB
      (`manhattan-bridge`, `saints-quarter`). The 140 weapon JPEGs average 83 KB for the same job.
      Takes ~8 MB down to ~2 MB and is the biggest user-facing win available.
- [ ] **Fix the item hero `<img>`.** It carries `loading="lazy"` with no `width`/`height`, on all
      249 pages. It's the LCP element and above the fold, so lazy actively delays it, and the
      missing dimensions cause layout shift. Wants `fetchpriority="high"`, no `loading`, explicit
      dimensions. Generator change in `build_pages.py`.
- [ ] **7.54 MB of byte-identical duplicate images**, 17 groups — e.g. `img/items/manhattan-bridge.png`
      is the same file as `img/battlefield-6-map-manhattan-bridge-16x9.png`. Costs users nothing;
      it's ~40% of the repo and slows clones and CI checkout.

Not actionable: GitHub Pages serves gzip only (no brotli) and pins `Cache-Control: max-age=600`.

---

## 6. Verified working — no action

- **Ko-fi button and Feedback button are both live and correct.** Checked on
  https://bf6balancelog.com/ in Chrome: `#kofi-fixed` is `position:fixed`, 18px off the bottom-right,
  containing the Feedback link (113×39) and the Ko-fi anchor (185×40) pointing at
  `ko-fi.com/L5V622ZF6S`. Nothing is broken.
  **Why you may not have seen it:** at **≤640px viewport width** the CSS deliberately switches
  `#kofi-fixed` to `position:static` and drops both buttons into the end of the page flow — and the
  front page is **14,300px tall**. On a phone you'd have to scroll past all 2,894 patch lines to
  reach them.
  - [ ] Decide: keep both buttons fixed on mobile too, or leave them parked at the bottom?
