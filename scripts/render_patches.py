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
FULL_JSON = REPO_ROOT / "data" / "patch-full.json"

# Every category on the page is generated. There is no "systemic" category:
# that was an editorial grouping with no EA equivalent, and its lines now sit in
# whichever category EA filed them under (decision 2026-08-03).
RENDERED = ["player", "weapons", "vehicles", "gadgets", "maps", "redsec",
            "progression", "ui", "audio", "portal", "ai", "misc"]

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

# The generic "Name: change" shape is the loose one - it would happily turn four
# consecutive prose lines that each contain an early colon ("Fixed an issue
# where X: Y happened") into a table of sentence fragments. An item name is a
# short designation, not a clause, so reject a left-hand side that reads like
# prose.
PROSE_WORDS = re.compile(
    r"\b(a|an|the|and|or|of|to|for|in|on|with|when|where|while|that|this|"
    r"issue|issues|fixed|resolved|corrected|updated|added|removed|improved|"
    r"could|would|should|players?|now)\b", re.I)


def looks_like_item(name):
    if len(name.split()) > 5:
        return False
    if PROSE_WORDS.search(name):
        return False
    return not name.rstrip().endswith((".", ",", ";"))


def esc(s):
    return H.escape(s, quote=False)


def read_index():
    return INDEX.read_text(encoding="utf-8")


INDEX_DATA = REPO_ROOT / "data" / "patch-index.json"


def patch_index():
    return json.loads(INDEX_DATA.read_text(encoding="utf-8"))["patches"]


def patch_meta():
    """version -> (posted, url). Single source for every block's date and link."""
    return {p["version"]: (p["posted"], p["url"]) for p in patch_index()}


EA_HOST = "https://www.ea.com/"


def render_locales(url):
    """Placeholder for the row of flag links to EA's own translations.

    Only the article path is emitted; the twelve <a> elements are built in the
    browser by buildLocaleLinks() in index.html, which also holds the locale
    table and the reasoning behind it.

    Spelling all twelve links out here costs ~3 KB per block and a version
    appears in one block per category, so the full markup added 442 KB to a
    618 KB page - more than undoing the work that moved the full notes out to
    data/patch-full.json. The row is decoration around an outbound link, so
    there is nothing to lose by building it client side.

    Anything that is not an ea.com URL gets no row rather than a guessed link.
    """
    return '<div class="i18n"%s></div>' % locale_attr(url)


# EA is inconsistent about this: three of the fifteen source URLs carry an
# explicit /en/ and the rest carry none. Both serve the same English article,
# but pasting a locale in front of the /en/ one gives /de/en/... which is a
# genuine 404 - it shipped 36 dead links before this was caught. Strip any
# leading locale segment before building the localised URL.
KNOWN_PREFIXES = {
    "en", "ar", "de", "es", "es-mx", "fr", "it", "ja", "ko", "pl", "pt-br",
    "zh-hans", "zh-hant", "cs", "da", "fi", "id", "nb", "nl", "ro", "ru", "sv",
    "th", "tr", "en-gb", "en-au", "pt", "zh",
}


def article_path(url):
    """The article path with any locale prefix removed, or None if not an EA URL."""
    if not url.startswith(EA_HOST):
        return None
    tail = url[len(EA_HOST):]
    head, sep, rest = tail.partition("/")
    if sep and head.lower() in KNOWN_PREFIXES:
        return rest
    return tail


def locale_attr(url):
    """` data-i18n="<path>"` for a patch URL, or "" when there is nothing to link."""
    path = article_path(url)
    if not path:
        return ""
    return ' data-i18n="%s"' % H.escape(path, quote=True)


def version_key(v):
    return [int(x) for x in v.split(".")]


