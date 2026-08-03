#!/usr/bin/env python3
"""Render data/patches/*.json into the marked regions of index.html.

Each category section on the page owns a region:

    <!-- PATCHES:ui:START -->   ... generated ...   <!-- PATCHES:ui:END -->

Everything outside those markers stays hand-authored. Inside them, every line
is EA's exact sentence: this script never rewrites text, it only groups,
tables and tags.

Tables: where EA publishes a run of same-shaped bullets ("CZ3A1: Decreased from
360 m/s to 336 m/s (-6.67%)") the run renders as a table. Every cell is a slice
of EA's own bullet taken straight from the regex match - nothing is re-derived,
recomputed or reformatted, so the verbatim guarantee still holds.

stdlib only.

    python scripts/render_patches.py            # write
    python scripts/render_patches.py --check    # exit 1 if a region is stale
"""
import argparse
import html as H
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATCHES = REPO_ROOT / "data" / "patches"
INDEX = REPO_ROOT / "index.html"
KNOWN = REPO_ROOT / "data" / "known_versions.json"

# Categories this script owns. The curated sections (systemic, player, weapons,
# vehicles, gadgets, maps, redsec, progression) are still hand-authored and are
# migrated separately; only sections with a marker pair are touched.
RENDERED = ["ui", "audio", "portal", "ai"]

MISC_LABEL = {
    "misc": "Settings, Network, Single Player, Stability and VFX",
}

# --- table shapes -----------------------------------------------------------
# Ordered most specific first. Each yields (headers, cells) built purely from
# captured substrings of EA's line.
TABLE_SHAPES = [
    (re.compile(
        r"^(?P<item>[^:]{1,44}):\s*(?:Decreased|Increased|Reduced|Lowered|Raised)"
        r"\s+from\s+(?P<a>.+?)\s+to\s+(?P<b>.+?)\s*\((?P<pct>[-+−][\d.,]+\s*%)\)\.?$",
        re.I),
     ["", "From", "To", "Change"], ["item", "a", "b", "pct"]),
    (re.compile(
        r"^(?P<item>[^:]{1,44}):\s*(?:Decreased|Increased|Reduced|Lowered|Raised)"
        r"\s+from\s+(?P<a>.+?)\s+to\s+(?P<b>.+?)\.?$", re.I),
     ["", "From", "To"], ["item", "a", "b"]),
    (re.compile(r"^(?P<item>[^:]{1,44}):\s*(?P<rest>.{4,200})$"),
     ["", "Change"], ["item", "rest"]),
]
MIN_TABLE_RUN = 4


def esc(s):
    return H.escape(s, quote=False)


def read_index():
    return INDEX.read_text(encoding="utf-8")


def patch_meta(index_html):
    """version -> (posted, url), read from the hand-authored Patch Index."""
    meta = {}
    for m in re.finditer(
            r"<tr><td>(\d[\d.]*)</td><td>([^<]*)</td><td>[^<]*</td><td>[^<]*</td>"
            r"<td><a href=\"([^\"]+)\"", index_html):
        meta[m.group(1)] = (m.group(2).strip(), m.group(3))
    return meta


def version_key(v):
    return [int(x) for x in v.split(".")]


