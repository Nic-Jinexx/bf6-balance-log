#!/usr/bin/env python3
"""Build the BF6 Balance Log item database.

Reads
  data/tree.json        navigation structure, which is also the URL structure
  data/items/*.json     one file per item
  index.html            patch content: any <li>/<tr> carrying data-item="<slug>"

Writes
  <branch>/[<sub>/]<slug>/index.html   one page per item
  <retired path>/index.html            redirect stub for an item that moved
  data/search-index.json               item lookup used by the search bar
  sitemap.xml                          home page plus every item page
  index.html                           the tree only, between the TREE markers

Stdlib only, on purpose: nothing in this repo may need a pip install.
Safe to re-run. Output is deterministic, so a run with no data change
produces no diff.

Usage:  python scripts/build_pages.py [--check]
        --check  build into memory and report, write nothing (exit 1 on drift)
"""

import html
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://bf6balancelog.com"

TREE_START = "<!-- TREE:START -->"
TREE_END = "<!-- TREE:END -->"

# Where "back to the full balance log" points when an item has no tagged entries
# to borrow a section from. Several branches share a log section: the log's
# "Individual Weapons & Attachments" covers both, and "Maps & Mode Balance"
# covers both maps and modes.
BRANCH_ANCHOR = {
    "weapons": "weapons",
    "attachments": "weapons",
    "gadgets": "gadgets",
    "vehicles": "vehicles",
    "maps": "maps",
    "modes": "maps",
    "classes": "progression",
}

# section id in index.html -> (readable label, color class used by h2.cat/.tag)
SECTIONS = {
    "systemic": ("systemic gunplay", "systemic"),
    "player": ("player & movement", "player"),
    "weapons": ("weapons", "weapons"),
    "vehicles": ("vehicles", "vehicles"),
    "gadgets": ("gadgets", "gadgets"),
    "maps": ("maps & modes", "maps"),
    "redsec": ("REDSEC", "redsec"),
    "progression": ("progression", "progression"),
}

# tree branch -> the category color it borrows, so the database speaks the
# same color language as the log. No new hues are introduced.
BRANCH_COLOR = {
    "patchnotes": "patchnotes",
    "weapons": "weapons",
    "attachments": "weapons",
    "gadgets": "gadgets",
    "vehicles": "vehicles",
    "classes": "systemic",
    "maps": "maps",
    "modes": "maps",
}

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


# --------------------------------------------------------------------------
# reading index.html
# --------------------------------------------------------------------------

class LogParser(HTMLParser):
    """Pulls every data-item tagged <li>/<tr> out of index.html.

    For each one it recovers the version and date from the enclosing
    <details class="patch">, the section from the nearest <h2 class="cat">
    with an id, and for table rows the parent table's caption and header
    cells so the row can be rebuilt with its columns labelled.

    That markup shape is load-bearing: restructuring the patch blocks in
    index.html breaks extraction. See docs/adr/0002.
    """

    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.raw = raw
        self.line_start = [0]
        for i, ch in enumerate(raw):
            if ch == "\n":
                self.line_start.append(i + 1)
        self.section = None
        self.patch = None
        self.patch_depth = 0
        self.in_summary = False
        self.span_kind = None
        self.tables = []
        self.cap_capture = False
        self.th_capture = False
        self.capture = None
        self.entries = []

    def _offset(self, pos):
        line, col = pos
        return self.line_start[line - 1] + col

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()

        if self.capture is not None and tag == self.capture["tag"]:
            self.capture["depth"] += 1

        if tag == "h2" and "cat" in classes and a.get("id"):
            self.section = a["id"]

        if tag == "details":
            if "patch" in classes and self.patch is None:
                self.patch = {"ver": "", "date": "", "section": self.section}
                self.patch_depth = 0
            elif self.patch is not None:
                self.patch_depth += 1

        if tag == "summary" and self.patch is not None and self.patch_depth == 0:
            self.in_summary = True
        if tag == "span" and self.in_summary:
            if "ver" in classes:
                self.span_kind = "ver"
            elif "date" in classes:
                self.span_kind = "date"

        if tag == "table":
            self.tables.append({"caption": "", "headers": []})
        if tag == "caption" and self.tables:
            self.cap_capture = True
        if tag == "th" and self.tables:
            self.th_capture = True
            self.tables[-1]["headers"].append("")

        if "data-item" in a and self.capture is None:
            table = None
            if tag == "tr" and self.tables:
                table = {
                    "caption": self.tables[-1]["caption"].strip(),
                    "headers": [h.strip() for h in self.tables[-1]["headers"]],
                }
            self.capture = {
                "tag": tag,
                "depth": 1,
                "start": self._offset(self.getpos()),
                "slugs": a["data-item"].split(),
                "patch": self.patch,
                "table": table,
            }

    def handle_endtag(self, tag):
        if self.capture is not None and tag == self.capture["tag"]:
            self.capture["depth"] -= 1
            if self.capture["depth"] == 0:
                end = self._offset(self.getpos()) + len("</%s>" % tag)
                cap = self.capture
                patch = cap["patch"] or {"ver": "", "date": "", "section": None}
                for slug in cap["slugs"]:
                    self.entries.append({
                        "slug": slug,
                        "tag": cap["tag"],
                        "html": self.raw[cap["start"]:end],
                        "version": patch["ver"].strip(),
                        "date": patch["date"].strip(),
                        "section": patch["section"],
                        "table": cap["table"],
                    })
                self.capture = None

        if tag == "details":
            if self.patch is not None and self.patch_depth > 0:
                self.patch_depth -= 1
            else:
                self.patch = None
        elif tag == "summary":
            self.in_summary = False
        elif tag == "span":
            self.span_kind = None
        elif tag == "table":
            if self.tables:
                self.tables.pop()
        elif tag == "caption":
            self.cap_capture = False
        elif tag == "th":
            self.th_capture = False

    def handle_data(self, data):
        if self.span_kind and self.patch is not None:
            self.patch[self.span_kind] += data
        if self.cap_capture and self.tables:
            self.tables[-1]["caption"] += data
        if self.th_capture and self.tables and self.tables[-1]["headers"]:
            self.tables[-1]["headers"][-1] += data


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write_text(path, text):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


MONTHS = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), start=1)}


def iso_date(date_text):
    """'Jul 16, 2026' -> '2026-07-16' for <lastmod>. None if unparseable, which
    just drops the hint rather than emitting a wrong or invented date."""
    m = re.match(r"([A-Za-z]{3})[a-z]*\s+(\d{1,2}),\s*(\d{4})", (date_text or "").strip())
    if not m or m.group(1).title() not in MONTHS:
        return None
    return "%s-%02d-%02d" % (m.group(3), MONTHS[m.group(1).title()], int(m.group(2)))


def version_key(v):
    parts = re.findall(r"\d+", v or "")
    return tuple(int(p) for p in parts) or (0,)


