#!/usr/bin/env python3
"""Prove the shipped Lua engine and the Python engine agree, byte for byte.

    python tools/scripts/equivalence_test.py

The project has two implementations of the same rules. Python's produces every
report, every preview and every review; Lua's is what the player actually gets
at load time. Boundaries, case shapes and markup spans are exactly the kind of
thing that drifts between two languages, and a drift means the reports describe
a mod that does not exist.

This builds a fixture from the Python engine over every Lua-half field in the
masters, then runs the fixture through `mod/scripts/rewrite/apply.lua` under
OpenMW's own `lua51.dll` - the same LuaJIT the game uses, not a lookalike.
"""

import argparse
import ctypes
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wo1_survey import (  # noqa: E402
    DISPLAY_FIELDS, FROZEN, field_values, load_masters,
)
from momw_compat import TYPE_CODE  # noqa: E402
from check_rules import apply_rules, load_rules  # noqa: E402
from transform import LUA_STORE  # noqa: E402

MASTERS = ("Morrowind.json", "Tribunal.json", "Bloodmoon.json")
LUA_DLL = r"D:\Program Files\OpenMW 0.51.0\lua51.dll"


def build_fixture(cache_dir, rules_path):
    rules = load_rules(rules_path)
    paths = [os.path.join(cache_dir, n) for n in MASTERS]
    records = load_masters(paths)
    cases = []
    for rec in records.values():
        rtype = rec["type"]
        specs = DISPLAY_FIELDS.get(rtype)
        if not specs:
            continue
        code = TYPE_CODE.get(rtype)
        if code not in LUA_STORE:
            continue
        rid = str(rec.get("id") or rec.get("effect_id")
                  or rec.get("skill_id") or rec.get("name") or "")
        for spec in specs:
            if (rtype, spec) in FROZEN:
                continue
            field = spec.split(".")[0] if "." in spec else spec
            for value in field_values(rec, spec):
                new, applied, _notes, _prot = apply_rules(
                    value, rules, code, field, rid)
                if applied:
                    cases.append({"code": code, "id": rid, "field": field,
                                  "before": value, "after": new})
    return cases


def run_lua(dll_path, script, prelude):
    d = ctypes.CDLL(dll_path)
    d.luaL_newstate.restype = ctypes.c_void_p
    d.luaL_openlibs.argtypes = [ctypes.c_void_p]
    d.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    d.luaL_loadfile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    d.lua_pcall.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 3
    d.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    d.lua_tolstring.restype = ctypes.c_char_p
    L = ctypes.c_void_p(d.luaL_newstate())
    d.luaL_openlibs(L)
    for label, loader, arg in (("prelude", d.luaL_loadstring, prelude.encode()),
                               ("script", d.luaL_loadfile, script.encode())):
        if loader(L, arg) != 0:
            raise SystemExit(f"{label} load error: "
                             f"{d.lua_tolstring(L, -1, None).decode()}")
        if d.lua_pcall(L, 0, 0, 0) != 0:
            msg = d.lua_tolstring(L, -1, None)
            raise SystemExit(f"{label} runtime error: "
                             f"{msg.decode() if msg else '<none>'}")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache-dir", default=os.path.join(root, "tools", "cache"))
    ap.add_argument("--rules", default=os.path.join(root, "tools", "rules",
                                                    "naming.csv"))
    ap.add_argument("--lua-dll", default=LUA_DLL)
    ap.add_argument("--scratch", default=os.path.join(root, "tools", "build"))
    args = ap.parse_args()

    print("Building the fixture from the Python engine ...")
    cases = build_fixture(args.cache_dir, args.rules)
    print(f"  {len(cases)} fields, "
          f"{sum(len(c['before']) for c in cases)} characters")

    os.makedirs(args.scratch, exist_ok=True)
    fixture = os.path.join(args.scratch, "equivalence-fixture.json")
    with open(fixture, "w", encoding="utf-8") as f:
        # Compact separators on purpose: the Lua side reads this with a
        # deliberately small parser that looks for `"field":"`, and the default
        # `": "` would not match it.
        #
        # ensure_ascii=False matters more than it looks. With backslash-u
        # escapes the curly quotes in book text reach Lua as literal text
        # ending in a letter, so the left word boundary on "Daedra" failed and
        # two books came back unchanged. OpenMW hands Lua UTF-8 bytes, and the
        # fixture has to do the same or it tests something the game never does.
        json.dump(cases, f, ensure_ascii=False, separators=(",", ":"))

    apply_lua = os.path.join(root, "mod", "scripts", "rewrite", "apply.lua")
    rules_lua = os.path.join(root, "mod", "scripts", "rewrite", "rules.lua")
    for p in (apply_lua, rules_lua):
        if not os.path.exists(p):
            raise SystemExit(f"missing {p} - run transform.py --write first")

    def lua_path(p):
        return p.replace("\\", "\\\\")

    prelude = (
        f'FIXTURE_PATH = "{lua_path(fixture)}"\n'
        f'RULES_PATH = "{lua_path(rules_lua)}"\n'
        f'APPLY_PATH = "{lua_path(apply_lua)}"\n'
    )
    print("Running the shipped Lua engine under OpenMW's lua51.dll ...")
    run_lua(args.lua_dll, os.path.join(here, "equivalence_test.lua"), prelude)
    return 0


if __name__ == "__main__":
    sys.exit(main())
