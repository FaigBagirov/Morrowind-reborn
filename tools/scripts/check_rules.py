#!/usr/bin/env python3
"""Validate the rules table and preview every substitution it would make.

    python tools/scripts/check_rules.py

Writes nothing a game can load. It reads `tools/rules/naming.csv` and the
cached masters, applies the rules in memory, and reports what would change.
This is the gate the transform will inherit: *Conversion Architecture* Part 14
requires the transform to refuse to run on any of the violations checked here,
so they are checked here first, before there is an artifact to get wrong.

Matching is literal. Lua's `string.gsub` and Python's `re` both read their
needle as a pattern, and a rules table made of prose is full of pattern
characters; every match and every substitution below goes through `str.find`.
"""

import argparse
import collections
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wo1_survey import (  # noqa: E402
    DISPLAY_FIELDS, FROZEN, LUA_TYPES, field_values, load_masters,
)
from momw_compat import TYPE_CODE  # noqa: E402

MASTERS = ("Morrowind.json", "Tribunal.json", "Bloodmoon.json")


class Rule:
    __slots__ = ("id", "order", "pattern", "replacement", "types", "fields",
                 "left", "right", "case", "exclude", "notes")

    def __init__(self, row):
        self.id = row["id"].strip()
        self.order = int(row["order"])
        self.pattern = row["pattern"]
        self.replacement = row["replacement"]
        self.types = _list(row["applies_to_types"])
        self.fields = _list(row["applies_to_fields"])
        self.left = row["left_boundary"].strip().lower() == "yes"
        self.right = row["right_boundary"].strip().lower() == "yes"
        self.case = row["case_handling"].strip().lower()
        self.exclude = {r.lower() for r in row["exclude_records"].split()}
        self.notes = row["notes"]

    def applies(self, code, field):
        if self.types != ["*"] and code not in self.types:
            return False
        if self.fields != ["*"] and field not in self.fields:
            return False
        return True


def _list(cell):
    cell = cell.strip()
    return ["*"] if cell == "*" or not cell else cell.replace(",", " ").split()


def load_rules(path):
    with open(path, newline="", encoding="utf-8") as f:
        rules = [Rule(r) for r in csv.DictReader(f)]
    rules.sort(key=lambda r: r.order)
    return rules


def validate(rules):
    """Every check Part 14 requires the transform to refuse to run on."""
    errors, warnings = [], []

    orders = collections.Counter(r.order for r in rules)
    for order, n in orders.items():
        if n > 1:
            errors.append(f"order {order} used by {n} rules - order must be total")

    ids = collections.Counter(r.id for r in rules)
    for rid, n in ids.items():
        if n > 1:
            errors.append(f"rule id {rid} used {n} times")

    for r in rules:
        if len(r.replacement) > len(r.pattern):
            errors.append(f"{r.id}: replacement is longer than pattern "
                          f"({len(r.replacement)} > {len(r.pattern)})")
        for label, text in (("pattern", r.pattern),
                            ("replacement", r.replacement)):
            bad = [c for c in text if ord(c) > 127]
            if bad:
                errors.append(f"{r.id}: {label} is not ASCII: {bad!r}")
        if r.case not in ("mirror", "literal"):
            errors.append(f"{r.id}: case_handling {r.case!r} is neither "
                          f"mirror nor literal")
        if not r.pattern:
            errors.append(f"{r.id}: empty pattern")

    # Idempotence, statically: no replacement may contain any rule's pattern,
    # or a second run would rewrite the first run's output.
    for r in rules:
        for other in rules:
            if other.pattern.lower() in r.replacement.lower():
                errors.append(f"{r.id}: replacement {r.replacement!r} contains "
                              f"{other.id}'s pattern {other.pattern!r} - "
                              f"the transform would not be idempotent")

    # Ordering: a rule whose pattern contains an earlier rule's pattern can
    # never fire, because the earlier rule has already consumed the text.
    for i, r in enumerate(rules):
        for earlier in rules[:i]:
            if earlier.pattern.lower() in r.pattern.lower():
                errors.append(f"{r.id} (order {r.order}) can never fire: its "
                              f"pattern contains {earlier.id}'s pattern "
                              f"{earlier.pattern!r}, applied first")

    # Reachability, against the WO0 measurements.
    for r in rules:
        if r.types == ["*"]:
            continue
        for code in r.types:
            if code not in TYPE_CODE.values():
                warnings.append(f"{r.id}: unknown record code {code}")

    return errors, warnings


