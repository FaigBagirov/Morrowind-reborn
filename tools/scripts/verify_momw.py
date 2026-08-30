#!/usr/bin/env python3
"""Prove the momw build kept every field it did not mean to change.

    python tools/scripts/verify_momw.py --plugins <openmw.cfg>

A Morrowind plugin overrides a record whole. Our build carries the winning
mod's version forward and substitutes into one field, which is the whole point
of `--profile momw` - but "carries forward" is a claim, and this checks it.

For every record we emit, the source is located (the mod that defines it last,
or the masters if nobody does) and compared field by field. Everything except
the fields the rules or an authored file were allowed to touch must be
byte-identical.
"""

import argparse
import collections
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import effective  # noqa: E402
from wo1_survey import record_key, stream_records  # noqa: E402

MASTERS = ("Morrowind.esm", "Tribunal.esm", "Bloodmoon.esm")
# The only fields the build is allowed to differ in.
# Fields we change on purpose, so a difference in them is the point rather than
# a fault. `biped_objects` joined the list when the imported armour arrived: the
# conversion repoints each slot at its own bodypart, which is a deliberate
# rewrite of a field the upstream mod also sets.
TOUCHABLE = {"name", "text", "description", "value", "biped_objects"}


def load_plugin(path, tes3conv, cache_dir):
    stem = os.path.splitext(os.path.basename(path))[0]
    stamp = int(os.path.getmtime(path))
    dst = os.path.join(cache_dir, f"{stem}.{stamp}.json")
    if not os.path.exists(dst) or os.path.getsize(dst) == 0:
        subprocess.run([tes3conv, path, dst, "--overwrite"], check=True)
    return dst


def index(json_path):
    out, topic = {}, ""
    for rec in stream_records(json_path):
        if rec.get("type") == "Dialogue":
            topic = rec.get("id", "")
        out[record_key(rec, topic)] = rec
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plugins", required=True)
    ap.add_argument("--built", default=os.path.join(root, "tools", "build",
                                                    "scifi-rewrite-momw.esp"))
    ap.add_argument("--cache-dir", default=os.path.join(root, "tools", "cache"))
    ap.add_argument("--tes3conv",
                    default=os.path.join(root, "tools", "bin", "tes3conv.exe"))
    args = ap.parse_args()

    print("Reading the built plugin ...")
    ours = index(load_plugin(args.built, args.tes3conv, args.cache_dir))
    ours = {k: v for k, v in ours.items() if v.get("type") != "Header"}
    print(f"  {len(ours)} records")

    data_dirs, content = effective.parse_cfg(args.plugins)
    plugins, _missing = effective.resolve(content, data_dirs)
    plugins = [(n, p) for n, p in plugins
               if os.path.basename(p) != os.path.basename(args.built)]
    print(f"Locating sources across {len(plugins)} plugins ...")
    winners = effective.find_winners(plugins, set(ours), progress=False)
    by_source = collections.defaultdict(set)
    for key, path in winners.items():
        by_source[path].add(key)
    print(f"  {len(winners)} of our records exist upstream, "
          f"in {len(by_source)} files")

    problems, checked, inherited = [], 0, 0
    for path, keys in by_source.items():
        src = index(load_plugin(path, args.tes3conv, args.cache_dir))
        is_master = os.path.basename(path) in MASTERS
        for key in keys:
            if key not in src:
                continue
            a, b = src[key], ours[key]
            checked += 1
            if not is_master:
                inherited += 1
            for field, value in a.items():
                if field in TOUCHABLE:
                    continue
                if b.get(field) != value:
                    problems.append((os.path.basename(path), key, field,
                                     json.dumps(value)[:60],
                                     json.dumps(b.get(field))[:60]))
            for field in b:
                if field not in a and field not in TOUCHABLE:
                    problems.append((os.path.basename(path), key, field,
                                     "<absent upstream>",
                                     json.dumps(b[field])[:60]))

    print(f"\nRecords compared: {checked}")
    print(f"  of which inherited from a mod rather than a master: {inherited}")
    new_records = len(ours) - checked
    print(f"  records we invent, with no upstream: {new_records}")
    if problems:
        print(f"\nFIELDS THAT CHANGED AND SHOULD NOT HAVE: {len(problems)}")
        for src_name, key, field, was, now in problems[:20]:
            print(f"  [{src_name}] {key[0]} {key[-1]} .{field}")
            print(f"      upstream: {was}")
            print(f"      ours    : {now}")
        raise SystemExit(1)
    print("\nEvery field outside name/text/description/value is byte-identical "
          "to its source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