# --------------------------------------------------------------------------
# tree
# --------------------------------------------------------------------------

def item_url(item):
    if item.get("subcategory"):
        return "/%s/%s/%s/" % (item["branch"], item["subcategory"], item["slug"])
    return "/%s/%s/" % (item["branch"], item["slug"])


def render_tree(tree, items_by_place, current_url):
    """Tree markup for one page. Uses <details>/<summary> so it expands with
    no JavaScript at all; the branch containing the current page is opened."""
    out = ['<nav class="tree-nav" aria-label="Item database">',
           # icon only, no wordmark, so the img carries the accessible name
           '<a class="tree-brand" href="/" title="BF6 Balance Log">'
           '<img src="/icon-192.png" alt="BF6 Balance Log, home" '
           'width="48" height="48"></a>']

    for branch in tree["branches"]:
        bkey = branch["key"]
        color = BRANCH_COLOR.get(bkey, "weapons")

        # a link branch is a jump, not an expandable node: it holds no items
        if branch.get("link"):
            cur = ' aria-current="page"' if current_url == branch["link"] else ""
            out.append('<a class="branch-link b-%s" href="%s"%s>%s</a>'
                       % (bkey, branch["link"], cur, html.escape(branch["label"])))
            continue

        if branch.get("flat"):
            groups = [(None, None, items_by_place.get((bkey, None), []))]
        else:
            groups = [(c["key"], c["label"], items_by_place.get((bkey, c["key"]), []))
                      for c in branch.get("children", [])]
        total = sum(len(g[2]) for g in groups)
        branch_open = any(any(i["url"] == current_url for i in g[2]) for g in groups)

        out.append('<details class="branch b-%s"%s>' % (bkey, " open" if branch_open else ""))
        out.append('<summary>%s<span class="cnt">%d</span></summary>'
                   % (html.escape(branch["label"]), total))

        for subkey, sublabel, entries in groups:
            if subkey is None:
                out.extend(_leaves(entries, current_url))
                continue
            sub_open = any(i["url"] == current_url for i in entries)
            cls = "sub" if entries else "sub empty"
            out.append('<details class="%s"%s>' % (cls, " open" if sub_open else ""))
            out.append('<summary>%s<span class="cnt">%d</span></summary>'
                       % (html.escape(sublabel), len(entries)))
            out.extend(_leaves(entries, current_url))
            out.append("</details>")

        out.append("</details>")

    out.append("</nav>")
    return "\n".join(out)


def leaf_order(item):
    """In-game order, not alphabetical. Items without an explicit `order` sort
    after the ordered ones, which is where a newly added weapon belongs."""
    return (item.get("order") if isinstance(item.get("order"), int) else 10 ** 6,
            item["name"].lower())


def _leaves(entries, current_url):
    if not entries:
        return ['<div class="leaf-none">nothing catalogued yet</div>']
    rows = []
    for it in sorted(entries, key=leaf_order):
        cur = ' aria-current="page"' if it["url"] == current_url else ""
        rows.append('<a class="leaf" href="%s"%s>%s</a>'
                    % (it["url"], cur, html.escape(it["name"])))
    return rows


def inject_tree(page_html, tree_html):
    start = page_html.find(TREE_START)
    end = page_html.find(TREE_END)
    if start == -1 or end == -1:
        raise ValueError("tree markers missing")
    return (page_html[:start + len(TREE_START)] + "\n" + tree_html + "\n"
            + page_html[end:])


# --------------------------------------------------------------------------
# item page
# --------------------------------------------------------------------------