def load_entries():
    by_cat = {}
    for path in sorted(PATCHES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        version = payload["version"]
        for entry in payload["entries"]:
            by_cat.setdefault(entry["section"], {}).setdefault(version, []).append(entry)
    return by_cat


def heading_label(entry):
    trail = [h.rstrip(":") for h in entry["heading"]
             if h.upper().rstrip(":") != "CHANGELOG"]
    trail = [h for h in trail if not h.upper().startswith("REDSEC")]
    return " · ".join(trail) if trail else ""


def table_at(entries, i):
    """Longest table starting at `entries[i]`, preferring the most specific shape.

    Specificity beats length: a heading group holding 39 "from X to Y (Z%)"
    lines followed by 12 prose lines must render the 39 as a four-column table,
    not collapse all 51 into the generic two-column shape.
    """
    for pattern, headers, groups in TABLE_SHAPES:
        rows = []
        for entry in entries[i:]:
            m = pattern.match(entry["text"])
            if not m:
                break
            rows.append((entry, [m.group(g).strip() for g in groups]))
        if len(rows) >= MIN_TABLE_RUN:
            return i + len(rows), headers, rows
    return None


def delta_class(cell):
    t = cell.replace("−", "-")
    if re.match(r"^\+", t):
        return " delta-up"
    if re.match(r"^-", t):
        return " delta-down"
    return ""


def render_rows(entries):
    """A heading group -> markup. Tables where EA's shape allows, else a list."""
    out = []
    i = 0
    while i < len(entries):
        best = table_at(entries, i)
        if best:
            end, headers, rows = best
            out.append("<table>")
            out.append("<tr>" + "".join("<th>%s</th>" % esc(h) for h in headers) + "</tr>")
            for entry, cells in rows:
                attr = ' data-item="%s"' % " ".join(entry["items"]) if entry["items"] else ""
                tds = ['<td class="item">%s</td>' % esc(cells[0])]
                for cell in cells[1:]:
                    tds.append('<td class="num%s">%s</td>' % (delta_class(cell), esc(cell)))
                out.append("<tr%s>%s</tr>" % (attr, "".join(tds)))
            out.append("</table>")
            i = end
            continue

        entry = entries[i]
        attr = ' data-item="%s"' % " ".join(entry["items"]) if entry["items"] else ""
        badge = '<b class="rs">REDSEC</b> ' if entry.get("redsec") else ""
        out.append("<li%s>%s%s</li>" % (attr, badge, esc(entry["text"])))
        i += 1

    # wrap consecutive <li> runs in a <ul>
    wrapped = []
    in_list = False
    for chunk in out:
        if chunk.startswith("<li"):
            if not in_list:
                wrapped.append('<ul class="plain">')
                in_list = True
        elif in_list:
            wrapped.append("</ul>")
            in_list = False
        wrapped.append(chunk)
    if in_list:
        wrapped.append("</ul>")
    return wrapped


def render_category(cat, by_version, meta, summaries):
    out = []
    versions = sorted(by_version, key=version_key, reverse=True)
    for n, version in enumerate(versions):
        entries = by_version[version]
        posted, url = meta.get(version, ("", ""))
        groups = {}
        order = []
        for e in entries:
            label = heading_label(e)
            if label not in groups:
                groups[label] = []
                order.append(label)
            groups[label].append(e)
        tag = "%d line%s" % (len(entries), "" if len(entries) == 1 else "s")
        out.append('<details class="patch"%s>' % (" open" if n == 0 else ""))
        out.append('<summary><span class="ver">%s</span><span class="date">%s</span>'
                   '<span class="tag tag-%s">%s</span></summary>'
                   % (version, posted, cat, tag))
        out.append('<div class="body">')
        note = summaries.get(version)
        if note:
            out.append('<p class="dev">Dev intent, quoted from EA\'s '
                       '&ldquo;Major Updates for %s&rdquo;: %s</p>' % (version, esc(note)))
        for label in order:
            if label:
                out.append('<p class="grp"><b>%s</b></p>' % esc(label))
            out.extend(render_rows(groups[label]))
        out.append('<div class="src">Source: <a href="%s" target="_blank" rel="noopener">'
                   'Battlefield 6 Game Update %s</a>, posted %s</div>'
                   % (url, version, posted))
        out.append("</div>")
        out.append("</details>")
    return "\n".join(out)


def collect_summaries(by_cat):
    """EA's own 'Major Updates for X' lines, kept verbatim, keyed by version."""
    out = {}
    for version, entries in by_cat.get("summary", {}).items():
        texts = [e["text"] for e in entries]
        if texts:
            out[version] = " ".join(texts)
    return out


def inject(index_html, cat, body):
    start = "<!-- PATCHES:%s:START -->" % cat
    end = "<!-- PATCHES:%s:END -->" % cat
    i = index_html.find(start)
    j = index_html.find(end)
    if i < 0 or j < 0:
        raise SystemExit("markers for %r not found in index.html" % cat)
    return index_html[:i + len(start)] + "\n" + body + "\n" + index_html[j:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    index_html = read_index()
    meta = patch_meta(index_html)
    by_cat = load_entries()
    summaries = collect_summaries(by_cat)

    updated = index_html
    for cat in RENDERED:
        body = render_category(cat, by_cat.get(cat, {}), meta, summaries)
        updated = inject(updated, cat, body)

    if args.check:
        if updated != index_html:
            print("render_patches: index.html is stale, re-run without --check")
            sys.exit(1)
        print("render_patches: up to date")
        return
    if updated != index_html:
        INDEX.write_text(updated, encoding="utf-8")
        print("render_patches: index.html updated")
    else:
        print("render_patches: no change")


if __name__ == "__main__":
    main()
