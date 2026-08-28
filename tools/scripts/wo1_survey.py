#!/usr/bin/env python3
"""WO1 - keyword and dialogue survey over the three Morrowind masters.

Reads tes3conv JSON dumps and writes four CSV reports plus a summary to
tools/reports/.

Run with no arguments from anywhere:

    python tools/scripts/wo1_survey.py

It converts tools/input/*.esm to JSON in tools/cache/ with tools/bin/tes3conv.exe
if the JSON is not already there, then surveys the JSON. Both directories can be
overridden; see --help.

What changed against the first pass (all four defects listed in CLAUDE.md):

  1. Cell records carry their name in "name", not "id", and the interior flag
     lives in data.flags. The first pass read rec["id"] and the top-level
     "flags", so every cell collapsed onto the key "" and no cell was ever
     interior. The reference count of 1231 was just "every script contains the
     empty string".
  2. Paths are no longer hardcoded to a scratch directory of another tool.
  3. The cast list is built from the actor-ID filter alone. The first pass kept
     an INFO only if it was actor-filtered AND contained a keyword, which is
     "who says daedra", not "who knows". Keyword columns are still reported
     alongside, so the old lower bound stays derivable.
  4. occurrence_count now counts occurrences. unique_record_count is a new
     column, and it is the one to plan against: 163 occurrences of "daedric" in
     book text could be one book or 163.

Also fixed here:

  - "aedra" carries a left word boundary. Without it the string inside "daedra"
    is counted, and the first pass reported more "aedra" than "daedra" in INFO
    text - 338 against 315 - which is the tell. Shared World Canon Part 10.
  - The field map covered name/text/description only. GMST strings live in
    value.data and were invisible; faction rank names live in a list. Both are
    covered now, and every scanned field is declared per record type in
    DISPLAY_FIELDS below rather than guessed.
  - Records redefined by an expansion are merged last-wins, as the engine loads
    them, instead of being counted once per master.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys

# Rule order is fixed and versioned: the longer daedra-family strings are
# matched before "aedra", and "aedra" carries a left word boundary so it cannot
# fire inside "daedra". The transform script in WO2 must use this same order.
KEYWORD_RULES = [
    ("daedroth", re.compile(r"daedroth", re.IGNORECASE)),
    ("daedric", re.compile(r"daedric", re.IGNORECASE)),
    ("daedra", re.compile(r"daedra", re.IGNORECASE)),
    ("aedra", re.compile(r"(?<![A-Za-z])aedra", re.IGNORECASE)),
]

# Display fields per record type. A "*" prefix marks a list-of-strings field; a
# dotted name is a path into a nested object. Anything not listed here is not
# scanned - IDs, mesh and icon paths, script bodies and sound paths are display
# -irrelevant or forbidden to touch by the rules in CLAUDE.md.
DISPLAY_FIELDS = {
    "Activator": ["name"],
    "Alchemy": ["name"],
    "Apparatus": ["name"],
    "Armor": ["name"],
    "Birthsign": ["name", "description"],
    "Book": ["name", "text"],
    "Cell": ["name"],
    "Class": ["name", "description"],
    "Clothing": ["name"],
    "Container": ["name"],
    "Creature": ["name"],
    "Dialogue": ["id"],
    "DialogueInfo": ["text"],
    "Door": ["name"],
    "Faction": ["name", "*rank_names"],
    "GameSetting": ["value.data"],
    "Ingredient": ["name"],
    "Light": ["name"],
    "Lockpick": ["name"],
    "MagicEffect": ["description"],
    "MiscItem": ["name"],
    "Npc": ["name"],
    "Probe": ["name"],
    "Race": ["name", "description"],
    "Region": ["name"],
    "RepairItem": ["name"],
    "Script": ["text"],
    "Skill": ["description"],
    "Spell": ["name"],
    "Weapon": ["name"],
}

# Where a hit would have to be rewritten, per the WO0 result (Architecture
# Part 12). This is a hint for planning, not a measurement: only BOOK text,
# GMST, SPEL name, INGR name and MGEF name were actually probed. The rest of
# the "lua" rows share a content sub-package with a probed record, and the
# "plugin" rows are there because the sub-package does not exist at all.
LUA_TYPES = {
    "Activator", "Alchemy", "Book", "Door", "GameSetting", "Ingredient",
    "Light", "MagicEffect", "MiscItem", "Probe", "Spell",
}
FROZEN = {
    ("Dialogue", "id"): "frozen: topic IDs are never renamed",
    ("Cell", "name"): "frozen: cell names are never renamed",
    ("Script", "text"): "frozen: script bodies are never touched",
}

# Types worth keeping in memory. Landscape, PathGrid, Bodypart and the leveled
# lists carry no display string and are the bulk of the file.
KEEP_TYPES = set(DISPLAY_FIELDS) | {"Script"}

WORD_RE = re.compile(r"\b\w+\b")
QUOTED_RE = re.compile(r'"([^"\r\n]*)"')
TOKEN_RE = re.compile(r"[A-Za-z0-9_'\-]+")

# Script lines that put a string on the player's screen. Everything else in a
# script body is an ID reference, a comment or a variable name.
SCRIPT_DISPLAY_RE = re.compile(r"\b(MessageBox|Say|Choice)\b", re.IGNORECASE)


def stream_records(filepath):
    """Yield top-level objects from a tes3conv JSON array.

    Relies on tes3conv's indentation: an object starts at '  {' and ends at
    '  }'. Do not feed this compact (-c) output.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        buffer = []
        for line in f:
            if line.startswith("  }") and buffer:
                buffer.append("}")
                try:
                    yield json.loads("".join(buffer))
                except json.JSONDecodeError:
                    pass
                buffer = []
            elif line.startswith("  {") and not buffer:
                buffer.append("{")
            elif buffer:
                buffer.append(line)


def field_values(rec, spec):
    """Return the list of strings a field spec selects from a record."""
    if spec.startswith("*"):
        val = rec.get(spec[1:])
        if isinstance(val, list):
            return [v for v in val if isinstance(v, str) and v]
        return []
    node = rec
    for part in spec.split("."):
        if not isinstance(node, dict):
            return []
        node = node.get(part)
    return [node] if isinstance(node, str) and node else []


def record_key(rec, topic=None):
    """Identity of a record for last-wins merging across the three masters.

    INFO ids are not globally unique - Morrowind.esm alone reuses 211 of them -
    so an INFO is identified by its parent topic together with its id. Keying on
    the id alone silently merges unrelated lines: it cost Eno Hlaalu half his
    dialogue before the esmtool cross-check caught it.
    """
    rtype = rec.get("type")
    if rtype == "Cell":
        grid = rec.get("data", {}).get("grid")
        return (rtype, rec.get("name", ""), tuple(grid) if grid else None)
    if rtype == "DialogueInfo":
        return (rtype, str(topic or "").lower(), str(rec.get("id", "")).lower())
    # Not every record type keys on "id". Skill uses skill_id and MagicEffect
    # uses effect_id, and keying those on a missing "id" collapsed all 27
    # skills onto one entry and all 142 magic effects onto another. Found by
    # the WO2 transform disagreeing with the compatibility check by one record.
    ident = (rec.get("id") or rec.get("skill_id") or rec.get("effect_id")
             or rec.get("name") or "")
    return (rtype, str(ident).lower())


def slim(rec, topic=None):
    """Drop everything the survey does not read. Cell reference lists alone are
    most of the file size."""
    rtype = rec["type"]
    keep = {"type": rec["type"]}
    if rtype == "DialogueInfo":
        keep["topic"] = topic or ""
    for key in ("id", "skill_id", "effect_id", "name", "text", "description",
                "value", "rank_names", "speaker_id", "data", "dialogue_type",
                "region"):
        if key in rec:
            keep[key] = rec[key]
    if rtype == "Cell":
        keep["data"] = {"flags": rec.get("data", {}).get("flags", ""),
                        "grid": rec.get("data", {}).get("grid")}
    return keep


def load_masters(json_files):
    """Merge the masters last-wins, as the engine loads them.

    An INFO record belongs to the DIAL topic that precedes it in the file, which
    is also half of its identity - see record_key.
    """
    records = {}
    for filepath in json_files:
        current_topic = ""
        seen = 0
        print(f"  reading {os.path.basename(filepath)} ...", flush=True)
        for rec in stream_records(filepath):
            seen += 1
            rtype = rec.get("type")
            if rtype == "Dialogue":
                current_topic = rec.get("id", "")
            if rtype in KEEP_TYPES:
                records[record_key(rec, current_topic)] = slim(rec,
                                                               current_topic)
        if seen == 0:
            raise SystemExit(
                f"parsed 0 records from {filepath} - the JSON is not "
                f"tes3conv's indented output"
            )
        print(f"    {seen} records", flush=True)
    return records


def survey_keywords(records):
    """Count keyword hits per (keyword, record type, field).

    occurrence_count is every match. unique_record_count is how many distinct
    records hold at least one - the number to plan against.
    """
    occ = {}
    for key, rec in records.items():
        rtype = rec["type"]
        for spec in DISPLAY_FIELDS.get(rtype, ()):
            for value in field_values(rec, spec):
                for kw, pattern in KEYWORD_RULES:
                    n = len(pattern.findall(value))
                    if n:
                        cell = occ.setdefault((kw, rtype, spec),
                                              {"occ": 0, "recs": set()})
                        cell["occ"] += n
                        cell["recs"].add(key)
    return occ


def route_for(rtype, field):
    frozen = FROZEN.get((rtype, field))
    if frozen:
        return frozen
    if rtype in LUA_TYPES:
        return "lua load context"
    return "plugin via tes3conv"


def write_keyword_report(occ, out_dir):
    path = os.path.join(out_dir, "wo1-keyword-occurrences.csv")
    rows = sorted(occ.items(), key=lambda kv: (-kv[1]["occ"], kv[0]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "record_type", "field", "occurrence_count",
                    "unique_record_count", "route_hint"])
        for (kw, rtype, field), data in rows:
            w.writerow([kw, rtype.upper(), field, data["occ"],
                        len(data["recs"]), route_for(rtype, field)])
    return path


def build_cast_list(records):
    """Every actor with actor-filtered INFO records - the actor-ID filter alone.

    keyword_* columns are the old, narrower selection, kept so the earlier
    lower bound stays comparable.
    """
    names = {}
    for (rtype, rid), rec in ((k[:2], v) for k, v in records.items()
                              if v["type"] in ("Npc", "Creature")):
        names[rid] = rec.get("name", "")

    cast = {}
    for rec in records.values():
        if rec["type"] != "DialogueInfo":
            continue
        speaker = str(rec.get("speaker_id", "") or "").lower()
        if not speaker:
            continue
        text = rec.get("text", "") or ""
        words = len(WORD_RE.findall(text))
        has_kw = any(p.search(text) for _, p in KEYWORD_RULES)
        row = cast.setdefault(speaker, {"infos": 0, "words": 0,
                                        "kw_infos": 0, "kw_words": 0})
        row["infos"] += 1
        row["words"] += words
        if has_kw:
            row["kw_infos"] += 1
            row["kw_words"] += words
    return cast, names


def write_cast_list(cast, names, out_dir):
    path = os.path.join(out_dir, "wo1-cast-list.csv")
    rows = sorted(cast.items(), key=lambda kv: -kv[1]["words"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["actor_id", "actor_name", "unique_info_count",
                    "total_words", "keyword_info_count", "keyword_words"])
        for actor_id, d in rows:
            w.writerow([actor_id, names.get(actor_id, ""), d["infos"],
                        d["words"], d["kw_infos"], d["kw_words"]])
    return path


def write_topic_inventory(records, out_dir):
    topics = {}
    for (rtype, rid), rec in ((k[:2], v) for k, v in records.items()
                              if v["type"] == "Dialogue"):
        tid = rec.get("id", "")
        topics[tid] = {
            "dialogue_type": str(rec.get("dialogue_type", "")),
            "info_count": 0,
            "keyword_info_count": 0,
            "contains_target_keyword": any(p.search(tid)
                                           for _, p in KEYWORD_RULES),
        }
    for rec in records.values():
        if rec["type"] != "DialogueInfo":
            continue
        parent = rec.get("topic", "")
        if parent not in topics:
            continue
        topics[parent]["info_count"] += 1
        text = rec.get("text", "") or ""
        if any(p.search(text) for _, p in KEYWORD_RULES):
            topics[parent]["keyword_info_count"] += 1

    path = os.path.join(out_dir, "wo1-topic-inventory.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["topic_id", "dialogue_type", "info_count",
                    "keyword_info_count", "contains_target_keyword"])
        for tid, d in sorted(topics.items()):
            w.writerow([tid, d["dialogue_type"], d["info_count"],
                        d["keyword_info_count"], d["contains_target_keyword"]])
    return path, topics


def count_script_references(cell_names, records):
    """How many scripts name each cell.

    Morrowind scripts quote multi-word cell names, so quoted literals carry
    almost all of it; single-word names are also matched as bare tokens. The
    first pass did a bare substring test against a key that was always the
    empty string, which matched every script.
    """
    counts = {name: 0 for name in cell_names}
    lowered = {name.lower(): name for name in cell_names}
    single = {n for n in lowered if " " not in n and "," not in n}
    for rec in records.values():
        if rec["type"] != "Script":
            continue
        text = (rec.get("text", "") or "").lower()
        if not text:
            continue
        hits = set()
        for literal in QUOTED_RE.findall(text):
            if literal in lowered:
                hits.add(literal)
        if single:
            for token in set(TOKEN_RE.findall(text)):
                if token in single:
                    hits.add(token)
        for h in hits:
            counts[lowered[h]] += 1
    return counts


def write_cell_report(records, out_dir):
    """Named cells only. Unnamed exteriors have no display string of their own -
    they show their region name - so there is nothing in them to rewrite."""
    cells = {}
    unnamed = 0
    for rec in records.values():
        if rec["type"] != "Cell":
            continue
        name = rec.get("name", "") or ""
        if not name:
            unnamed += 1
            continue
        flags = rec.get("data", {}).get("flags", "") or ""
        cells[name] = {
            "is_interior": "IS_INTERIOR" in flags,
            "contains_target_keyword": any(p.search(name)
                                           for _, p in KEYWORD_RULES),
        }
    counts = count_script_references(set(cells), records)
    path = os.path.join(out_dir, "wo1-cell-report.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cell_id", "is_interior", "contains_target_keyword",
                    "referenced_by_script_count"])
        for name, d in sorted(cells.items()):
            w.writerow([name, d["is_interior"], d["contains_target_keyword"],
                        counts.get(name, 0)])
    return path, cells, unnamed