PAGE_CSS = """
.crumb{font-family:var(--mono);font-size:13px;color:var(--dim);margin:20px 0 0;letter-spacing:.3px}
.crumb a{color:var(--muted);text-decoration:none}
.crumb a:hover{color:var(--text)}
header.itemhead{border-bottom:1px solid var(--border);padding:14px 0 24px;margin-bottom:0}
header.itemhead h1{margin:10px 0 0}
/* gadgets lead with the model designation EA's notes use; the in-game name rides underneath */
header.itemhead p.itemsub{margin:5px 0 0;font-family:var(--mono);font-size:14px;color:var(--muted);
  text-transform:uppercase;letter-spacing:.6px}
.descblock{margin:20px 0 0;max-width:760px}
.desclabel{font-family:var(--mono);font-size:12.5px;font-weight:600;text-transform:uppercase;
  letter-spacing:.7px;color:var(--dim);margin:0 0 7px}
blockquote.ingame{margin:0;padding:8px 0 8px 16px;border-left:3px solid var(--border2);
  color:var(--text);font-size:16.5px}
.tbd{color:var(--dim);font-style:italic}
.traits{display:flex;flex-wrap:wrap;gap:7px;margin:13px 0 0}
.traits span{font-family:var(--mono);font-size:12px;text-transform:uppercase;letter-spacing:.5px;
  color:var(--muted);border:1px solid var(--border2);border-radius:3px;padding:4px 10px;background:var(--panel)}
/* square ends, and vertically centred: the global td rule is vertical-align:top,
   which left the bar riding above its label */
.factbox table.ratings td{vertical-align:middle}
.factbox table.ratings td:nth-child(2){width:100%;padding:6px 12px}
.factbox table.ratings td:last-child{width:1%}
.bar{display:block;height:7px;background:rgba(255,255,255,.09);overflow:hidden}
.bar i{display:block;height:100%}
.itemgrid{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:24px;
  margin:26px 0 4px;align-items:start}
/* no fact box to sit beside: let the art use the full width instead of leaving
   a dead column, and cap it so a 2-up does not tower over the page */
.itemgrid.solo{grid-template-columns:minmax(0,1fr)}
.itemgrid.solo .itemart{flex-direction:row;flex-wrap:wrap}
.itemgrid.solo figure.itemimg{flex:1 1 320px;min-width:0}
/* one figure normally, stacked figures when a page covers two faction variants */
.itemart{display:flex;flex-direction:column;gap:14px}
figure.itemimg{margin:0}
figure.itemimg img{width:100%;height:auto;display:block;border:1px solid var(--border);
  border-radius:6px;background:var(--panel)}
figure.itemimg figcaption{font-family:var(--mono);font-size:12px;color:var(--dim);margin-top:8px}
/* Mode badges. The game draws these as a small square glyph beside GAME MODE,
   so they keep that scale instead of being stretched across the art column, and
   opt out of the solo grid's flex-grow. */
figure.itemimg.icon{flex:0 0 auto}
figure.itemimg.icon img{width:104px;height:104px;border-radius:5px}
figure.itemimg.icon .imgpending{width:104px;height:104px;aspect-ratio:auto;padding:8px;gap:4px}
figure.itemimg.icon .imgpending b{font-size:12px;line-height:1.2}
figure.itemimg.icon .imgpending span{font-size:11px}
.imgpending{aspect-ratio:16/9;border:1px dashed var(--border2);border-radius:6px;background:var(--panel);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;
  color:var(--dim);font-family:var(--mono);font-size:13px;text-align:center;padding:16px}
.imgpending b{color:var(--muted);font-size:16px;font-weight:600;letter-spacing:.4px}
/* No horizontal padding on the box itself: the inset lives on the cells instead,
   so a striped row's background runs the full width of the panel rather than
   stopping 16px short on each side. overflow:hidden keeps a stripe from
   spilling past the rounded corners. */
.factbox{background:var(--panel);border:1px solid var(--border);border-radius:6px;
  padding:2px 0 14px;overflow:hidden}
.factbox h3{font-family:var(--mono);font-size:12.5px;text-transform:uppercase;letter-spacing:.6px;
  color:var(--dim);margin:16px 0 0;padding:0 16px;font-weight:600}
.factbox .emptynote{padding:0 16px}
.factbox table{margin:8px 0 2px}
.factbox td{padding:6px 0}
.factbox td:first-child{color:var(--muted);padding-left:16px}
.factbox td:last-child{font-family:var(--mono);text-align:right;color:var(--text);padding-right:16px}
/* a challenge with several tasks: left aligned and wrapping, since right-aligned
   mono prose is unreadable. Must follow the :last-child rule to win on order.
   padding-left is load-bearing: the label column shrinks to fit its text, so
   without it a wrapping task butts straight against the word "Requirement". */
.factbox td.stack{text-align:left;font-family:var(--sans);white-space:normal;
  padding-top:9px;padding-bottom:9px;padding-left:18px}
.factbox tr.stackrow td:first-child{vertical-align:top;padding-top:11px}
.factbox td.stack .req{display:block;font-size:14px;line-height:1.4}
.factbox td.stack .req + .req{margin-top:5px}
.emptynote{color:var(--dim);font-style:italic;font-size:14.5px;margin:12px 0 0}
.relgroup{margin:14px 0 0}
.relgroup h4{font-family:var(--mono);font-size:12.5px;text-transform:uppercase;letter-spacing:.5px;
  color:var(--dim);margin:0 0 6px;font-weight:600}
.relgroup a{color:var(--text)}
/* Vehicle loadouts. A slot is a table rather than a list because every option
   carries three fields, and most of them are TBD until the option is captured. */
.lo-role{margin:22px 0 0}
.lo-role > h3{font-family:var(--mono);font-size:13px;font-weight:600;text-transform:uppercase;
  letter-spacing:.9px;color:var(--vehicles);margin:0 0 2px}
.lo-slot{margin:14px 0 0}
.lo-slot > h4{font-family:var(--mono);font-size:12.5px;font-weight:600;text-transform:uppercase;
  letter-spacing:.5px;color:var(--dim);margin:0 0 6px}
.lo-slot table{margin:0}
.lo-slot td:first-child{white-space:nowrap;color:var(--text)}
.lo-slot td:nth-child(2){font-family:var(--mono);font-size:13px;color:var(--muted);white-space:nowrap}
.lo-locked{color:var(--dim);font-style:italic;font-size:14.5px;margin:0}
.lo-locked b{color:var(--muted);font-style:normal}
/* Class training paths. The ability table is the same three-column shape as a
   loadout slot, so it reuses .lo-slot; only the group heading and the path's own
   blurb are new. The heading takes the systemic hue because that is the color the
   classes branch borrows in BRANCH_COLOR. */
.tp-path{margin:22px 0 0}
.tp-path > h3{font-family:var(--mono);font-size:13px;font-weight:600;text-transform:uppercase;
  letter-spacing:.9px;color:var(--systemic);margin:0 0 2px}
.tp-desc{color:var(--muted);font-size:14.5px;margin:6px 0 10px;max-width:70ch}
.backlog{margin-top:26px;font-family:var(--mono);font-size:14px}
.backlog a{color:var(--vehicles);text-decoration:none}
.backlog a:hover{text-decoration:underline}
/* the shared rule turns every table into its own scroll box below 1100px, which
   is right for wide patch tables but collapses this two-column one to content
   width. Opt the fact box back out; it never needs to scroll. */
@media (max-width:1100px){
  .factbox table{display:table;width:100%;background-image:none}
}
@media (max-width:900px){.itemgrid{grid-template-columns:1fr}}
@media (max-width:640px){
  header.itemhead h1{font-size:22px}
  blockquote.ingame{font-size:15.5px}
  .factbox{padding:2px 12px 12px}
}
"""

