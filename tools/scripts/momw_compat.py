#!/usr/bin/env python3
"""Compatibility check: do our edits collide with the MOMW graphics-overhaul list?

    python tools/scripts/momw_compat.py --mods "D:/Games/OpenMWMods/graphics-overhaul"

The question is not "do these mods work with ours" in the abstract. It is
mechanical and it has an exact answer:

  * The **Lua half** edits records in place from the load context, after every
    content file has loaded. It rewrites one field of a record and leaves the
    rest alone, and it reads the value it is substituting into - so if a mod
    changed a book's text, our rule applies to the modded text. Load order
    cannot break this and neither can a plugin. It is compatible by
    construction, and this script does not need to prove it. What it does
    check is the one thing that could still bite: another **Lua** mod writing
    the same records.

  * The **plugin half** is different. A Morrowind plugin overrides a record
    *whole*, not field by field. If a graphics mod edits a weapon to change
    its mesh and our plugin edits the same weapon to change its name, the one
    that loads later wins entirely and silently discards the other's work.
    That collision is what this script finds: the intersection of the record
    IDs our plugin would touch with the record IDs every plugin in the list
    touches.

Plugins are read straight out of the binary rather than through tes3conv: the
list is ~2 GB across ~700 files and converting it all is not practical. The
reader is validated against tes3conv on Morrowind.esm - every record type
matches exactly - and the check is re-run by `--selfcheck`.
"""

import argparse
import collections
import csv
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wo1_survey import (  # noqa: E402
    DISPLAY_FIELDS, KEYWORD_RULES, LUA_TYPES, FROZEN, field_values,
    stream_records,
)

# tes3conv's record type names against the four-character codes in the binary.
TYPE_CODE = {
    "Book": "BOOK", "Spell": "SPEL", "Ingredient": "INGR", "MiscItem": "MISC",
    "GameSetting": "GMST", "Weapon": "WEAP", "Armor": "ARMO",
    "Creature": "CREA", "Clothing": "CLOT", "Class": "CLAS",
    "DialogueInfo": "INFO", "Dialogue": "DIAL", "Cell": "CELL",
    "Script": "SCPT", "Npc": "NPC_", "Alchemy": "ALCH", "Light": "LIGH",
    "Activator": "ACTI", "Door": "DOOR", "Apparatus": "APPA",
    "Lockpick": "LOCK", "Probe": "PROB", "RepairItem": "REPA",
    "Container": "CONT", "Faction": "FACT", "Race": "RACE",
    "Birthsign": "BSGN", "Region": "REGN", "Skill": "SKIL",
    "MagicEffect": "MGEF",
}

PLUGIN_EXT = (".esp", ".esm", ".omwaddon")


def walk_plugin(path, wanted=None):
    """Yield (record code, id, parent topic) from a TES3 plugin.

    Record header is 16 bytes - type[4], size u32, unused u32, flags u32 -
    followed by subrecords of type[4], size u32, data. The id lives in NAME
    for most record types and in INAM for INFO.
    """
    with open(path, "rb") as f:
        data = f.read()
    pos, end = 0, len(data)
    topic = ""
    while pos + 16 <= end:
        code = data[pos:pos + 4].decode("ascii", "replace")
        size = struct.unpack_from("<I", data, pos + 4)[0]
        body = pos + 16
        stop = body + size
        if stop > end:
            return  # truncated file; stop rather than guess
        rid = None
        if code == "DIAL" or wanted is None or code in wanted:
            p = body
            while p + 8 <= stop:
                sub = data[p:p + 4].decode("ascii", "replace")
                ssize = struct.unpack_from("<I", data, p + 8 - 4)[0]
                if sub in ("NAME", "INAM"):
                    raw = data[p + 8:p + 8 + ssize].split(b"\x00")[0]
                    rid = raw.decode("cp1252", "replace")
                    break
                p = p + 8 + ssize
        if code == "DIAL":
            topic = rid or ""
        # DIAL is yielded as well as tracked, so the self-check can compare
        # every record type against tes3conv without a special case.
        if wanted is None or code in wanted or code == "DIAL":
            yield code, rid, (topic if code == "INFO" else None)
        pos = stop


