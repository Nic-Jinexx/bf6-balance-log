# V2 Checklist

Everything currently unfilled, wrong, or worth deciding. Counts are from a **full re-scan** of
`data/items/*.json` (249 items), `data/releases.json` and `img/` on **Aug 12, 2026** — not carried
over from the Aug 7 pass. Where a number moved, the old one is noted.

Anything marked **TBD** renders as a visible TBD on the live page. Anything marked *(by design)* is
correct as-is and listed only so it isn't mistaken for a gap.

---

## 0. Season 4 / Top Gun — ships Aug 18, six days out

The nearest deadline, so it goes first. `releases.json` `scheduled` lists 8 items under Top Gun;
the generator ignores that array, so **none of this can be filled until it actually ships** — but
the pages can be drafted now and the `Added in` filled on the day.

**Only items get pages.** POIs, Features and Events are recorded in `releases.json` and never become
item pages — every one ever released carries no slug, from `Portal Updates` to
`Defense Testing Complex 3 - Fort Lyndon POI`. That's the pattern, not a gap.

| Content | Kind | Page needed | Status |
|---|---|---|---|
| Wake Island | Map | yes | ✅ done — art added Aug 12, Status row says "Scheduled — not yet released" |
| Interdictor | Weapon | yes | needs a page. Subcategory unknown until it ships |
| F/A-81F Super Spectre | Vehicle | yes | needs a page. `vehicles` is flat, one page per class |
| F-74A Seacat | Vehicle | yes | needs a page |
| Top Gun: Carrier Strike | Mode | **decide** | the `modes` branch is the 8 core-multiplayer modes in Custom Search. Every REDSEC/BR mode — Battle Royale, Gauntlet, Strikepoint, Sabotage, Nightfall — is recorded with no page. So this turns on whether it's core MP |
| Top Gun: Fighter Sweep | Mode | **decide** | REDSEC, so on the above precedent: no page |
| Aircraft Carrier | POI | no | *(by design)* — a POI on the map, not an item. Recorded in `releases.json` only, exactly like the Fort Lyndon POI |
| Spectator Mode + Custom Lobbies | Feature | no | *(by design)* — Features never get pages |

- [ ] **Decide where `Topgun.png` goes, or that it goes nowhere.** Added Aug 12 in preparation for
      the patch. It's chapter art, and chapters aren't items, so it has no home unless one of the
      Top Gun modes gets a page to hero it on. Excluded from the repo for now. It also carries
      Paramount's mark and copyright line, a different licensing question from EA's own art — worth
      a thought before it's published.
- [ ] **Confirm the Top Gun mode names against EA on patch day.** `scheduled` currently says
      *Carrier Strike* and *Fighter Sweep*, taken from the roadmap art. A mode called **Carrier
      Assault** may be the real name — **deliberately not written in**, on the owner's instruction
      and the standing rule that names come from EA's own page, never from recollection or press.
- [ ] **On patch day: run `fetch_patch.py` first**, then the build chain, then all four checks.
      Expect the version to be **`1.4.2.0`** on the `1.<season>.<part>.0` scheme — that's read off
      the pattern, *not* confirmed, so take it from EA's page like every other number.
- [ ] **Run `check_tags.py` after adding any new item file.** That is exactly the case it exists for:
      a patch logged before an item exists is never re-scanned when the item appears.
- [ ] **Refresh `fetch_community_updates.py`** — EA usually posts a Community Update alongside a
      chapter drop, and it is deliberately not in `verify.yml`, so nothing pulls it automatically.
- [ ] **Fill `Added in` for everything above on release day**, moving it out of `scheduled` into the
      new version's `added` array. Nothing may carry an `Added in` before it ships.

---

## 1. TBD values — 86 across 21 items

Was 84/20 on Aug 7. The two new ones are EF88's, and they are **not** a real gap — see below.

### Vehicles — 75 TBDs, still the big one