PAGE_JS = """
(function(){
  var input = document.getElementById('searchInput');
  var box = document.getElementById('searchSuggestions');
  if (!input || !box || !window.fetch) return;
  var items = [], hits = [], active = -1;

  fetch('/data/search-index.json').then(function(r){ return r.ok ? r.json() : null; })
    .then(function(d){ if (d && d.items) items = d.items; }).catch(function(){});

  function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function mark(term, q){
    var p = term.toLowerCase().indexOf(q);
    if (p === -1) return esc(term);
    return esc(term.slice(0,p)) + '<mark class="hl">' + esc(term.slice(p,p+q.length)) +
           '</mark>' + esc(term.slice(p+q.length));
  }
  function render(q){
    if (!q){ box.classList.remove('show'); box.innerHTML=''; hits=[]; active=-1; return; }
    var starts = [], contains = [];
    items.forEach(function(it){
      var hay = (it.name + ' ' + (it.alt || '')).toLowerCase();
      if (hay.indexOf(q) === -1) return;
      (it.name.toLowerCase().indexOf(q) === 0 ? starts : contains).push(it);
    });
    var byLen = function(a,b){ return a.name.length - b.name.length; };
    starts.sort(byLen); contains.sort(byLen);
    hits = starts.concat(contains).slice(0, 8);
    active = -1;
    if (!hits.length){
      box.innerHTML = '<div class="sug-empty">No matching item. ' +
        '<a href="/" style="color:inherit">Search the full log</a>.</div>';
      box.classList.add('show'); return;
    }
    box.innerHTML = '<div class="sug-head">Database</div>' + hits.map(function(it,i){
      return '<div class="sug-item sug-goto" onmousedown="location.href=\\''+it.url+'\\'">' +
             '<span class="sug-term">' + mark(it.name, q) + '</span>' +
             '<span class="sug-cat">' + esc(it.cat) + '</span></div>';
    }).join('');
    box.classList.add('show');
  }
  function setActive(i){
    var els = box.querySelectorAll('.sug-item');
    els.forEach(function(e){ e.classList.remove('active'); });
    if (i >= 0 && i < els.length){ els[i].classList.add('active'); els[i].scrollIntoView({block:'nearest'}); }
    active = i;
  }
  window.handleSearchInput = function(v){
    var q = v.trim().toLowerCase();
    document.getElementById('searchClear').classList.toggle('show', q !== '');
    render(q);
  };
  window.handleSearchKeydown = function(e){
    var open = box.classList.contains('show') && hits.length;
    if (e.key === 'ArrowDown' && open){ e.preventDefault(); setActive(Math.min(active+1, hits.length-1)); }
    else if (e.key === 'ArrowUp' && open){ e.preventDefault(); setActive(Math.max(active-1, 0)); }
    else if (e.key === 'Enter'){
      if (open && active >= 0){ e.preventDefault(); location.href = hits[active].url; }
      else if (input.value.trim()){ location.href = '/?q=' + encodeURIComponent(input.value.trim()); }
    }
    else if (e.key === 'Escape'){ box.classList.remove('show'); }
  };
  window.clearBalanceSearch = function(){
    input.value = ''; render(''); document.getElementById('searchClear').classList.remove('show');
    input.focus();
  };
  document.addEventListener('click', function(e){
    var bar = document.querySelector('.searchbar');
    if (bar && !bar.contains(e.target)) box.classList.remove('show');
  });
})();
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e0c">
<title>{{TITLE}}</title>
<meta name="description" content="{{DESC}}">
<link rel="canonical" href="{{CANONICAL}}">
<meta property="og:type" content="article">
<meta property="og:title" content="{{OGTITLE}}">
<meta property="og:description" content="{{DESC}}">
<meta property="og:url" content="{{CANONICAL}}">
<meta property="og:site_name" content="BF6 Balance Log">
<meta property="og:image" content="{{OGIMAGE}}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{OGTITLE}}">
<meta name="twitter:description" content="{{DESC}}">
<meta name="twitter:image" content="{{OGIMAGE}}">
<script type="application/ld+json">
{{JSONLD}}
</script>
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" type="image/png" href="/icon-192.png" sizes="192x192">
<link rel="icon" type="image/png" href="/icon-512.png" sizes="512x512">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>
{{CSS}}
</style>
<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "2ed16d9d96844272bd6103453ef7aefc"}'></script><!-- End Cloudflare Web Analytics -->
</head>
<body>
<input type="checkbox" id="treeToggle" aria-label="Toggle database navigation">
<label for="treeToggle" class="treeScrim" aria-hidden="true"></label>

<div class="layout">

<aside class="tree" aria-label="Database navigation">
<!-- TREE:START -->
<!-- TREE:END -->
</aside>

<div class="wrap">

<label for="treeToggle" class="treeBtn">&#9776; Browse database</label>

<nav class="crumb"><a href="/">Balance Log</a> / {{CRUMB}}</nav>

<header class="top itemhead">
<h1>{{NAME}}</h1>
{{SUBTITLE}}
{{TRAITS}}
{{QUOTE}}
</header>

<div class="searchbar">
<span class="icon">&#128269;</span>
<input type="text" id="searchInput" aria-label="Search the database" placeholder="Search the database&hellip;" autocomplete="off"
  oninput="handleSearchInput(this.value)"
  onkeydown="handleSearchKeydown(event)"
  onfocus="handleSearchInput(this.value)">
<span id="searchClear" onclick="clearBalanceSearch()">&times;</span>
<div id="searchSuggestions" class="suggestions"></div>
</div>

<div class="itemgrid{{GRIDMOD}}">
<div class="itemart">{{IMAGE}}</div>
{{FACTBOX}}
</div>

{{LOADOUT}}
{{PATHS}}
{{OPTIONS}}

<h2 class="cat {{COLOR}}" id="history"><span class="dot"></span>Patch history</h2>
<p class="cat-note">{{HISTNOTE}}</p>
{{HISTORY}}

{{RELATED}}

<p class="backlog"><a href="/#{{SECTIONANCHOR}}">&larr; Back to the full balance log</a></p>

<footer>
<p class="disclaimer" style="margin-top:0">This is unofficial fan content. It is not affiliated with, endorsed by, or sponsored by Electronic Arts, DICE, Battlefield Studios, Ripple Effect, or Criterion. Battlefield&trade;, REDSEC&trade;, and all related names, weapons, and trademarks are the property of their respective owners.</p>
<p>Patch entries on this page are the {{NAME}} lines from EA's official Game Update notes, reproduced exactly as published and linked to their source in the <a href="/">full log</a>. Any in-game description is quoted and attributed.</p>
</footer>

</div><!-- /.wrap -->
</div><!-- /.layout -->

<script>
{{JS}}
</script>

<div id="kofi-fixed">
<a class="feedback-btn" href="mailto:feedback@bf6balancelog.com?subject=BF6%20Balance%20Log%20feedback" title="Send feedback">&#9993; Feedback</a>
</div>
</body>
</html>
"""

