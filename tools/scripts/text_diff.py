"""Render rewritten text as a word diff, the way git shows one, in one HTML page.

    python tools/scripts/text_diff.py                      # the rule-rewritten replies
    python tools/scripts/text_diff.py --what books         # book text, changed paragraphs only
    python tools/scripts/text_diff.py --what hand          # hand-written records
    python tools/scripts/text_diff.py --ids BookSkill_Alteration3 --what books

Faig reads changed text as a diff: what was removed struck through in red, what
came in in green, both inside the one line. Two columns of before and after are
hard for him to read, and he said so on 2026-09-19. This page is that diff.

Input is `tools/build/<name>-text.json`, which `transform.py` writes on every
run - so run the build first, with the profile the game uses:

    python tools/scripts/transform.py --profile momw --plugins "<play>/openmw.cfg" --out-name scifi-rewrite-momw

Under momw the "before" side is what the player would read without our plugin -
Patch for Purists' fixes included - not the bare master.

Speaker names are read from the masters, never recalled. Where the topic's own
word survives in a rewritten reply, it is underlined: the rules keep one literal
instance on purpose, or the topic's hyperlink stops firing (CLAUDE.md, Rules).
"""

import argparse
import collections
import csv
import difflib
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wo1_survey import stream_records  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MASTERS = ("Morrowind.json", "Tribunal.json", "Bloodmoon.json")

# A word, a run of whitespace, or one punctuation mark. Apostrophes stay inside
# words so "Daedra's" is one token and changes as one.
TOKEN_RE = re.compile(r"\s+|[A-Za-z0-9']+|[^\sA-Za-z0-9']")
BR_RE = re.compile(r"<br\s*/?>", re.I)
TAG_RE = re.compile(r"<[^>]*>")


def display_names(cache_dir, wanted):
    """Display names for speaker and book ids, read from the masters, last one
    wins."""
    names = {}
    wanted = {w.lower() for w in wanted if w}
    if not wanted:
        return names
    for m in MASTERS:
        for rec in stream_records(os.path.join(cache_dir, m)):
            if rec.get("type") in ("Npc", "Creature", "Book"):
                rid = str(rec.get("id", "")).lower()
                if rid in wanted and rec.get("name"):
                    names[rid] = rec["name"]
    return names