**The Aug 7 breakdown was wrong** and this is worth knowing before you start: it recorded 64
"loadout option descriptions". The actual split is **55 missing `designation` values** and only
**9 missing `description` values**, plus the 11 `description.text`. The designation is the model
name on the tile (`120mm HEMP-T Round`), so most of this is transcription, not prose.

| Vehicle | TBDs | designation | option description | page description |
|---|---|---|---|---|
| Infantry Fighting Vehicle | 19 | 15 | 3 | 1 |
| Armored Transport | 15 | 10 | 4 | 1 |
| Main Battle Tank | 12 | 10 | 1 | 1 |
| Mobile Anti-Air | 8 | 6 | 1 | 1 |
| Attack Helicopter | 7 | 6 | — | 1 |
| Scout Helicopter | 7 | 6 | — | 1 |
| Patrol Boat | 3 | 2 | — | 1 |
| Attack Jet | 1 | — | — | 1 |
| Fighter Jet | 1 | — | — | 1 |
| Light Ground Transport | 1 | — | — | 1 |
| Transport Helicopter | 1 | — | — | 1 |

- [ ] Fill the **55 loadout `designation`** values — read off each vehicle's own customisation
      screen. **Never share text between vehicles**: the MBT's High Explosive is a 120mm HEMP-T and
      the IFV's is an HEI-T. Role is part of the key too.
- [ ] Fill the **9 loadout option `description`** values, same rule.
- [ ] Fill the **11 vehicle `description.text`** values.

### Weapons — 7 TBDs across 6 items

- [ ] `availability` for the five melee items: **Combat Knife, EOD Bot Arm, Ice Axe, Serrated Blade,
      Sledgehammer**
- **EF88** — 2 TBDs in `compatibility.slots[].options[].name`, *(by design)*: the Compatible
  attachments section was removed Aug 8 and **nothing reads `compatibility`**. These render nowhere.
  They're kept so the captured EF88 grid isn't lost. Not work.

### Modes — 2 TBDs

- [ ] `description.text` for **King of the Hill** and **Rush**. KotH is playable again as of Aug 11,
      so its screen is readable now; Rush is still out of Custom Search.

### Classes — 1 TBD

- [ ] `documented_paths[].abilities[].description` for **Assault** — a training path EA names but no
      capture covers

### Attachments — 1 TBD

- [ ] `description.text` for **Magnifier**

---

## 2. Missing images — 100

Was 101. **Wake Island is now done** — added Aug 12 as a 1500px progressive JPEG (269 KB), matching
where §5 wants the map art to go rather than adding a 24th oversized PNG.

- [ ] **98 attachment pages** have no image at all. Every page under `/attachments/` is text-only.
      Still the biggest single visual gap on the site.
- [ ] **King of the Hill** and **Rush** — the only two modes without one. KotH is back in rotation,
      so it can be captured now.

Vehicle faction variants are all present — both NATO and Pax Armata images resolve for all 11.

---

## 3. Missing `Added in` — 118 items

`data/releases.json` is the only source for this row. 131 slugs are recorded; these are not:

- [ ] **94 attachments** (of 98)
- [ ] **11 vehicles** (all of them)
- [ ] **7 modes** — Breakthrough, Conquest, Domination, Escalation, King of the Hill, Rush,
      Team Deathmatch
- [ ] **4 classes** — Assault, Engineer, Recon, Support
- [ ] **1 gadget** — Long-Range Launcher
- **1 map** — Wake Island, *(by design)*: it's in `scheduled` and must not carry an `Added in`
  until Aug 18. This is the +1 against Aug 7's count of 117; it is not new work.

Most of the rest shipped at launch (`1.0.1.0`), whose entry already warns it is *"not an exhaustive
launch roster."* Filling it is mostly confirming which were launch content and adding them to that
release's `added` array.

---

## 4. Decisions to make (not defects)