def target_records(cache_dir):
    """Every master record our rules would touch, keyed as the plugin walker
    keys them, split by route.

    Two INFO sets, because they answer different questions. The broad set is
    every INFO carrying a keyword. The strict set applies the project's own
    dialogue policy on top - Architecture Part 5 and the rules in CLAUDE.md
    allow only uniquely-filtered INFO records to be rewritten, never greetings,
    never journals, never general responses - so it is the one the transform
    would actually touch. The broad set is the ceiling.
    """
    targets = collections.defaultdict(set)   # route -> {(code, id, topic)}
    per_type = collections.Counter()
    for name in ("Morrowind.json", "Tribunal.json", "Bloodmoon.json"):
        path = os.path.join(cache_dir, name)
        if not os.path.exists(path):
            raise SystemExit(
                f"missing {path} - run tools/scripts/wo1_survey.py first"
            )
        topic = ""
        for rec in stream_records(path):
            rtype = rec.get("type")
            if rtype == "Dialogue":
                topic = rec.get("id", "")
            specs = DISPLAY_FIELDS.get(rtype)
            if not specs:
                continue
            hit = False
            for spec in specs:
                for value in field_values(rec, spec):
                    if any(p.search(value) for _, p in KEYWORD_RULES):
                        if (rtype, spec) in FROZEN:
                            continue
                        hit = True
            if not hit:
                continue
            code = TYPE_CODE.get(rtype)
            if code is None:
                continue
            rid = rec.get("id", "") if rtype != "Cell" else rec.get("name", "")
            key = (code, str(rid).lower(),
                   topic.lower() if code == "INFO" else None)
            route = "lua" if rtype in LUA_TYPES else "plugin"
            targets[route].add(key)
            per_type[(route, code)] += 1
            if code == "INFO":
                speaker = str(rec.get("speaker_id", "") or "")
                dtype = str(rec.get("data", {}).get("dialogue_type", ""))
                if speaker and dtype == "Topic":
                    targets["plugin_strict"].add(key)
            elif route == "plugin":
                targets["plugin_strict"].add(key)
    return targets, per_type


def scan_mods(mods_dir, wanted):
    """Every record of interest each plugin in the list touches."""
    plugins = []
    for root, _dirs, files in os.walk(mods_dir):
        for fn in files:
            if fn.lower().endswith(PLUGIN_EXT):
                plugins.append(os.path.join(root, fn))
    plugins.sort()

    edits = {}
    for i, path in enumerate(plugins, 1):
        rel = os.path.relpath(path, mods_dir).replace("\\", "/")
        if i % 50 == 0 or i == len(plugins):
            print(f"  {i}/{len(plugins)} plugins ...", flush=True)
        seen = set()
        try:
            for code, rid, topic in walk_plugin(path, wanted):
                if rid is None:
                    continue
                seen.add((code, rid.lower(),
                          topic.lower() if code == "INFO" else None))
        except (OSError, struct.error) as exc:
            print(f"  ! unreadable, skipped: {rel} ({exc})", flush=True)
            continue
        edits[rel] = seen
    return edits