def write_script_strings(records, out_dir):
    """Keyword hits on script lines that put text on screen.

    Script bodies are frozen by the rules, and the ESM carries compiled
    bytecode beside the text, so a text-only edit would not change what the
    player reads anyway. These lines are therefore residue: visible in game and
    out of reach of the transform. Counting them is the point.
    """
    rows = []
    for rec in records.values():
        if rec["type"] != "Script":
            continue
        text = rec.get("text", "") or ""
        if not text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(";"):
                continue
            if not SCRIPT_DISPLAY_RE.search(line):
                continue
            hits = [kw for kw, p in KEYWORD_RULES if p.search(line)]
            if hits:
                rows.append((rec.get("id", ""), ",".join(hits), line))
    path = os.path.join(out_dir, "wo1-script-strings.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["script_id", "keywords", "line"])
        for row in sorted(rows):
            w.writerow(row)
    return path, rows


def write_summary(out_dir, occ, cast, names, topics, cells, unnamed,
                  script_rows):
    lines = []
    add = lines.append
    add("# WO1 survey summary")
    add("")
    add("Generated by tools/scripts/wo1_survey.py. Numbers here are counts, not")
    add("decisions - the selection of what actually gets rewritten is Canon Part 7.")
    add("")

    kw_actors = {a: d for a, d in cast.items() if d["kw_infos"]}
    total_infos = sum(d["infos"] for d in cast.values())
    total_words = sum(d["words"] for d in cast.values())
    kw_infos = sum(d["kw_infos"] for d in cast.values())
    kw_words = sum(d["kw_words"] for d in cast.values())

    add("## Cast list - actor-ID filter")
    add("")
    add(f"- Actors with actor-filtered INFO records: **{len(cast)}**")
    add(f"- Actor-filtered INFO records: **{total_infos}**")
    add(f"- Words in them: **{total_words}**")
    add("")
    add("The narrower keyword-filtered selection the first pass reported, for")
    add("comparison:")
    add("")
    add(f"- Actors: {len(kw_actors)}, records: {kw_infos}, words: {kw_words}")
    add("")
    cohort_infos = sum(d["infos"] for d in kw_actors.values())
    cohort_words = sum(d["words"] for d in kw_actors.values())
    add("Between the two sits the figure to plan against: every actor-filtered")
    add("line belonging to an actor who says a keyword at least once. Rewriting")
    add("one line of an actor's lore means reading the rest of that actor for")
    add("consistency, so this is the reading load, and the keyword figure above")
    add("is the writing load.")
    add("")
    add(f"- Actors: **{len(kw_actors)}**, records: **{cohort_infos}**, "
        f"words: **{cohort_words}**")
    add("")
    ranked = sorted(cast.items(), key=lambda kv: -kv[1]["words"])
    add("Top 10 actors by words:")
    add("")
    add("| actor | INFOs | words | of which keyword |")
    add("| --- | --- | --- | --- |")
    for actor_id, d in ranked[:10]:
        label = names.get(actor_id) or actor_id
        add(f"| {label} | {d['infos']} | {d['words']} | {d['kw_words']} |")
    add("")
    cum = 0
    for n in (10, 30):
        cum = sum(d["words"] for _, d in ranked[:n])
        share = 100.0 * cum / total_words if total_words else 0
        add(f"- Top {n} actors hold {share:.0f}% of the words")
    add("")

    add("## Keyword hits")
    add("")
    add("| keyword | records | occurrences |")
    add("| --- | --- | --- |")
    for kw, _ in KEYWORD_RULES:
        recs = set()
        occurrences = 0
        for (k, _rt, _f), d in occ.items():
            if k == kw:
                recs |= d["recs"]
                occurrences += d["occ"]
        add(f"| {kw} | {len(recs)} | {occurrences} |")
    add("")

    add("Distinct records carrying at least one keyword, by record type and")
    add("route. This is the size of the job, and it is what the first pass's")
    add("occurrence_count column was mistaken for.")
    add("")
    by_type = {}
    for (kw, rtype, field), d in occ.items():
        by_type.setdefault((rtype, field), set()).update(d["recs"])
    add("| record type | field | records | route |")
    add("| --- | --- | --- | --- |")
    for (rtype, field), recs in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        add(f"| {rtype.upper()} | {field} | {len(recs)} | "
            f"{route_for(rtype, field)} |")
    add("")

    add("## Residue in script bodies")
    add("")
    add(f"- Script lines that display text and carry a keyword: "
        f"**{len(script_rows)}**, listed in wo1-script-strings.csv")
    add("")
    add("Script bodies are frozen by the rules, and the ESM stores compiled")
    add("bytecode beside the text, so editing the text would not change what")
    add("the player reads. These lines are visible in game and unreachable by")
    add("the transform. Mostly the Vivec shrine MessageBoxes.")
    add("")

    add("## Cells")
    add("")
    add(f"- Named cells: **{len(cells)}** "
        f"({sum(1 for d in cells.values() if d['is_interior'])} interior)")
    add(f"- Unnamed exterior cells, not listed: {unnamed}")
    kwcells = sorted(n for n, d in cells.items() if d["contains_target_keyword"])
    add(f"- Named cells carrying a keyword: **{len(kwcells)}** - frozen by policy")
    for n in kwcells:
        add(f"  - {n}")
    add("")

    add("## Topics")
    add("")
    add(f"- Topics: **{len(topics)}**")
    kwtopics = [t for t, d in topics.items() if d["contains_target_keyword"]]
    kwtopic_infos = sum(topics[t]["info_count"] for t in kwtopics)
    add(f"- Topics whose ID carries a keyword: **{len(kwtopics)}**, "
        f"holding {kwtopic_infos} INFO records - frozen by policy")
    add("")

    path = os.path.join(out_dir, "wo1-summary.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return path


def ensure_json(esm_dir, cache_dir, tes3conv):
    """Convert the masters to JSON if the dump is not already cached."""
    os.makedirs(cache_dir, exist_ok=True)
    out = []
    for master in ("Morrowind.esm", "Tribunal.esm", "Bloodmoon.esm"):
        src = os.path.join(esm_dir, master)
        dst = os.path.join(cache_dir, master.replace(".esm", ".json"))
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            out.append(dst)
            continue
        if not os.path.exists(src):
            raise SystemExit(f"master not found: {src}")
        if not os.path.exists(tes3conv):
            raise SystemExit(f"tes3conv not found: {tes3conv}")
        print(f"  converting {master} ...", flush=True)
        subprocess.run([tes3conv, src, dst, "--overwrite"], check=True)
        out.append(dst)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--esm-dir", default=os.path.join(root, "tools", "input"))
    ap.add_argument("--cache-dir", default=os.path.join(root, "tools", "cache"),
                    help="where the tes3conv JSON dumps live or get written")
    ap.add_argument("--json", nargs="*", default=None,
                    help="use these JSON dumps instead of converting")
    ap.add_argument("--out", default=os.path.join(root, "tools", "reports"))
    ap.add_argument("--tes3conv",
                    default=os.path.join(root, "tools", "bin", "tes3conv.exe"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    print("Resolving inputs ...", flush=True)
    json_files = args.json or ensure_json(args.esm_dir, args.cache_dir,
                                          args.tes3conv)

    print("Loading masters (last definition wins) ...", flush=True)
    records = load_masters(json_files)
    print(f"  {len(records)} surviving records of interest", flush=True)

    print("Counting keywords ...", flush=True)
    occ = survey_keywords(records)
    p_kw = write_keyword_report(occ, args.out)

    print("Building cast list ...", flush=True)
    cast, names = build_cast_list(records)
    p_cast = write_cast_list(cast, names, args.out)

    print("Inventorying topics ...", flush=True)
    p_top, topics = write_topic_inventory(records, args.out)

    print("Surveying cells ...", flush=True)
    p_cell, cells, unnamed = write_cell_report(records, args.out)

    print("Collecting script display strings ...", flush=True)
    p_scr, script_rows = write_script_strings(records, args.out)

    p_sum = write_summary(args.out, occ, cast, names, topics, cells, unnamed,
                          script_rows)

    print("\nWrote:")
    for p in (p_kw, p_cast, p_top, p_cell, p_scr, p_sum):
        print("  " + os.path.relpath(p, root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
