"""What does a player still read that the conversion has not accounted for?

The rules table says what changes. This says what is left, which is a different
question and the one that decides whether the game is playable and shareable.

The cut that matters is not "which words remain" - the setting deliberately
keeps mortal vocabulary, so "magicka" in a book is a decision, not a defect. It
is **who is speaking**. A game setting, an effect description, a skill or a
birthsign is the game talking in its own voice, and there it must be
consistent. A book, a dialogue line or a class biography is a person talking,
and there the old words are the point.

So every string is filed under one of those two voices before it is counted,
and only the first is a defect. Run with no arguments:

    python tools/scripts/audit.py
"""

import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_rules as cr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CACHE = os.path.join(ROOT, "tools", "cache")
MASTERS = ("Morrowind.json", "Tribunal.json", "Bloodmoon.json")

# Which fields a player actually reads, and whose voice they are in.
# code is the four-letter type the rules table scopes on.
ENGINE = [
    ("GameSetting", "value",       "GMST"),
    ("MagicEffect", "description", "MGEF"),
    ("Skill",       "description", "SKIL"),
    ("Birthsign",   "name",        "BSGN"),
    ("Birthsign",   "description", "BSGN"),
    ("Spell",       "name",        "SPEL"),
    ("Alchemy",     "name",        "ALCH"),
    ("Enchanting",  "name",        "ENCH"),
    ("Armor",       "name",        "ARMO"),
    ("Weapon",      "name",        "WEAP"),
    ("Clothing",    "name",        "CLOT"),
    ("MiscItem",    "name",        "MISC"),
    ("Ingredient",  "name",        "INGR"),
    ("Creature",    "name",        "CREA"),
    ("Npc",         "name",        "NPC_"),
    ("Faction",     "name",        "FACT"),
    ("Race",        "name",        "RACE"),
    ("Class",       "name",        "CLAS"),
    ("Region",      "name",        "REGN"),
    ("Cell",        "name",        "CELL"),
]
MORTAL = [
    # A book's title is written by its author, who is a mortal. It shows in the
    # inventory, but so does a mortal's name.
    ("Book",          "name",        "BOOK"),
    ("Book",          "text",        "BOOK"),
    ("DialogueInfo",  "text",        "INFO"),
    ("Class",         "description", "CLAS"),
    ("Faction",       "rank_names",  "FACT"),
]

# Vocabulary the setting has an answer for, and vocabulary it has not.
BUCKETS = collections.OrderedDict([
    # Should be zero everywhere after the rules run. Anything here is a miss.
    ("daedra",   r"\b(?:a?edra|daedr\w*|daedroth)\b"),
    # Renamed in the engine's voice only. In a mortal's voice it is kept.
    ("magicka",  r"\bmagicka\b|\bmagika\b|\bspell points\b"),
    # No rule touches these at all. In the engine's voice they contradict a
    # setting whose whole premise is that there is no magic.
    ("arcane",   r"\b(?:magic|magical|magically|spell|spells|spellcasting|"
                 r"spellcaster|cast|casts|casting|enchant\w*|sorcer\w*|"
                 r"wizard\w*|witch\w*|mage|mages|arcane|conjur\w*|"
                 r"necroman\w*|rune|runes|scroll|scrolls)\b"),
    # Religion. Canon keeps the Temple as a cult, so this is a judgement call
    # rather than a defect - counted so the judgement is made on numbers.
    ("divine",   r"\b(?:god|gods|goddess|divine|divinity|holy|saint|saints|"
                 r"prayer|prayers|blessing|blessings|soul|souls|worship\w*|"
                 r"sacred|blasphem\w*)\b"),
])
PATTERNS = {k: re.compile(v, re.I) for k, v in BUCKETS.items()}


def load_masters():
    merged = {}
    for name in MASTERS:
        path = os.path.join(CACHE, name)
        if not os.path.exists(path):
            raise SystemExit(f"missing {path} - run tools/scripts/wo1_survey.py")
        for rec in json.load(open(path, encoding="utf-8")):
            rid = (rec.get("id") or rec.get("effect_id") or
                   rec.get("skill_id") or "")
            merged[(rec.get("type"), str(rid))] = rec
    return merged


def strings(rec, field):
    """One field can be a string, a list of them, or a typed GMST value."""
    v = rec.get(field)
    if v is None:
        return []
    if isinstance(v, dict):                       # GameSetting
        return [v["data"]] if v.get("type") == "String" else []
    if isinstance(v, list):                       # Faction rank_names
        return [x for x in v if isinstance(x, str)]
    return [v] if isinstance(v, str) else []


def main():
    rules = cr.load_rules(os.path.join(ROOT, "tools", "rules", "naming.csv"))
    frozen = cr.load_frozen(os.path.join(ROOT, "tools", "rules",
                                         "frozen-records.csv"))
    merged = load_masters()
    print(f"{len(merged)} records over the three masters, "
          f"{len(rules)} rules applied before counting\n")

    tally = collections.defaultdict(lambda: collections.defaultdict(int))
    records = collections.defaultdict(lambda: collections.defaultdict(set))
    sample = collections.defaultdict(list)

    for voice, spec in (("engine", ENGINE), ("mortal", MORTAL)):
        for jtype, field, code in spec:
            for (t, rid), rec in merged.items():
                if t != jtype:
                    continue
                for raw in strings(rec, field):
                    after = cr.apply_rules(raw, rules, code, field,
                                          rid, frozen)[0]
                    for bucket, pat in PATTERNS.items():
                        hits = pat.findall(after)
                        if not hits:
                            continue
                        key = (voice, bucket)
                        tally[key][(code, field)] += len(hits)
                        records[key][(code, field)].add(rid)
                        if len(sample[(voice, bucket, code, field)]) < 3:
                            sample[(voice, bucket, code, field)].append(
                                (rid, after.strip()[:150]))

    for voice in ("engine", "mortal"):
        title = ("THE GAME IN ITS OWN VOICE - every count here is a defect "
                 "except where noted" if voice == "engine"
                 else "MORTALS SPEAKING - kept on purpose, listed for scale")
        print("=" * 78)
        print(title)
        print("=" * 78)
        for bucket in BUCKETS:
            key = (voice, bucket)
            if not tally[key]:
                print(f"\n  {bucket:8} none")
                continue
            total = sum(tally[key].values())
            recs = sum(len(v) for v in records[key].values())
            print(f"\n  {bucket:8} {total:6} occurrences in {recs} records")
            for (code, field), n in sorted(tally[key].items(),
                                           key=lambda x: -x[1]):
                r = len(records[key][(code, field)])
                print(f"      {n:6}  {r:5} rec  {code} {field}")
    print()

    print("=" * 78)
    print("EXAMPLES, the engine's voice only")
    print("=" * 78)
    for (voice, bucket, code, field), items in sorted(sample.items()):
        if voice != "engine":
            continue
        print(f"\n  {bucket} / {code} {field}")
        for rid, text in items:
            print(f"      {rid}: {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