REDIRECT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Moved: {{NAME}}</title>
<link rel="canonical" href="{{TARGET}}">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={{PATH}}">
</head>
<body>
<p>This page moved to <a href="{{PATH}}">{{PATH}}</a>.</p>
</body>
</html>
"""


def find_image(slug):
    for ext in IMAGE_EXTS:
        rel = "img/items/%s%s" % (slug, ext)
        if os.path.isfile(os.path.join(ROOT, rel)):
            return "/" + rel
    return None


def render_traits(item):
    traits = item.get("traits") or []
    if not traits:
        return ""
    return ('<div class="traits">%s</div>'
            % "".join("<span>%s</span>" % html.escape(t) for t in traits))


def render_subtitle(item):
    """The in-game display name, when the page leads with a model designation instead."""
    text = (item.get("blurb") or "").strip()
    if not text:
        return ""
    return '<p class="itemsub">%s</p>' % html.escape(text)


def render_facts(item, color, signature=None, added_in=None, klass=None, removed=None):
    out = []
    stats = item.get("stats") or []
    if stats:
        as_of = item.get("stats_as_of") or "TBD"
        out.append("<h3>Stats <span class=\"tbd\" style=\"text-transform:none;letter-spacing:0\">"
                   "as of %s</span></h3>" % html.escape(as_of))
        out.append("<table>")
        for row in stats:
            out.append("<tr><td>%s</td><td>%s</td></tr>"
                       % (html.escape(row.get("label", "")), value_cell(row.get("value"))))
        out.append("</table>")
    # the game shows these as 0-100 bars, so a bare number would lose the scale
    ratings = item.get("ratings") or []
    if ratings:
        out.append("<h3>Ratings</h3><table class=\"ratings\">")
        for row in ratings:
            try:
                pct = max(0, min(100, int(row.get("value"))))
            except (TypeError, ValueError):
                continue
            out.append('<tr><td>%s</td><td><span class="bar">'
                       '<i style="width:%d%%;background:var(--%s)"></i></span></td>'
                       '<td>%d</td></tr>'
                       % (html.escape(row.get("label", "")), pct, color, pct))
        out.append("</table>")

    # the subcategory supplies the signature class unless the item overrides it
    avail = [dict(r) for r in (item.get("availability") or [])]
    # data/releases.json is authoritative for Added in when it covers this item
    if added_in:
        if not any((r.get("label") or "").strip().lower() == "added in" for r in avail):
            avail.append({"label": "Added in", "value": added_in})
        for r in avail:
            if (r.get("label") or "").strip().lower() == "added in":
                r["value"] = added_in
    # ...and for Removed, which has no version because EA never published one.
    # The value is the literal string from releases.json, so nothing is assembled
    # here. It goes last: the page reads added, then gone.
    if removed:
        avail = [r for r in avail
                 if (r.get("label") or "").strip().lower() != "removed"]
        avail.append({"label": "Removed", "value": removed})
    if signature and not any((r.get("label") or "").strip().lower() == "signature weapon"
                             for r in avail):
        avail.insert(0, {"label": "Signature Weapon", "value": signature})
    # gadgets are class-locked, and it varies per item rather than per subcategory
    if klass and not any((r.get("label") or "").strip().lower() == "class" for r in avail):
        avail.insert(0, {"label": "Class", "value": klass})
    if avail:
        out.append("<h3>Availability</h3><table>")
        for row in avail:
            is_stack = isinstance(row.get("value"), (list, tuple))
            # The row carries the marker too, so the label can be top-aligned
            # against a multi-line cell without needing :has().
            out.append("<tr%s><td>%s</td><td%s>%s</td></tr>"
                       % (' class="stackrow"' if is_stack else "",
                          html.escape(row.get("label", "")),
                          ' class="stack"' if is_stack else "",
                          value_cell(row.get("value"))))
        out.append("</table>")
    # Empty means empty: the caller drops the whole box and lets the art span the
    # row, rather than parking "No stats recorded yet" beside it. Vehicles have
    # no stat block at all now that faction is carried by the variant captions.
    return "\n".join(out)


def value_cell(value):
    """A value may be a list, for challenges that carry more than one task.
    Each part renders on its own line rather than being joined into one string."""
    if isinstance(value, (list, tuple)):
        parts = [str(v).strip() for v in value if str(v).strip()]
        if not parts:
            return '<span class="tbd">TBD</span>'
        return "".join('<span class="req">%s</span>' % html.escape(p) for p in parts)
    text = (value or "").strip()
    if not text or text.upper() == "TBD":
        return '<span class="tbd">TBD</span>'
    return html.escape(text)


def render_quote(item):
    """The label above the quote carries the attribution, so no trailing cite
    line is needed. ADR 0006 still holds: quoted verbatim, visibly credited."""
    desc = item.get("description") or {}
    label = html.escape(desc.get("attribution") or "In-game description")
    text = (desc.get("text") or "").strip()
    if not text or text.upper() == "TBD":
        body = '<span class="tbd">Not recorded yet.</span>'
    else:
        body = "&ldquo;%s&rdquo;" % html.escape(text)
    return ('<div class="descblock"><h2 class="desclabel">%s</h2>'
            '<blockquote class="ingame">%s</blockquote></div>' % (label, body))


def render_image(item, img):
    """Art for the page: one figure, or one per faction variant.

    A vehicle class is a single page covering both factions, so it carries a
    `variants` list and gets a figure each. The caption names the faction and
    the model, which is why those two no longer need Availability rows.
    """
    variants = item.get("variants") or []
    if variants:
        out = []
        for v in variants:
            base = (v.get("image") or "").strip()
            src = find_image(base) if base else None
            # A vehicle variant carries the faction's model designation, so the
            # caption names both. A class variant has no second name to give, so
            # it captions with the faction alone rather than a bare TBD.
            if (v.get("name") or "").strip():
                label = "%s &middot; %s" % (html.escape(v.get("faction", "")),
                                            html.escape(v["name"]))
            else:
                label = html.escape(v.get("faction", ""))
            if src and (v.get("name") or "").strip():
                body = ('<img src="%s" alt="The %s in Battlefield 6, %s variant" '
                        'loading="lazy">'
                        % (src, html.escape(v["name"]), html.escape(v.get("faction", ""))))
            elif src:
                body = ('<img src="%s" alt="%s, %s variant, in Battlefield 6" '
                        'loading="lazy">'
                        % (src, html.escape(item["name"]),
                           html.escape(v.get("faction", ""))))
            else:
                body = ('<div class="imgpending"><b>%s</b><span>image pending</span></div>'
                        % html.escape(v.get("name") or v.get("faction") or item["name"]))
            out.append('<figure class="itemimg">%s<figcaption>%s</figcaption></figure>'
                       % (body, label))
        return "\n".join(out)

    # A mode's art is the badge the game prints beside GAME MODE, not a scene.
    # Blown up to the width of the art column it would be a wall of grey, so it
    # renders at its own size and the alt text says what it is.
    icon = (item.get("art") or "").strip().lower() == "icon"
    cls = "itemimg icon" if icon else "itemimg"
    if img:
        alt = ("%s mode badge in Battlefield 6" if icon else "%s in Battlefield 6")
        return ('<figure class="%s"><img src="%s" alt="%s" loading="lazy"></figure>'
                % (cls, img, html.escape(alt % item["name"])))
    # Attachments have no art and are not waiting for any: they are tiny parts
    # shown as line drawings in game, and a full-width "image pending" placeholder
    # would be the largest thing on a page whose real content is a table.
    if item["branch"] == "attachments":
        return ""
    return ('<figure class="%s"><div class="imgpending"><b>%s</b>'
            '<span>%s</span></div></figure>'
            % (cls, html.escape(item["name"]),
               "no badge" if icon else "image pending"))


def render_loadout(item):
    """Vehicle customisation slots, grouped by seat.

    Every option tile visible in a capture is listed, even when only its name is
    legible: a slot screen names the whole row but describes only the highlighted
    option, so an omitted tile would silently read as "this option does not
    exist". Unread fields are TBD, same rule as everywhere else.
    """
    slots = item.get("loadout") or []
    if not slots:
        return ""

    out = ['<h2 class="cat vehicles" id="loadout"><span class="dot"></span>Loadout</h2>']
    described = sum(1 for s in slots for o in (s.get("options") or [])
                    if (o.get("description") or "").strip()
                    and o["description"].strip().upper() != "TBD")
    total = sum(len(s.get("options") or []) for s in slots)
    locked = [s for s in slots if s.get("locked")]
    note = ("Every customisation slot and every option in it, transcribed from the in-game "
            "screens. %d of %d options have their in-game description recorded; the rest are "
            "named but not yet described." % (described, total))
    if locked:
        note += (" %d slot%s could not be opened on the capturing account and show only the "
                 "equipped item." % (len(locked), "" if len(locked) == 1 else "s"))
    out.append('<p class="cat-note">%s</p>' % note)

    by_role = []
    for slot in slots:
        role = slot.get("role") or ""
        if not by_role or by_role[-1][0] != role:
            by_role.append((role, []))
        by_role[-1][1].append(slot)

    out.append('<div class="loadout">')
    for role, group in by_role:
        out.append('<section class="lo-role"><h3>%s</h3>' % html.escape(role))
        for slot in group:
            out.append('<div class="lo-slot"><h4>%s</h4>' % html.escape(slot.get("slot", "")))
            options = slot.get("options") or []
            if slot.get("locked") and not options:
                out.append('<p class="lo-locked">Slot locked; equipped item reads '
                           '<b>%s</b>. Its alternatives are not selectable, so no option '
                           'list was captured.</p>' % html.escape(slot.get("equipped") or "TBD"))
                out.append("</div>")
                continue
            out.append("<table>")
            out.append("<tr><th>Option</th><th>Designation</th><th>In-game description</th></tr>")
            for opt in options:
                out.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                           % (html.escape(opt.get("name", "")),
                              value_cell(opt.get("designation")),
                              value_cell(opt.get("description"))))
            out.append("</table></div>")
        out.append("</section>")
    out.append("</div>")
    return "\n".join(out)


def render_paths(item):
    """Class training paths, and the active ability the paths share.

    The ability is recorded once on the class rather than twice in the data,
    because both of a class's path screens show the same LVL 03 entry. It leads
    the section so the page states plainly that picking a path does not change
    it. Levels are the game's own labels (LVL 03 down to LVL 00), kept as
    strings rather than numbers because that is how the screen prints them.
    """
    paths = item.get("training_paths") or []
    ability = item.get("ability") or {}
    if not paths and not ability:
        return ""

    color = BRANCH_COLOR.get(item["branch"], "weapons")
    out = ['<h2 class="cat %s" id="paths"><span class="dot"></span>Training paths</h2>' % color]
    out.append('<p class="cat-note">Every training path for this class and every ability in it, '
               'transcribed from the in-game screens. The class active ability is shared: it is '
               'the same on both paths, so choosing one does not change it.</p>')
    out.append('<div class="loadout">')

    def table(rows):
        cells = ['<table>',
                 '<tr><th>Level</th><th>Ability</th><th>In-game description</th></tr>']
        for r in rows:
            cells.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                         % (value_cell(r.get("level")),
                            html.escape(r.get("name", "")),
                            value_cell(r.get("description"))))
        cells.append("</table>")
        return "\n".join(cells)

    if ability:
        out.append('<section class="tp-path"><h3>Class active ability</h3>')
        out.append('<div class="lo-slot">%s</div></section>' % table([ability]))
    for path in paths:
        out.append('<section class="tp-path"><h3>%s</h3>' % html.escape(path.get("name", "")))
        desc = (path.get("description") or "").strip()
        if desc and desc.upper() != "TBD":
            out.append('<p class="tp-desc">%s</p>' % html.escape(desc))
        out.append('<div class="lo-slot">%s</div></section>'
                   % table(path.get("abilities") or []))
    out.append("</div>")
    return "\n".join(out)


def render_options(item):
    """A flat table of models on a page that covers a whole attachment family.

    Three attachment pages stand for many in-game tiles rather than one each,
    and for different reasons. Optics: EA writes one description per
    magnification band, so 22 of the 30 would otherwise repeat the same
    sentence. Barrels and Magazines: the tile's full name carries the weapon's
    own barrel length or magazine capacity (415mm Factory on the KORD 6P67,
    16" Factory on the EF88), so there is no shared name to title a page with,
    while the type and its description are shared.
    """
    options = item.get("options") or []
    if not options:
        return ""
    color = BRANCH_COLOR.get(item["branch"], "weapons")
    has_desig = any((o.get("designation") or "").strip() for o in options)
    out = ['<h2 class="cat %s" id="options"><span class="dot"></span>%s</h2>'
           % (color, html.escape(item["name"]))]
    out.append('<p class="cat-note">%d in the game, transcribed from the in-game '
               'screens. Point cost is the number on the tile; every weapon has '
               '100 points to spend across all its slots.</p>' % len(options))
    out.append('<div class="loadout"><div class="lo-slot"><table>')
    head = ["Name"] + (["Tile"] if has_desig else []) + ["Points", "In-game description"]
    out.append("<tr>%s</tr>" % "".join("<th>%s</th>" % h for h in head))
    for o in options:
        cells = ["<td>%s</td>" % html.escape(o.get("name", ""))]
        if has_desig:
            cells.append("<td>%s</td>" % value_cell(o.get("designation")))
        cells.append("<td>%s</td>" % value_cell(str(o.get("cost", "")) or None))
        cells.append("<td>%s</td>" % value_cell(o.get("description")))
        out.append("<tr>%s</tr>" % "".join(cells))
    out.append("</table></div></div>")
    return "\n".join(out)


def render_related(item, by_slug, color):
    """Compatible attachments. Weapons only.

    This started as a generic "Related items" block on every page and was empty
    on all 151 of them, which is just a heading promising something the site
    does not have. Attachments are the one real relationship in the data, and
    they only ever hang off a weapon, so the section renders there and nowhere
    else. A vehicle, gadget, map, mode or class simply ends at its patch history.
    """
    if item["branch"] != "weapons":
        return ""

    head = ('<h2 class="cat %s" id="related"><span class="dot"></span>'
            'Compatible attachments</h2>' % color)
    groups = item.get("related") or []
    if not any(g.get("items") for g in groups):
        return (head + '\n<p class="emptynote">Compatibility is not catalogued yet. '
                'Once attachments are added they will be listed here, and each '
                'attachment will link back to this page.</p>')
    out = [head]
    for g in groups:
        entries = g.get("items") or []
        if not entries:
            continue
        out.append('<div class="relgroup"><h4>%s</h4><p>' % html.escape(g.get("group", "")))
        links = []
        for e in entries:
            target = by_slug.get(e.get("slug"))
            if target:
                links.append('<a href="%s">%s</a>' % (target["url"], html.escape(e.get("name", ""))))
            else:
                links.append('<span class="tbd">%s</span>' % html.escape(e.get("name", "")))
        out.append(" &middot; ".join(links))
        out.append("</p></div>")
    return "\n".join(out)


def render_history(entries, name, the="the "):
    if not entries:
        # Same article rule as the meta description: a map, class or mode is a
        # proper noun and takes no "the".
        return ('<p class="emptynote">EA has not named %s%s in a patch note yet. '
                'Entries appear here automatically once a patch line in the log is tagged '
                'for this item.</p>' % (the, html.escape(name)))

    by_version = {}
    for e in entries:
        by_version.setdefault((e["version"], e["date"]), []).append(e)

    out = []
    ordered = sorted(by_version.items(), key=lambda kv: version_key(kv[0][0]), reverse=True)
    for n, ((ver, date), group) in enumerate(ordered):
        section = group[0].get("section") or ""
        label, color = SECTIONS.get(section, ("balance", "progression"))
        # Only the newest patch opens. Items now carry every EA line that names
        # them, so an all-open history runs to hundreds of lines on the busier
        # weapons.
        out.append('<details class="patch"%s>' % (" open" if n == 0 else ""))
        out.append('<summary><span class="ver">%s</span><span class="date">%s</span>'
                   '<span class="tag tag-%s">%s</span></summary>'
                   % (html.escape(ver), html.escape(date), color, html.escape(label)))
        out.append('<div class="body">')

        bullets = [e for e in group if e["tag"] != "tr"]
        rows = [e for e in group if e["tag"] == "tr"]

        if bullets:
            out.append('<ul class="plain">')
            for e in bullets:
                out.append(e["html"])
            out.append("</ul>")

        tables = {}
        for e in rows:
            tbl = e.get("table") or {"caption": "", "headers": []}
            key = (tbl["caption"], tuple(tbl["headers"]))
            tables.setdefault(key, []).append(e)
        for (caption, headers), group_rows in tables.items():
            out.append("<table>")
            if caption:
                out.append("<caption>%s</caption>" % html.escape(caption))
            if headers:
                out.append("<tr>%s</tr>" % "".join("<th>%s</th>" % html.escape(h) for h in headers))
            for e in group_rows:
                out.append(e["html"])
            out.append("</table>")

        out.append('<div class="src">Full patch entry and EA source link: '
                   '<a href="/#%s">%s in the balance log</a></div>'
                   % (section or "", html.escape(ver)))
        out.append("</div></details>")
    return "\n".join(out)


def build_page(item, entries, tree, items_by_place, by_slug, shared_css):
    url = item["url"]
    name = item["name"]
    color = BRANCH_COLOR.get(item["branch"], "weapons")
    branch_label = item["branch_label"]
    sub_label = item.get("subcategory_label")
    crumb = " / ".join('<span>%s</span>' % html.escape(x)
                       for x in (branch_label, sub_label) if x)
    crumb += ' / <span style="color:var(--%s)">%s</span>' % (color, html.escape(name))

    img = find_image(item["slug"])
    facts = render_facts(item, color, item.get("signature"), item.get("_added_in"),
                         item.get("class"), item.get("_removed"))
    canonical = SITE + url
    # Maps are places, and a class or a mode is named the way a proper noun is:
    # "the Tsuru Reef", "the Assault" and "the Rush" all read wrong, while
    # weapons, gadgets and vehicles take the article. This shows up in search
    # results on every page in those branches.
    the = "" if item["branch"] in ("maps", "classes", "modes") else "the "
    desc = ("Every Battlefield 6 patch note mentioning %s%s, quoted from EA's official "
            "Game Updates, with stats and in-game description." % (the, name))
    n = len(entries)
    histnote = ("%d patch note%s mentioning %s%s, newest first. Each entry is the exact "
                "line from EA's Game Update notes." % (n, "" if n == 1 else "s", the, name)) \
               if n else "Nothing logged for this item yet."

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "BF6 Balance Log", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": name, "item": canonical},
        ],
    }, separators=(",", ":"))

    fields = {
        # no em dashes anywhere in page copy, per the site's writing rules
        "TITLE": "%s: Patch History &amp; Stats | BF6 Balance Log" % html.escape(name),
        "OGTITLE": "%s patch history | BF6 Balance Log" % html.escape(name),
        "DESC": html.escape(desc, quote=True),
        "CANONICAL": canonical,
        "OGIMAGE": SITE + (img or "/og-image.png"),
        "JSONLD": jsonld,
        "CSS": shared_css + PAGE_CSS,
        "CRUMB": crumb,
        "COLOR": color,
        "NAME": html.escape(name),
        "SUBTITLE": render_subtitle(item),
        "TRAITS": render_traits(item),
        "QUOTE": render_quote(item),
        "IMAGE": render_image(item, img),
        "GRIDMOD": "" if facts else " solo",
        "FACTBOX": '<div class="factbox">\n%s\n</div>' % facts if facts else "",
        "LOADOUT": render_loadout(item),
        "PATHS": render_paths(item),
        "OPTIONS": render_options(item),
        "HISTNOTE": histnote,
        "HISTORY": render_history(entries, name, the),
        "RELATED": render_related(item, by_slug, color),
        "SECTIONANCHOR": (entries[0]["section"] if entries and entries[0].get("section")
                          else BRANCH_ANCHOR.get(item["branch"], "weapons")),
        "JS": PAGE_JS,
    }
    page = PAGE_TEMPLATE
    for key, val in fields.items():
        page = page.replace("{{%s}}" % key, val)
    return inject_tree(page, render_tree(tree, items_by_place, url))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    check_only = "--check" in sys.argv
    index_path = os.path.join(ROOT, "index.html")
    index_raw = read_text(index_path)

    style = re.search(r"<style>(.*?)</style>", index_raw, re.S)
    if not style:
        print("error: no <style> block found in index.html")
        return 1
    shared_css = style.group(1)

    tree = json.loads(read_text(os.path.join(ROOT, "data", "tree.json")))
    branch_labels = {b["key"]: b["label"] for b in tree["branches"]}
    sub_labels = {(b["key"], c["key"]): c["label"]
                  for b in tree["branches"] for c in b.get("children", [])}
    sub_signature = {(b["key"], c["key"]): c.get("signature")
                     for b in tree["branches"] for c in b.get("children", [])}
    valid_places = set()
    for b in tree["branches"]:
        if b.get("flat"):
            valid_places.add((b["key"], None))
        for c in b.get("children", []):
            valid_places.add((b["key"], c["key"]))

    problems = []

    # ---- content releases: the source for Added in ----
    releases_path = os.path.join(ROOT, "data", "releases.json")
    releases = {"releases": []}
    if os.path.isfile(releases_path):
        releases = json.loads(read_text(releases_path))
    known_path = os.path.join(ROOT, "data", "known_versions.json")
    known_versions = set()
    if os.path.isfile(known_path):
        known_versions = set(json.loads(read_text(known_path)).get("versions") or [])

    added_in = {}
    unbuilt = []
    gaps = []
    for rel in releases.get("releases") or []:
        ver, name = rel.get("version"), rel.get("name")
        if known_versions and ver not in known_versions:
            if rel.get("_version_unconfirmed"):
                # a known gap in the log, flagged in the data on purpose
                gaps.append((ver, name, rel.get("live")))
            else:
                problems.append("releases.json: version %r is not in known_versions.json" % ver)
        label = "%s (%s)" % (ver, name) if name else ver
        for entry in rel.get("added") or []:
            if entry.get("slug"):
                added_in[entry["slug"]] = label
            else:
                unbuilt.append((entry.get("name", "?"), entry.get("kind", "?"), ver))

    # ---- content removals: the source for the Removed row ----
    # No version to check against known_versions.json: EA has published no
    # changelog line for any removal so far, so a block carries an observation
    # date and its source instead. The rendered string is taken literally.
    removed_in = {}
    unbuilt_removed = []
    for block in releases.get("removed") or []:
        value = (block.get("value") or "").strip()
        if not value:
            problems.append("releases.json: a removed block has no 'value' to render")
            continue
        if not (block.get("source") or "").strip():
            problems.append("releases.json: removed block %r has no 'source'" % value)
        for entry in block.get("entries") or []:
            if entry.get("slug"):
                removed_in[entry["slug"]] = value
            else:
                unbuilt_removed.append((entry.get("name", "?"), entry.get("kind", "?"),
                                        block.get("observed", "?")))

    items_dir = os.path.join(ROOT, "data", "items")
    items = []
    if os.path.isdir(items_dir):
        for fname in sorted(os.listdir(items_dir)):
            if not fname.endswith(".json"):
                continue
            item = json.loads(read_text(os.path.join(items_dir, fname)))
            place = (item.get("branch"), item.get("subcategory") or None)
            if place not in valid_places:
                problems.append("%s: branch/subcategory %s is not in data/tree.json" % (fname, place))
                continue
            if item["slug"] != os.path.splitext(fname)[0]:
                problems.append("%s: slug %r does not match the filename" % (fname, item["slug"]))
            item["url"] = item_url(item)
            item["branch_label"] = branch_labels[item["branch"]]
            item["subcategory_label"] = sub_labels.get(place)
            item["signature"] = sub_signature.get(place)
            # releases.json wins, but disagreement is reported rather than hidden
            release_value = added_in.get(item["slug"])
            if release_value:
                own = next((r.get("value") for r in (item.get("availability") or [])
                            if (r.get("label") or "").strip().lower() == "added in"), None)
                if isinstance(own, str) and own.strip() and own.strip().upper() != "TBD" \
                        and own.strip() != release_value:
                    problems.append("%s: Added in %r in the item file disagrees with %r in "
                                    "releases.json" % (fname, own, release_value))
                item["_added_in"] = release_value
            item["_removed"] = removed_in.get(item["slug"])
            items.append(item)

    by_slug = {i["slug"]: i for i in items}
    items_by_place = {}
    for i in items:
        items_by_place.setdefault((i["branch"], i.get("subcategory") or None), []).append(i)

    parser = LogParser(index_raw)
    parser.feed(index_raw)
    parser.close()

    history = {}
    for e in parser.entries:
        history.setdefault(e["slug"], []).append(e)

    written = []
    for item in items:
        page = build_page(item, history.get(item["slug"], []), tree,
                          items_by_place, by_slug, shared_css)
        out_path = os.path.join(ROOT, item["url"].strip("/").replace("/", os.sep), "index.html")
        written.append((out_path, page))
        for old in item.get("retired_paths") or []:
            stub = REDIRECT_TEMPLATE
            for key, val in (("NAME", html.escape(item["name"])),
                             ("TARGET", SITE + item["url"]),
                             ("PATH", item["url"])):
                stub = stub.replace("{{%s}}" % key, val)
            written.append((os.path.join(ROOT, old.strip("/").replace("/", os.sep), "index.html"), stub))

    search_index = {
        "items": [
            {"name": i["name"], "url": i["url"], "cat": (i.get("subcategory_label")
                                                         or i["branch_label"]).upper(),
             "alt": " ".join(i.get("aliases") or [])}
            for i in sorted(items, key=lambda x: x["name"].lower())
        ]
    }
    written.append((os.path.join(ROOT, "data", "search-index.json"),
                    json.dumps(search_index, indent=1) + "\n"))

    # lastmod from the newest patch each page actually carries, not from the
    # build clock: rebuilding for a template tweak should not tell crawlers that
    # 127 item pages changed. The home page tracks the newest update overall.
    def newest_for(entry_list):
        vers = [e["version"] for e in entry_list if e.get("version") and e.get("date")]
        if not vers:
            return None
        newest = max(vers, key=version_key)
        for e in entry_list:
            if e["version"] == newest:
                return iso_date(e["date"])
        return None

    all_entries = [e for group in history.values() for e in group]
    site_lastmod = newest_for(all_entries) if all_entries else None

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    def add(url, lastmod):
        if lastmod:
            sitemap.append("  <url><loc>%s</loc><lastmod>%s</lastmod></url>" % (url, lastmod))
        else:
            sitemap.append("  <url><loc>%s</loc></url>" % url)

    add(SITE + "/", site_lastmod)
    for i in items:
        add(SITE + i["url"], newest_for(history.get(i["slug"], [])))
    sitemap.append("</urlset>")
    written.append((os.path.join(ROOT, "sitemap.xml"), "\n".join(sitemap) + "\n"))

    # "/" so the Patch Notes link marks itself current on the home page
    written.append((index_path, inject_tree(index_raw, render_tree(tree, items_by_place, "/"))))

    changed = []
    for path, content in written:
        existing = read_text(path) if os.path.isfile(path) else None
        if existing != content:
            changed.append(os.path.relpath(path, ROOT).replace(os.sep, "/"))
            if not check_only:
                write_text(path, content)

    # ---- report ----
    print("items:      %d" % len(items))
    print("tagged:     %d line(s) in index.html across %d slug(s)"
          % (len(parser.entries), len(history)))
    for item in items:
        print("  %-28s %-32s %d entr%s"
              % (item["name"], item["url"], len(history.get(item["slug"], [])),
                 "y" if len(history.get(item["slug"], [])) == 1 else "ies"))

    orphans = sorted(s for s in history if s not in by_slug)
    if orphans:
        print("\nbacklog: tagged in the log but no data/items/<slug>.json yet:")
        for s in orphans:
            print("  %-22s %d line(s)" % (s, len(history[s])))

    if gaps:
        print("\nRELEASE MISSING FROM THE LOG (no patch entry in index.html):")
        for ver, name, live in gaps:
            print("  %-9s %-22s %s   <- version number unconfirmed" % (ver, name, live))

    if unbuilt:
        print("\nreleased but no page yet (from data/releases.json):")
        for name, kind, ver in unbuilt:
            print("  %-22s %-12s %s" % (name, kind, ver))

    if unbuilt_removed:
        print("\nrecorded as removed but no page yet (from data/releases.json):")
        for name, kind, observed in unbuilt_removed:
            print("  %-22s %-12s observed %s" % (name, kind, observed))

    # A removal that points at a slug with no item file would render nowhere, so
    # the removal would silently not be stated anywhere on the site.
    for slug in sorted(set(removed_in) - set(by_slug)):
        problems.append("releases.json: %r is recorded as removed but has no "
                        "data/items/%s.json, so nothing renders the Removed row"
                        % (slug, slug))

    empty = [i["name"] for i in items if not history.get(i["slug"])]
    if empty:
        print("\nno history yet (nothing in the log is tagged for these): %s" % ", ".join(empty))

    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  " + p)

    if check_only:
        print("\n--check: %d file(s) would change" % len(changed))
        for c in changed:
            print("  " + c)
        return 1 if changed else 0

    print("\nwrote %d file(s)%s" % (len(changed), ":" if changed else " (already up to date)"))
    for c in changed:
        print("  " + c)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
