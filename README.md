# Battlefield 6 — Balance Change Log

A categorized, searchable log of every official BF6 balance change (weapons, vehicles,
gadgets, maps, REDSEC), sourced from EA's own patch note pages. Static HTML, no build step.

Live page once deployed: `https://<you>.github.io/<repo>/`

## How it stays current

This repo does **not** auto-write new entries. Turning a raw EA changelog into clean,
categorized "balance vs. not-balance" entries needs editorial judgment — that part stays
a Claude (or Claude Code) task, on purpose, so the page doesn't silently fill up with
misclassified or hallucinated changes.

What *is* automated:

- `.github/workflows/check-patches.yml` runs daily and checks EA's BF6 news page and the
  EA Forums update board for Game Update version numbers not yet listed in
  `data/known_versions.json`.
- If it finds one, it opens a GitHub issue tagged `new-patch` with a checklist.
- You (or Claude Code) do the actual update: fetch that patch's notes, add the
  balance-relevant entries to `index.html` in the right category, add the version to
  `known_versions.json`, and push.
- Push to `main` → GitHub Pages redeploys automatically. No deploy workflow needed for
  that part — it's a single static file.

## One-time setup

1. Create a new **public** GitHub repo (Pages on the free tier requires public; private
   repos need GitHub Pro/Team).
2. From this folder:
   ```bash
   git init
   git add .
   git commit -m "BF6 balance log + patch-check bot"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
3. **Settings → Pages → Build and deployment → Source: "Deploy from a branch" →
   Branch: `main`, folder `/ (root)`.** Save. The page goes live at
   `https://<you>.github.io/<repo>/` within a minute or two.
4. **Settings → Actions → General → Workflow permissions → "Read and write
   permissions."** Needed so the bot can open issues with the built-in `GITHUB_TOKEN`
   (no extra secret required).
5. Done. The checker runs daily at 14:00 UTC, or trigger it manually any time from the
   **Actions** tab → "Check for new BF6 patches" → **Run workflow**.

## Connecting bf6balancelog.com (bought via Cloudflare)

Domain's already sitting in Cloudflare DNS since you bought it there. Two things to do,
one on each side:

**In Cloudflare (dashboard → your domain → DNS → Records → Add record):**

| Type | Name | Content | Proxy status |
|------|------|---------|--------------|
| CNAME | `www` | `<you>.github.io` | DNS only (grey cloud) |
| A | `@` | `185.199.108.153` | DNS only (grey cloud) |
| A | `@` | `185.199.109.153` | DNS only (grey cloud) |
| A | `@` | `185.199.110.153` | DNS only (grey cloud) |
| A | `@` | `185.199.111.153` | DNS only (grey cloud) |

Important: click the orange cloud icon on each record to turn it **grey ("DNS only")**.
Leaving it orange (proxied) can break GitHub's automatic HTTPS certificate.

**In GitHub (repo → Settings → Pages):**

1. Under "Custom domain," type `bf6balancelog.com`, hit Save. GitHub commits a
   `CNAME` file to the repo automatically.
2. Wait a few minutes to a couple hours for the DNS check to go green.
3. Once it does, tick **"Enforce HTTPS"** (may take a bit to become available — GitHub
   is issuing a free cert behind the scenes).
4. Optionally add `www.bf6balancelog.com` as well and pick which one redirects to the
   other in GitHub's settings.

After that, `bf6balancelog.com` and `<you>.github.io/<repo>` both serve the same site.

**Optional: Cloudflare Web Analytics** — since Cloudflare doesn't proxy these DNS
records (they're DNS-only, not orange-clouded), you don't get Cloudflare's one-click
Pages analytics. You can still get free analytics by adding the domain under Cloudflare
dashboard → **Analytics & Logs → Web Analytics → Add a site**, then pasting the small
JS snippet it gives you into `index.html`'s `<head>`.


## Updating when the bot flags a patch

1. Open the flagged issue — it links the version number.
2. Ask Claude (or Claude Code) to pull that patch's official notes and pick out the
   balance-relevant changes (weapon/vehicle/gadget/mode numeric or behavioral changes —
   not bug fixes, cosmetics, audio, or Portal scripting).
3. Add a new `<details class="patch">` block to each relevant category section in
   `index.html`, following the existing markup, plus a row in the Patch Index table at
   the top.
4. Add the version string to `data/known_versions.json`.
5. Commit and push to `main`. Close the issue (or let it stay for your own record).

## Files

```
index.html                             the page itself
data/known_versions.json               versions already logged — the bot's memory
scripts/check_patches.py               stdlib-only checker, no pip install needed
.github/workflows/check-patches.yml    daily cron + manual trigger
```

## Known limitation

`check_patches.py` does a plain HTTP fetch — no JavaScript rendering. If EA ever moves
either source to a client-side-only listing, the bot could miss a patch silently. Worth
glancing at `ea.com/games/battlefield/battlefield-6/news` yourself now and then as a
backstop, especially around season launches.
