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

## 1. TBD values — 30 across 20 items

**Was 86 on Aug 12 morning. The Aug 12 captures and the designation rule cleared 56 of them.**

**Most of the vehicle pile was never real work.** 50 of the 55 missing `designation` values were on
Equipment and Upgrade tiles, which *have no designation* — the screen prints a name and a
description and nothing else. Across all 11 vehicles those slots held 50 options and not one ever
had a real designation, while the weapon and ammo slots held 49. The key is now absent on them and
the Designation column drops per slot. See the rule in `CLAUDE.md`.

### Vehicles — 20 TBDs (was 75)

| Vehicle | TBDs | designation | option description | page description |
|---|---|---|---|---|
| Armored Transport | 7 | 2 | 4 | 1 |
| Main Battle Tank | 3 | 1 | 1 | 1 |
| Mobile Anti-Air | 2 | — | 1 | 1 |
| Attack Helicopter, Attack Jet, Fighter Jet, IFV, Light Ground Transport, Patrol Boat, Scout Helicopter, Transport Helicopter | 1 each | — | — | 1 each |

- [ ] Fill the **11 vehicle `description.text`** values — now the bulk of what's left.
- [ ] Fill the **6 loadout option `description`** values (4 Armored Transport, 1 MBT, 1 Mobile
      Anti-Air). **Never share text between vehicles**: the MBT's High Explosive is a 120mm HEMP-T
      and the IFV's is an HEI-T. Role is part of the key too.
- [ ] Fill the **3 remaining `designation` values**, all in real weapon slots so they genuinely
      exist: Armored Transport's Light Machine Gun and Grenade Launcher (Gunner / Remote Weapon),
      and the MBT's Coaxial HMG (Driver / Secondary).

✅ **Infantry Fighting Vehicle is complete** — 0 TBDs. The Aug 12 captures filled the Remote Weapon
LMG (`RWS 7.62mm MG`) and Grenade Launcher (`RWS 40mm AGL`) and the Gunner Countermeasures
description; the rest were the designation drop.

### Weapons — 7 TBDs across 6 items

- [ ] `availability` for the five melee items: **Combat Knife, EOD Bot Arm, Ice Axe, Serrated Blade,
      Sledgehammer**
- **EF88** — 2 TBDs in `compatibility.slots[].options[].name`, *(by design)*: the Compatible
  attachments section was removed Aug 8 and **nothing reads `compatibility`**. These render nowhere.
  They're kept so the captured EF88 grid isn't lost. Not work.

### Modes — 1 TBD (was 2)

- [ ] `description.text` for **Rush** — still out of Custom Search, so the screen isn't readable.
- ✅ **King of the Hill** filled from the Aug 12 Custom Search capture: *"Battle for control over
  multiple objectives that activate across the combat area."*

### Classes — 1 TBD

- [ ] `documented_paths[].abilities[].description` for **Assault** — this is the **Hazmat Breacher**,
      a Battle Royale field upgrade EA named in `1.2.3.0` and `1.3.1.0` but never captured. The
      Aug 12 captures do **not** cover it; Breacher and Frontliner were already complete and the
      captures match them exactly. Needs the REDSEC field-upgrade screen, not the class screen.

### Attachments — 1 TBD

- [ ] `description.text` for **Magnifier**

---

## 2. Missing images — 100

Was 101. **Wake Island is now done** — added Aug 12 as a 1500px progressive JPEG (269 KB), matching
where §5 wants the map art to go rather than adding a 24th oversized PNG.

- [ ] **98 attachment pages** have no image at all. Every page under `/attachments/` is text-only.
      **Owner's leaning as of Aug 12: probably not doing this.** 98 crops is a lot of work for
      small parts that mostly look alike, and the pages read fine without art. Left open rather
      than closed — undecided, not rejected.
- [ ] **King of the Hill** and **Rush** — the only two modes without one. KotH is back in rotation,
      so it can be captured now.

Vehicle faction variants are all present — both NATO and Pax Armata images resolve for all 11.

---

## 2b. Open questions from the Aug 12 captures

- ✅ **REDSEC classes shipped Aug 12 as an "In REDSEC" section on each class page.** Owner's choice
      of the three options. Assault, Engineer and Support each carry a `redsec` block —
      signature set, the `Stockpile` passive, the three-ability training track, and the shared
      Universal Equipment rows — transcribed from captures `20260812180236` / `180241` / `180245`.
      Rule in `CLAUDE.md`.
- [ ] **Capture the REDSEC Recon class.** The only one of the four missing. Its page deliberately
      has **no** In REDSEC section rather than a guessed one, so the gap is currently invisible to
      a reader — worth closing next time you're in a Battle Royale lobby.
- [ ] **The 7.7M NSW RHIB has no page, and may deserve one.** Confirmed by the owner as a new boat
      at the Season 4 launch (`1.4.1.0`, Jul 16 2026), alongside the RCB-90 Patrol Boat and Tsuru
      Reef. It is a drivable vehicle with its own handling — `1.2.3.0` alone carries three lines
      about RHIB handling, speed gauges and hull simulation — but the `vehicles` branch is one page
      per class and this class has none, so those lines point nowhere. Decide whether it is its own
      class page. (A RHIB is referenced from `1.1.2.0`, so the earlier boat and the 7.7M NSW model
      are not the same thing; a page would need to say which it covers.)
- ✅ **The Pax Armata Scout Helicopter name is correct as-is — resolved Aug 12.** The variant stays
      **MD530 Cayuse**: the owner confirmed that is what the game currently displays, and the game
      is the source for item names. EA's notes disagree — `1.2.2.0` writes "MH350 Scout Helicopter
      (PAX)" and `1.3.2.0` says *"Naming for the PAX Scout Helicopter has been updated to display
      its correct name, MH-350"* — but that is exactly the case the alias rule exists for, and
      `mh-350` and `mh350` were **already** in the item's aliases, so every patch line naming
      MH-350 already resolves to this page. No conflict and nothing to change. Don't "fix" this
      later off the changelog.

---

## 3. Missing `Added in` — 116 items

`data/releases.json` is the only source for this row. 131 slugs are recorded; these are not:

- [ ] **94 attachments** (of 98)
- [ ] **9 vehicles** (was 11)
- [ ] **7 modes** — Breakthrough, Conquest, Domination, Escalation, King of the Hill, Rush,
      Team Deathmatch
- [ ] **4 classes** — Assault, Engineer, Recon, Support
- [ ] **1 gadget** — Long-Range Launcher
- **1 map** — Wake Island, *(by design)*: it's in `scheduled` and must not carry an `Added in`
  until Aug 18. Not work.

✅ **Two filled Aug 12, from the patch notes rather than memory:**
- **Scout Helicopter → `1.2.1.0` (Extreme Measures).** Both faction models shipped in that update —
  `AH-6 Little Bird: The iconic attack helicopter returns for NATO forces` and the MH-350 for Pax
  Armata — and patch lines reference it continuously from `1.2.2.0`. The slug sits on the Little
  Bird entry; a class page covers both factions, so either would give the same answer.
- **Patrol Boat → `1.4.1.0` (Pacific Front).** The page's model is the **RCB-90**, listed there.
  Note this is Season 4, not Season 3. The `7.7M NSW RHIB` in the same update deliberately has **no
  slug**: a RHIB appears in patch lines from `1.1.2.0`, so it is a model shipping in `1.4.1.0`
  rather than the first boat, and it is not the Patrol Boat.

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