def scan_lua_mods(mods_dir):
    """Lua mods that write records from the load context - the only way the
    Lua half of our mod can collide with anything."""
    hits = []
    for root, _dirs, files in os.walk(mods_dir):
        for fn in files:
            if not fn.lower().endswith(".lua"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            if "openmw.content" not in text:
                continue
            wrote = [ln.strip() for ln in text.splitlines()
                     if "content." in ln and "=" in ln and
                     not ln.strip().startswith("--")]
            hits.append((os.path.relpath(path, mods_dir).replace("\\", "/"),
                         wrote[:6]))
    return hits


def selfcheck(esm, cache_json):
    """The reader against tes3conv on the same file, every record type."""
    mine = collections.Counter()
    for code, _rid, _topic in walk_plugin(esm, wanted=None):
        mine[code] += 1
    theirs = collections.Counter()
    for rec in stream_records(cache_json):
        code = TYPE_CODE.get(rec.get("type"))
        theirs[code if code else rec.get("type")] += 1
    bad = []
    for code, n in theirs.items():
        if code in TYPE_CODE.values() and mine.get(code, 0) != n:
            bad.append((code, n, mine.get(code, 0)))
    total_ok = sum(mine.values())
    print(f"  reader total records: {total_ok}")
    if bad:
        for code, want, got in bad:
            print(f"  MISMATCH {code}: tes3conv {want}, reader {got}")
        return False
    print("  every record type matches tes3conv")
    return True


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mods", default="D:/Games/OpenMWMods/graphics-overhaul")
    ap.add_argument("--cache-dir", default=os.path.join(root, "tools", "cache"))
    ap.add_argument("--out", default=os.path.join(root, "tools", "reports"))
    ap.add_argument("--selfcheck", action="store_true",
                    help="validate the binary reader against tes3conv first")
    args = ap.parse_args()

    if args.selfcheck:
        print("Self-check against tes3conv ...")
        ok = selfcheck(os.path.join(root, "tools", "input", "Morrowind.esm"),
                       os.path.join(args.cache_dir, "Morrowind.json"))
        if not ok:
            raise SystemExit("reader disagrees with tes3conv - stopping")

    print("Building the target set from the masters ...")
    targets, per_type = target_records(args.cache_dir)
    plugin_targets = targets["plugin"]
    strict_targets = targets["plugin_strict"]
    lua_targets = targets["lua"]
    wanted = {code for code, _rid, _t in plugin_targets | lua_targets}
    print(f"  plugin route: {len(plugin_targets)} records "
          f"({len(strict_targets)} after the dialogue policy)")
    print(f"  lua route   : {len(lua_targets)} records")

    print(f"Scanning {args.mods} ...")
    edits = scan_mods(args.mods, wanted)
    print(f"  {len(edits)} plugins read")

    print("Scanning Lua mods ...")
    lua_mods = scan_lua_mods(args.mods)
    print(f"  {len(lua_mods)} Lua files touch openmw.content")

    # Intersect.
    collisions = {}       # plugin -> {route: set of keys}
    for rel, seen in edits.items():
        p_hit = seen & plugin_targets
        s_hit = seen & strict_targets
        l_hit = seen & lua_targets
        if p_hit or l_hit:
            collisions[rel] = {"plugin": p_hit, "strict": s_hit, "lua": l_hit}

    os.makedirs(args.out, exist_ok=True)
    csv_path = os.path.join(args.out, "momw-compat.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["plugin", "route", "in_strict_set", "record_type",
                    "record_id", "topic"])
        for rel in sorted(collisions):
            for route in ("plugin", "lua"):
                for key in sorted(collisions[rel][route]):
                    code, rid, topic = key
                    strict = "yes" if key in collisions[rel]["strict"] else "no"
                    w.writerow([rel, route, strict, code, rid, topic or ""])

    # Console summary; the write-up is authored by hand from these numbers.
    print("")
    print("=== RESULT ===")
    hard = {r: d for r, d in collisions.items() if d["plugin"]}
    soft = {r: d for r, d in collisions.items() if d["lua"] and not d["plugin"]}
    print(f"Plugins colliding on the PLUGIN route (real conflicts): {len(hard)}")
    for rel in sorted(hard, key=lambda r: -len(collisions[r]["plugin"]))[:25]:
        n = len(collisions[rel]["plugin"])
        ns = len(collisions[rel]["strict"])
        codes = collections.Counter(c for c, _i, _t in collisions[rel]["plugin"])
        print(f"  {n:5} ({ns} after policy)  {rel}")
        print(f"         {dict(codes)}")
    print("")
    print(f"Plugins touching LUA-route records (no conflict, in-place wins): "
          f"{len(soft)}")
    for rel in sorted(soft, key=lambda r: -len(collisions[r]["lua"]))[:15]:
        codes = collections.Counter(c for c, _i, _t in collisions[rel]["lua"])
        print(f"  {len(collisions[rel]['lua']):5}  {rel}  {dict(codes)}")
    print("")
    print("Lua mods writing openmw.content:")
    for rel, lines in lua_mods:
        print(f"  {rel}")
        for ln in lines:
            print(f"      {ln[:100]}")
    print("")
    print("Wrote", os.path.relpath(csv_path, root))


if __name__ == "__main__":
    main()