def load_by_version():
    """version -> [entry] in EA's original document order, all categories."""
    out = {}
    for path in sorted(PATCHES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        out[payload["version"]] = list(payload["entries"])
    return out


def load_entries():
    """section -> version -> [entry].

    REDSEC lines go to the REDSEC section rather than their gameplay category,
    so Battle Royale tuning stays separate from multiplayer (decision
    2026-08-03). The gameplay heading survives as the group label inside it.
    """
    by_cat = {}
    for path in sorted(PATCHES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        version = payload["version"]
        for entry in payload["entries"]:
            cat = "redsec" if entry.get("redsec") else entry["section"]
            if entry["section"] == "summary":
                cat = "summary"
            by_cat.setdefault(cat, {}).setdefault(version, []).append(entry)
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
            cells = [m.group(g).strip() for g in groups]
            if not looks_like_item(cells[0]):
                break
            rows.append((entry, cells))
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


def render_rows(entries, emitted=None):
    """A heading group -> markup. Tables where EA's shape allows, else a list.

    Every entry consumed is recorded in `emitted` so main() can prove that no
    line was silently dropped on the way to the page.
    """
    out = []
    i = 0
    while i < len(entries):
        best = table_at(entries, i)
        if best:
            end, headers, rows = best
            out.append("<table>")
            out.append("<tr>" + "".join("<th>%s</th>" % esc(h) for h in headers) + "</tr>")
            for entry, cells in rows:
                if emitted is not None:
                    emitted.append(entry)
                attr = ' data-item="%s"' % " ".join(entry["items"]) if entry["items"] else ""
                tds = ['<td class="item">%s</td>' % esc(cells[0])]
                for cell in cells[1:]:
                    tds.append('<td class="num%s">%s</td>' % (delta_class(cell), esc(cell)))
                out.append("<tr%s>%s</tr>" % (attr, "".join(tds)))
            out.append("</table>")
            i = end
            continue

        entry = entries[i]
        if emitted is not None:
            emitted.append(entry)
        attr = ' data-item="%s"' % " ".join(entry["items"]) if entry["items"] else ""
        # No REDSEC badge: those lines live in the REDSEC section, which labels
        # them already.
        out.append("<li%s>%s</li>" % (attr, esc(entry["text"])))
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


def render_category(cat, by_version, meta, summaries, emitted=None, newest=None):
    out = []
    versions = sorted(by_version, key=version_key, reverse=True)
    for n, version in enumerate(versions):
        entries = by_version[version]
        if version not in meta:
            # Silently rendering ("", "") would ship a patch block with a blank
            # date and href="" - and dates are the whole point of this site.
            raise SystemExit(
                "render_patches: %s has entries but no row in data/patch-index.json; "
                "add it there first (version, posted, live, headline, url)" % version)
        posted, url = meta[version]
        groups = {}
        order = []
        for e in entries:
            label = heading_label(e)
            if label not in groups:
                groups[label] = []
                order.append(label)
            groups[label].append(e)
        tag = "%d line%s" % (len(entries), "" if len(entries) == 1 else "s")
        # Only the newest update on the site opens. With every EA line present,
        # one open block per category would be thousands of lines on first paint.
        out.append('<details class="patch"%s>' % (" open" if version == newest else ""))
        out.append('<summary><span class="ver">%s</span><span class="date">%s</span>'
                   '<span class="tag tag-%s">%s</span></summary>'
                   % (esc(version), esc(posted), cat, tag))
        out.append('<div class="body">')
        out.append(render_locales(url))
        note = summaries.get(version)
        if note:
            out.append('<p class="dev">Dev intent, quoted from EA\'s '
                       '&ldquo;Major Updates for %s&rdquo;: %s</p>' % (version, esc(note)))
        for label in order:
            if label:
                out.append('<p class="grp"><b>%s</b></p>' % esc(label))
            out.extend(render_rows(groups[label], emitted))
        out.append('<div class="src">Source: <a href="%s" target="_blank" rel="noopener">'
                   'Battlefield 6 Game Update %s</a>, posted %s</div>'
                   % (H.escape(url, quote=True), esc(version), esc(posted)))
        out.append("</div>")
        out.append("</details>")
    return "\n".join(out)


def full_patch_payload(by_version_all):
    """version -> the complete update, grouped by EA's heading, for the browser.

    This lives in data/patch-full.json rather than in index.html because the
    expandable view repeats every line that already appears in its category
    section. Inlining both copies took the page to 928 KB; fetching this on
    first expand keeps index.html at roughly 600 KB and costs one request that
    most visitors never make.
    """
    payload = {}
    for patch in patch_index():
        version = patch["version"]
        groups = []
        for entry in by_version_all.get(version, []):
            label = heading_label(entry) or "General"
            cat = "redsec" if entry.get("redsec") else entry["section"]
            if entry.get("redsec"):
                inner = heading_label(entry)
                label = "REDSEC" + (" · " + inner if inner else "")
            if not groups or groups[-1]["label"] != label:
                groups.append({"label": label, "cat": cat, "lines": []})
            groups[-1]["lines"].append(entry["text"])
        payload[version] = {"url": patch["url"], "groups": groups}
    return payload


def render_header(by_version_all):
    """The header's counts and date window.

    Generated because it rotted: the page shipped "1.0.1.0 - 1.4.1.0 (14
    updates)" and "Compiled Jul 29, 2026" for a while after 1.4.1.5 landed. Any
    number that has to be retyped when a patch ships will eventually be wrong.
    """
    patches = patch_index()
    if not patches:
        return ""
    ordered = sorted(patches, key=lambda p: version_key(p["version"]))
    oldest, newest = ordered[0], ordered[-1]
    lines = sum(len(v) for v in by_version_all.values())
    return (
        '<div class="meta-row">\n'
        '<span><b>Patches covered</b> %s &ndash; %s (%d update%s)</span>\n'
        '<span><b>Window</b> %s &ndash; %s</span>\n'
        '<span><b>Lines logged</b> %s, every one quoted from EA</span>\n'
        '</div>'
        % (esc(oldest["version"]), esc(newest["version"]), len(patches),
           "" if len(patches) == 1 else "s",
           esc(oldest["posted"]), esc(newest["posted"]), format(lines, ",")))


def render_index(by_version_all):
    """The Patch Index table body: a row per update, each followed by an empty
    hidden row the browser fills from data/patch-full.json on first expand.

    Hidden by default - the table reads exactly as before until a row is
    clicked. Headers inside the panel are colored by the category the line
    belongs to, so the full read still shows at a glance what kind of change
    each block is.
    """
    out = []
    for patch in patch_index():
        version = patch["version"]
        count = len(by_version_all.get(version, []))
        out.append(
            '<tr class="ixrow" data-ver="%s" data-count="%d" tabindex="0" role="button" '
            'aria-expanded="false" title="Click to read the full %s notes">'
            '<td><span class="ixcaret">&rsaquo;</span>%s</td><td>%s</td><td>%s</td>'
            '<td>%s</td><td><a href="%s" target="_blank" rel="noopener">'
            'ea.com &#8599;</a></td></tr>'
            % (esc(version), count, esc(version), esc(version), esc(patch["posted"]),
               esc(patch["live"]), esc(patch["headline"]),
               H.escape(patch["url"], quote=True)))
        # Empty on purpose - filled client-side. No data-item anywhere in here
        # either way: build_pages.py harvests every tagged li/tr out of
        # index.html, and these lines already appear in their category section.
        # The locale row is static markup rather than part of the fetched
        # payload, so it is there the moment the row opens and survives the
        # panel being refilled.
        out.append('<tr class="ixfull" data-ver="%s" hidden><td colspan="5">'
                   '<div class="i18n"%s></div>'
                   '<div class="fullpatch"></div></td></tr>'
                   % (esc(version), locale_attr(patch["url"])))
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
    if j < i:
        # Slicing on a reversed pair silently duplicates the page instead of
        # replacing a region.
        raise SystemExit("markers for %r are out of order in index.html" % cat)
    if index_html.count(start) > 1 or index_html.count(end) > 1:
        raise SystemExit("markers for %r appear more than once in index.html" % cat)
    return index_html[:i + len(start)] + "\n" + body + "\n" + index_html[j:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    index_html = read_index()
    meta = patch_meta()
    by_cat = load_entries()
    summaries = collect_summaries(by_cat)

    all_versions = {v for cat in RENDERED for v in by_cat.get(cat, {})}
    newest = max(all_versions, key=version_key) if all_versions else None

    updated = index_html
    emitted = []
    for cat in RENDERED:
        body = render_category(cat, by_cat.get(cat, {}), meta, summaries, emitted, newest)
        updated = inject(updated, cat, body)

    by_version_all = load_by_version()
    updated = inject(updated, "header", render_header(by_version_all))
    updated = inject(updated, "index", render_index(by_version_all))
    full_json = json.dumps(full_patch_payload(by_version_all),
                           ensure_ascii=False, separators=(",", ":")) + "\n"

    # The browser view has to carry every line too, or "read the whole patch"
    # quietly shows a subset.
    in_payload = sum(len(g["lines"])
                     for v in full_patch_payload(by_version_all).values()
                     for g in v["groups"])
    in_data = sum(len(v) for v in by_version_all.values())
    if in_payload != in_data:
        print("render_patches: full-patch payload holds %d of %d lines"
              % (in_payload, in_data))
        sys.exit(1)

    # Completeness: every entry in every rendered category must reach the page,
    # as a list item or as a table row. "summary" is excluded because those
    # lines render as the per-patch dev-intent note instead.
    expected = sum(len(v) for cat in RENDERED
                   for v in by_cat.get(cat, {}).values())
    if len(emitted) != expected:
        print("render_patches: %d entries expected, %d reached the page"
              % (expected, len(emitted)))
        sys.exit(1)
    unrendered = sorted(set(by_cat) - set(RENDERED) - {"summary"})
    if unrendered:
        print("render_patches: categories with no section on the page: %s"
              % ", ".join(unrendered))
        sys.exit(1)
    print("render_patches: %d entries rendered across %d categories"
          % (len(emitted), len(RENDERED)))

    stale_json = (not FULL_JSON.exists()
                  or FULL_JSON.read_text(encoding="utf-8") != full_json)

    if args.check:
        problems = []
        if updated != index_html:
            problems.append("index.html")
        if stale_json:
            problems.append(FULL_JSON.name)
        if problems:
            print("render_patches: stale, re-run without --check: "
                  + ", ".join(problems))
            sys.exit(1)
        print("render_patches: up to date")
        return

    wrote = []
    if updated != index_html:
        INDEX.write_text(updated, encoding="utf-8")
        wrote.append("index.html")
    if stale_json:
        FULL_JSON.write_text(full_json, encoding="utf-8")
        wrote.append(FULL_JSON.name)
    print("render_patches: " + (", ".join(wrote) + " updated" if wrote else "no change"))


if __name__ == "__main__":
    main()
