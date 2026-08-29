#!/usr/bin/env python3
"""The effective record set: the masters as the player's load order leaves them.

Used by `transform.py --profile momw`. The reason it exists is measured, not
theoretical: generating the plugin from the bare masters would silently revert
Patch for Purists in 13 dialogue records, because a Morrowind plugin overrides a
record whole and the later plugin wins. See `tools/reports/momw-compat.md`.

Two passes, because 262 plugins are 405 MB and converting all of them through
`tes3conv` is not practical:

  1. **Binary scan, all plugins in load order.** For each record we intend to
     touch, note which plugin defines it last. That plugin, and no other, holds
     the text the player actually reads.
  2. **Convert only the winners.** Usually a handful of files. Their JSON is
     cached beside the masters' and reused.

The reader is the one from `momw_compat.py`, validated against `tes3conv` on
Morrowind.esm.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from momw_compat import walk_plugin  # noqa: E402
from wo1_survey import record_key, stream_records  # noqa: E402


def parse_cfg(path):
    """Return (data directories, content files in load order)."""
    data, content = [], []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("data="):
                value = line[5:].strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                data.append(value)
            elif line.startswith("content="):
                content.append(line[8:].strip())
    return data, content


def resolve(content, data_dirs):
    """Content file names to paths, in load order. Lua-only entries are skipped."""
    out, missing = [], []
    for name in content:
        if name.lower().endswith(".omwscripts"):
            continue
        hit = None
        for d in data_dirs:
            candidate = os.path.join(d, name)
            if os.path.exists(candidate):
                hit = candidate
                break
        if hit:
            out.append((name, hit))
        else:
            missing.append(name)
    return out, missing


def find_winners(plugins, wanted, masters_last=None, progress=True):
    """Which plugin defines each wanted record last.

    `wanted` is a set of record keys as `wo1_survey.record_key` builds them.
    Records nobody overrides keep whatever `masters_last` says, which is the
    masters themselves.
    """
    winners = dict(masters_last or {})
    codes = {key[0] for key in wanted}
    code_of = {"Book": "BOOK", "DialogueInfo": "INFO", "Weapon": "WEAP",
               "Armor": "ARMO", "Creature": "CREA", "Clothing": "CLOT",
               "Class": "CLAS", "Skill": "SKIL", "Spell": "SPEL",
               "MiscItem": "MISC", "Ingredient": "INGR",
               "GameSetting": "GMST", "MagicEffect": "MGEF"}
    want_codes = {code_of[c] for c in codes if c in code_of}

    for i, (name, path) in enumerate(plugins, 1):
        if progress and (i % 40 == 0 or i == len(plugins)):
            print(f"    {i}/{len(plugins)} plugins scanned", flush=True)
        topic = ""
        try:
            for code, rid, rec_topic in walk_plugin(path, want_codes):
                if code == "DIAL":
                    topic = rid or ""
                    continue
                if rid is None:
                    continue
                key = _key_from_binary(code, rid, rec_topic or topic)
                if key in wanted:
                    winners[key] = path
        except (OSError, ValueError):
            print(f"    ! unreadable, skipped: {name}", flush=True)
    return winners


def _key_from_binary(code, rid, topic):
    """Mirror record_key for the four-character codes the binary reader gives."""
    type_of = {"BOOK": "Book", "INFO": "DialogueInfo", "WEAP": "Weapon",
               "ARMO": "Armor", "CREA": "Creature", "CLOT": "Clothing",
               "CLAS": "Class", "SKIL": "Skill", "SPEL": "Spell",
               "MISC": "MiscItem", "INGR": "Ingredient",
               "GMST": "GameSetting", "MGEF": "MagicEffect"}
    rtype = type_of.get(code)
    if rtype is None:
        return None
    if rtype == "DialogueInfo":
        return (rtype, str(topic or "").lower(), rid.lower())
    return (rtype, rid.lower())


def convert(paths, cache_dir, tes3conv):
    """tes3conv the plugins that won something. Cached by name and mtime."""
    os.makedirs(cache_dir, exist_ok=True)
    out = {}
    for path in sorted(set(paths)):
        stem = os.path.splitext(os.path.basename(path))[0]
        stamp = int(os.path.getmtime(path))
        dst = os.path.join(cache_dir, f"{stem}.{stamp}.json")
        if not os.path.exists(dst) or os.path.getsize(dst) == 0:
            print(f"    converting {os.path.basename(path)} ...", flush=True)
            subprocess.run([tes3conv, path, dst, "--overwrite"], check=True)
        out[path] = dst
    return out


def read_records(json_path, wanted):
    """Full records from one converted plugin, keyed as the survey keys them."""
    out = {}
    topic = ""
    for rec in stream_records(json_path):
        if rec.get("type") == "Dialogue":
            topic = rec.get("id", "")
        key = record_key(rec, topic)
        if key in wanted:
            out[key] = rec
    return out