def is_letter(ch):
    return ch.isalpha()


def find_all(haystack, needle, left, right):
    """Literal search, honouring word boundaries. Never a regular expression."""
    out = []
    low_h, low_n = haystack.lower(), needle.lower()
    pos = 0
    while True:
        i = low_h.find(low_n, pos)
        if i < 0:
            return out
        j = i + len(needle)
        ok = True
        if left and i > 0 and is_letter(haystack[i - 1]):
            ok = False
        if right and j < len(haystack) and is_letter(haystack[j]):
            ok = False
        if ok:
            out.append((i, j))
        pos = i + 1


def shape(text):
    """lower / sentence / title / upper / other - the mirror classifier.

    `sentence` earns its place: "Daedric ruin" is the commonest shape in the
    game and it is neither Title Case nor lower. Without it the classifier
    rejected 197 perfectly ordinary matches and buried the real oddities in
    its own false alarms.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "other"
    if all(c.islower() for c in letters):
        return "lower"
    if all(c.isupper() for c in letters):
        return "upper"
    words = [w for w in text.split() if w and w[0].isalpha()]
    if words and all(w[0].isupper() and w[1:].islower() for w in words):
        return "title"
    if (words and words[0][0].isupper() and words[0][1:].islower()
            and all(w.islower() for w in words[1:])):
        return "sentence"
    return "other"


def cast(replacement, matched, case_mode):
    if case_mode == "literal":
        return replacement, None
    s = shape(matched)
    if s == "lower":
        return replacement.lower(), None
    if s == "upper":
        return replacement.upper(), None
    if s in ("title", "sentence"):
        # The replacement is authored in the same shape it is written back in.
        return replacement, None
    return replacement, f"unclassified case {matched!r}"


def following_word(text, end):
    """The word after a match, markup stripped - evidence for the next rule."""
    tail = text[end:end + 40]
    while tail.startswith("<"):
        close = tail.find(">")
        if close < 0:
            break
        tail = tail[close + 1:]
    tail = " ".join(tail.split())
    word = tail.split(" ")[0] if tail else ""
    return word.strip(".,;:!?\"'()").lower()


def markup_spans(text):
    """Byte ranges inside pseudo-HTML tags, which are machine references.

    Book text carries markup, and `FACE="Daedric"` names a **font** - 83 of
    them across the masters. Rewriting it would leave the page pointing at a
    font that does not exist. The same class of trap as `sMagicDaedrothID`: a
    string that looks like prose and is not. Nothing inside a tag is ever
    substituted.
    """
    spans, i = [], 0
    while True:
        a = text.find("<", i)
        if a < 0:
            return spans
        b = text.find(">", a)
        if b < 0:
            spans.append((a, len(text)))
            return spans
        spans.append((a, b + 1))
        i = b + 1


def in_spans(i, j, spans):
    return any(a <= i and j <= b for a, b in spans)


def apply_rules(value, rules, code, field, record_id):
    """Return (new value, [(rule id, matched, written, next word)], [notes]).

    One left-to-right pass per rule. Replacements are validated never to
    contain any rule's pattern, so a single pass is complete and the result is
    idempotent.
    """
    applied, notes, protected_hits = [], [], []
    rid = record_id.lower()
    for r in rules:
        if not r.applies(code, field) or rid in r.exclude:
            continue
        spans = markup_spans(value)
        matches = find_all(value, r.pattern, r.left, r.right)
        if not matches:
            continue
        out, prev = [], 0
        for i, j in matches:
            if in_spans(i, j, spans):
                protected_hits.append((r.id, value[i:j],
                                       value[max(0, i - 24):j + 4]))
                continue
            matched = value[i:j]
            nxt = following_word(value, j)
            written, note = cast(r.replacement, matched, r.case)
            if note:
                notes.append(f"{r.id}: {note}")
            out.append(value[prev:i])
            out.append(written)
            prev = j
            applied.append((r.id, matched, written, nxt))
        out.append(value[prev:])
        value = "".join(out)
    return value, applied, notes, protected_hits


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rules", default=os.path.join(root, "tools", "rules",
                                                    "naming.csv"))
    ap.add_argument("--cache-dir", default=os.path.join(root, "tools", "cache"))
    ap.add_argument("--out", default=os.path.join(root, "tools", "reports"))
    args = ap.parse_args()

    rules = load_rules(args.rules)
    print(f"Loaded {len(rules)} rules from "
          f"{os.path.relpath(args.rules, root)}")

    errors, warnings = validate(rules)
    for w in warnings:
        print("  warning:", w)
    if errors:
        print("")
        for e in errors:
            print("  REFUSED:", e)
        raise SystemExit(f"\n{len(errors)} violations - the transform would "
                         f"refuse to run on this table")
    print("  table passes: order total, ASCII, length, idempotence, ordering")

    fired = collections.Counter()
    in_markup = collections.Counter()
    markup_examples = []
    rows = []
    default_hits = collections.Counter()
    unclassified = []
    excluded = []

    print("Previewing against the masters ...")
    paths = [os.path.join(args.cache_dir, n) for n in MASTERS]
    for path in paths:
        if not os.path.exists(path):
            raise SystemExit(f"missing {path} - run wo1_survey.py first")
    # Merged last-wins, as the engine loads them. Counting each master
    # separately would inflate every figure by the expansion overrides - 5,132
    # INFO records alone are defined more than once.
    records = load_masters(paths)

    for rec in records.values():
        rtype = rec["type"]
        specs = DISPLAY_FIELDS.get(rtype)
        if not specs:
            continue
        code = TYPE_CODE.get(rtype)
        if code is None:
            continue
        rid = str(rec.get("id", "") or "")
        for r in rules:
            if rid.lower() in r.exclude:
                excluded.append((r.id, code, rid))
        for spec in specs:
            if (rtype, spec) in FROZEN:
                continue
            field = spec.split(".")[0] if "." in spec else spec
            for value in field_values(rec, spec):
                new_value, applied, notes, protected = apply_rules(
                    value, rules, code, field, rid)
                for rule_id, matched, ctx in protected:
                    in_markup[(rule_id, matched)] += 1
                    if len(markup_examples) < 6:
                        markup_examples.append(f"{code} {rid}: ...{ctx}...")
                if not applied:
                    continue
                for rule_id, matched, written, nxt in applied:
                    fired[rule_id] += 1
                    if rule_id == "R300":
                        default_hits[nxt] += 1
                unclassified.extend(f"{code} {rid}: {n}" for n in notes)
                rows.append({
                    "record_type": code,
                    "record_id": rid,
                    "field": spec,
                    "route": "lua" if rtype in LUA_TYPES else "plugin",
                    "rules": " ".join(sorted({a[0] for a in applied})),
                    "length_delta": len(new_value) - len(value),
                    "before": value if len(value) < 400 else value[:400] + " ...",
                    "after": (new_value if len(new_value) < 400
                              else new_value[:400] + " ..."),
                })

    os.makedirs(args.out, exist_ok=True)
    prev = os.path.join(args.out, "rules-preview.csv")
    with open(prev, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["record_type", "record_id", "field",
                                          "route", "rules", "length_delta",
                                          "before", "after"])
        w.writeheader()
        w.writerows(rows)

    print("")
    print(f"Records touched: {len(rows)}")
    by_route = collections.Counter(r["route"] for r in rows)
    print(f"  lua {by_route['lua']}   plugin {by_route['plugin']}")
    longer = [r for r in rows if r["length_delta"] > 0]
    print(f"  fields that grew: {len(longer)} (must be 0)")
    print("")
    print("Rule firing counts:")
    for r in rules:
        n = fired.get(r.id, 0)
        flag = "   <-- NEVER FIRES, defect per Part 14" if n == 0 else ""
        print(f"  {r.id}  order {r.order:4}  {n:5}  {r.pattern!r}{flag}")
    print("")
    print("What reached the R300 default, by the word that follows it:")
    for word, n in default_hits.most_common(30):
        print(f"  {n:4}  Daedric {word}")
    if in_markup:
        print("")
        print("Matches inside markup, protected and NOT substituted:")
        for (rule_id, matched), n in in_markup.most_common():
            print(f"  {n:4}  {rule_id}  {matched!r}")
        for ex in markup_examples:
            print("   ", ex[:150])
    if unclassified:
        print("")
        print(f"Unclassified case, written literally: {len(unclassified)}")
        for u in unclassified[:10]:
            print("   ", u)
    if excluded:
        print("")
        print("Exclusions that matched a real record:")
        for rule_id, code, rid in sorted(set(excluded)):
            print(f"  {rule_id} skipped {code} {rid}")
    print("")
    print("Wrote", os.path.relpath(prev, root))


if __name__ == "__main__":
    main()