- [ ] **The `summary` section gap.** 58 EA "Major Updates for X" lines are joined into one untagged
      paragraph, so **50 tag pairs across 38 items never reach their item page**. The text is on the
      front page verbatim — only the per-item view loses it. Fixing it changes how that quote reads,
      so it's your call. Pre-existing and documented.
- [ ] **80 items have zero tagged patch lines** — 70 attachments, 6 weapons, 2 gadgets, 1 vehicle,
      1 map. Not a defect: EA simply hasn't named them. `check_tags.py` reports 0 unreviewed, so
      coverage is genuinely clean.
- [ ] **Ko-fi on mobile.** At **≤640px** the CSS switches `#kofi-fixed` to `position:static` and
      drops both buttons into the page flow — and the front page is **14,300px tall**, so on a phone
      you'd scroll past all 2,894 patch lines to reach them. Keep them fixed on mobile, or leave
      them parked? Carried over from Aug 7; still undecided.

✅ **Resolved since Aug 7:**
- The three stale "Compatible attachments" rules in `CLAUDE.md` are gone, replaced by one rule
  saying the section was removed and must not be rebuilt.
- The `removed` array shape question is settled — it's blocks of `entries`, and a block may now set
  its own `label`. See the Aug 12 amendment on `docs/adr/0007`.

---

## 5. Performance

- [ ] **Convert 17 map PNGs + `mas-148.png` to JPEG.** **Correction:** Aug 7 said "23 map PNGs".
      There are 23 PNGs in `img/items/`, but only 17 are maps; one more (`mas-148.png`, 469 KB) is a
      gadget photo, and the remaining **6 are 164×164 mode badges** averaging 18 KB, which should
      **stay PNG** — converting them saves nothing and risks artefacts on a small glyph.
      The real target is **18 files, 8.27 MB**, worst offenders `manhattan-bridge` (964 KB),
      `saints-quarter` (885 KB), `liberation-peak` (671 KB). None of the 23 has an alpha channel, so
      nothing breaks. Follow the Wake Island recipe: 1500px, progressive, q82 — that landed at
      269 KB from a 1.19 MB source. Still the biggest user-facing win available.
- [ ] **Fix the item hero `<img>`.** It carries `loading="lazy"` with no `width`/`height`, on all
      249 pages. It's the LCP element and above the fold, so lazy actively delays it, and the
      missing dimensions cause layout shift. Wants `fetchpriority="high"`, no `loading`, explicit
      dimensions. Generator change in `build_pages.py`.
- [ ] **7.91 MB of byte-identical duplicates**, 17 groups (Aug 7 said 7.54 MB). Every group is an
      `img/battlefield-6-map-*-16x9.png` that is the same file as its `img/items/*.png`.
      **Newly verified: nothing references them** — 0 hits across every `.html`, `sitemap.xml` and
      `data/search-index.json`. So the `img/` root copies are safe to delete, which is ~26% of the
      30.9 MB `img/` tree. Costs users nothing; it slows clones and CI checkout.
      *(Deleting them is destructive and unreviewed, so it hasn't been done.)*

Not actionable: GitHub Pages serves gzip only (no brotli) and pins `Cache-Control: max-age=600`.

---

## 6. Verified working — no action

- **Ko-fi and Feedback buttons are both live and correct** on every page. `#kofi-fixed` is
  `position:fixed`, 18px off the bottom-right, Feedback link 113×39 and Ko-fi anchor 185×40 pointing
  at `ko-fi.com/L5V622ZF6S`. The only open question is the mobile behaviour in §4.
- **Community Updates block** — 23 EA posts, in the sidebar on all 250 pages. Reviewed and approved
  Aug 12.
- **Mode availability rows** — Rush and Domination carry a Removed row, King of the Hill a Rotation
  row, Team Deathmatch none (still listed). Recorded Aug 12.
- **All four checks pass**, and `check_tags.py` reports **0 unreviewed** across 249 items and
  2,894 patch lines.