def readable(text, is_book):
    """Book text is pseudo-HTML; show it as the page shows it."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if is_book:
        text = BR_RE.sub("\n", text)
        text = TAG_RE.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")


def segments(before, after):
    """(kind, text) runs: kind is 'eq', 'del' or 'ins'."""
    a = TOKEN_RE.findall(before)
    b = TOKEN_RE.findall(after)
    out = []
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append(("eq", "".join(a[i1:i2])))
            continue
        if i2 > i1:
            out.append(("del", "".join(a[i1:i2])))
        if j2 > j1:
            out.append(("ins", "".join(b[j1:j2])))
    return out


def mark_keyword(text, keyword):
    """Escape text, underlining whole-word occurrences of the topic keyword."""
    if not keyword:
        return html.escape(text)
    pat = re.compile(r"(?<![A-Za-z])" + re.escape(keyword) + r"(?![A-Za-z])",
                     re.I)
    parts, last = [], 0
    for m in pat.finditer(text):
        parts.append(html.escape(text[last:m.start()]))
        parts.append('<u class="kw" title="слово темы: оставлено, чтобы '
                     'работала ссылка на тему">'
                     + html.escape(m.group(0)) + "</u>")
        last = m.end()
    parts.append(html.escape(text[last:]))
    return "".join(parts)


def render(segs, keyword):
    out = []
    for kind, text in segs:
        if kind == "eq":
            out.append(mark_keyword(text, keyword))
        else:
            out.append(f"<{kind}>{html.escape(text)}</{kind}>")
    return "".join(out)


def changed_lines(segs):
    """Split runs into lines and keep only the lines that changed, for long
    texts. Returns a list of lists of runs, None between non-adjacent lines."""
    lines, cur, dirty = [], [], False
    for kind, text in segs:
        pieces = text.split("\n")
        for n, piece in enumerate(pieces):
            if n > 0:
                lines.append((cur, dirty))
                cur, dirty = [], False
            if piece:
                cur.append((kind, piece))
                if kind != "eq":
                    dirty = True
    lines.append((cur, dirty))
    kept, prev = [], -2
    for i, (runs, d) in enumerate(lines):
        if d:
            if kept and i != prev + 1:
                kept.append(None)
            kept.append(runs)
            prev = i
    return kept


def plural(n, one, few, many):
    """Russian noun form for a count: 1 запись, 2 записи, 5 записей."""
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def rule_patterns(path):
    with open(path, encoding="utf-8", newline="") as f:
        return [r["pattern"].lower() for r in csv.DictReader(f)]


CSS = """
:root { --bg:#fbfaf7; --fg:#1d1c1a; --mute:#6b6760; --line:#e4e0d8;
  --del-bg:#fbe3e1; --del-fg:#9b1c14; --ins-bg:#dcf2e0; --ins-fg:#15632b;
  --kw:#8a5a00; --card:#ffffff; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg:#171614; --fg:#ece9e3; --mute:#a29d93; --line:#34312c;
  --del-bg:#4a1f1c; --del-fg:#ffb4ab; --ins-bg:#16391f; --ins-fg:#9be3ab;
  --kw:#f0c068; --card:#201f1c; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width:780px; margin:0 auto; padding:20px 16px 80px; }
h1 { font-size:1.35rem; margin:0 0 6px; }
h2 { font-size:1.05rem; margin:34px 0 10px; padding-top:10px;
  border-top:1px solid var(--line); }
h2 small, .meta { color:var(--mute); font-weight:normal; font-size:.85rem; }
.legend, .summary { color:var(--mute); font-size:.92rem; margin:6px 0; }
.legend del, .legend ins, .legend u { font-size:.92rem; }
nav { columns:2 220px; font-size:.9rem; margin:14px 0 0; }
nav a { color:inherit; } nav div { break-inside:avoid; }
.e { background:var(--card); border:1px solid var(--line); border-radius:8px;
  padding:10px 12px; margin:10px 0; }
.who { font-weight:600; } .n { color:var(--mute); font-weight:normal; }
.t { white-space:pre-wrap; overflow-wrap:anywhere; margin-top:4px; }
.gap { color:var(--mute); text-align:center; margin:4px 0; }
del { background:var(--del-bg); color:var(--del-fg); text-decoration:line-through; }
ins { background:var(--ins-bg); color:var(--ins-fg); text-decoration:none; }
u.kw { text-decoration:underline dotted; text-decoration-color:var(--kw);
  text-underline-offset:3px; }
.note { color:var(--kw); font-size:.85rem; margin-top:4px; }
"""

TITLES = {
    "replies": "Реплики, переписанные правилами",
    "hand": "Записи, написанные вручную",
    "books": "Книги, изменённые правилами",
    "all": "Все изменения",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--text", default=os.path.join(
        ROOT, "tools", "build", "scifi-rewrite-momw-text.json"))
    ap.add_argument("--rules", default=os.path.join(
        ROOT, "tools", "rules", "naming.csv"))
    ap.add_argument("--cache-dir", default=os.path.join(ROOT, "tools", "cache"))
    ap.add_argument("--what", choices=sorted(TITLES), default="replies")
    ap.add_argument("--ids", nargs="*", default=None,
                    help="only these record ids")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if not os.path.exists(args.text):
        raise SystemExit(f"missing {args.text} - run transform.py first")
    entries = json.load(open(args.text, encoding="utf-8"))

    def wanted(e):
        hand = e["rules"] == "HAND-WRITTEN"
        if args.ids is not None and e["record_id"] not in args.ids:
            return False
        if args.what == "replies":
            return e["record_type"] == "INFO" and not hand
        if args.what == "hand":
            return hand
        if args.what == "books":
            return e["record_type"] == "BOOK" and e["field"] == "text" and not hand
        return True
    entries = [e for e in entries if wanted(e)]
    if not entries:
        raise SystemExit("nothing selected")

    patterns = rule_patterns(args.rules)
    names = display_names(args.cache_dir,
                          {e["speaker"] or e["record_id"] for e in entries})

    groups = collections.defaultdict(list)
    for e in entries:
        head = e["topic"] if e["record_type"] == "INFO" else e["record_type"]
        groups[head or e["record_type"]].append(e)
    for g in groups.values():
        g.sort(key=lambda e: (names.get(e["speaker"].lower(),
                                        e["speaker"]).lower(), e["record_id"]))
    order = sorted(groups, key=str.lower)

    body, nav, n, kept_kw = [], [], 0, 0
    for gi, head in enumerate(order):
        items = groups[head]
        anchor = f"g{gi}"
        nav.append(f'<div><a href="#{anchor}">{html.escape(head)}</a> '
                   f'<span class="meta">{len(items)}</span></div>')
        body.append(f'<h2 id="{anchor}">{html.escape(head)} '
                    f'<small>{len(items)}</small></h2>')
        for e in items:
            n += 1
            is_book = e["record_type"] == "BOOK"
            segs = segments(readable(e["before"], is_book),
                            readable(e["after"], is_book))
            kw = e["topic"] if e["record_type"] == "INFO" else ""
            # Underline the topic word only where a rule would otherwise have
            # changed it - "Daedra" was kept on purpose, "Balmora" was not.
            if kw and not any(p in kw.lower() for p in patterns):
                kw = ""
            if len(e["before"]) > 700 or is_book:
                parts = []
                for runs in changed_lines(segs):
                    if runs is None:
                        parts.append('<div class="gap">…</div>')
                    else:
                        parts.append(f'<div class="t">{render(runs, kw)}</div>')
                text_html = "".join(parts)
            else:
                text_html = f'<div class="t">{render(segs, kw)}</div>'
            who_id = e["speaker"] or e["record_id"]
            who = names.get(who_id.lower(), who_id)
            note = ""
            if kw and re.search(r"(?<![A-Za-z])" + re.escape(kw)
                                + r"(?![A-Za-z])", e["after"], re.I):
                kept_kw += 1
                note = (f'<div class="note">«{html.escape(kw)}» оставлено '
                        f'нарочно: без него перестанет работать ссылка на '
                        f'тему.</div>')
            body.append(
                f'<div class="e" id="n{n}"><div><span class="n">№ {n}</span> '
                f'<span class="who">{html.escape(who)}</span> '
                f'<span class="meta">{html.escape(e["record_id"])} · '
                f'{html.escape(e["rules"])}</span></div>'
                f'{text_html}{note}</div>')

    speakers = len({e["speaker"].lower() for e in entries if e["speaker"]})
    title = TITLES[args.what]
    summary = (f"{n} {plural(n, 'запись', 'записи', 'записей')} в "
               f"{len(order)} {plural(len(order), 'группе', 'группах', 'группах')}")
    if speakers:
        summary += f", говорящих: {speakers}"
    if kept_kw:
        summary += (f". В {kept_kw} из них слово темы оставлено нарочно "
                    f"(подчёркнуто)")
    page = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head>
<body><main>
<h1>{html.escape(title)}</h1>
<p class="summary">{html.escape(summary)}.</p>
<p class="legend"><del>зачёркнуто</del> — было, <ins>зелёным</ins> — стало,
<u class="kw">подчёркнуто</u> — слово темы, оставленное ради ссылки.
Серым после имени — id записи и правила, которые её изменили.</p>
<nav>{"".join(nav)}</nav>
{"".join(body)}
</main></body></html>
"""
    out = args.out or os.path.join(ROOT, "tools", "reports",
                                   f"{args.what}-diff.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"{n} entries, {len(order)} groups -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
