#!/usr/bin/env python3
"""Say whether a NIF found on the internet is any use to this game.

    python tools/scripts/nif_info.py <file or folder>

`.nif` is not one format. It is a family of generations sharing an extension:
Morrowind writes **4.0.0.2**, Oblivion 20.0.0.5, Skyrim 20.2.0.7. A helmet
downloaded for the wrong game looks identical in a file listing and will not
load. This reads the version out of the header and says so before anything is
installed.

It also answers the three things that decide whether a mesh is usable here at
all, none of which the file name tells you:

* **Does it carry texture coordinates?** Print and sculpt formats do not, and a
  mesh with no UVs has nowhere to put a texture - it renders as flat plastic.
* **How heavy is it?** Morrowind helmets run 89 to 177 vertices. A model meant
  for 3D printing runs into the hundreds of thousands.
* **Does OpenMW itself accept it?** `niftest.exe`, shipped with the game, is the
  authority. Its verdict is reported here rather than guessed at.
"""

import argparse
import os
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uvmap import parse_trishape  # noqa: E402

NIFTEST = r"D:/Program Files/OpenMW 0.51.0/niftest.exe"

# The generations that matter, by the version word in the header.
KNOWN = {
    0x04000002: ("Morrowind", "usable here, nothing to convert"),
    0x0303000D: ("Freedom Force era", "older than Morrowind, untested here"),
    0x14000005: ("Oblivion", "needs conversion - Blender with NifTools"),
    0x14020007: ("Skyrim", "needs conversion - Blender with NifTools"),
    0x14030009: ("Fallout 4 era", "needs conversion, and probably not worth it"),
}

# Vanilla helmets, for scale. Measured, not recalled.
BUDGET = "Morrowind helmets are 89 to 177 vertices, 61 to 273 triangles"


def read_version(blob):
    end = blob.find(b"\n")
    if end < 0 or end > 120:
        return None, None
    header = blob[:end].decode("ascii", "replace")
    try:
        version, = struct.unpack_from("<I", blob, end + 1)
    except struct.error:
        return header, None
    return header, version


def describe(path):
    with open(path, "rb") as f:
        blob = f.read()
    header, version = read_version(blob)
    print(f"\n{os.path.basename(path)}  ({len(blob):,} bytes)")
    if header is None:
        print("  not a NIF at all - no header line")
        return
    print(f"  header   {header.strip()}")
    if version is None:
        print("  version  unreadable")
    else:
        name, verdict = KNOWN.get(version, ("unrecognised", "unknown generation"))
        print(f"  version  {version:#010x}  {name} - {verdict}")

    try:
        verts, uv, tris = parse_trishape(blob)
        print(f"  geometry {len(verts)} vertices, {len(tris)} triangles")
        print(f"           {BUDGET}")
        span = (uv[:, 0].min(), uv[:, 0].max(), uv[:, 1].min(), uv[:, 1].max())
        print("  texture  UV coordinates present, U %.3f..%.3f  V %.3f..%.3f"
              % span)
    except Exception as exc:
        # Not fatal and not a verdict: a mesh can be perfectly good and still
        # not match the one shape layout this reader knows.
        print(f"  geometry could not be read by our parser: {exc}")

    if os.path.exists(NIFTEST):
        done = subprocess.run([NIFTEST, path], capture_output=True, text=True)
        ok = done.returncode == 0
        print(f"  OpenMW   {'ACCEPTS it' if ok else 'REJECTS it'}"
              f" (niftest exit {done.returncode})")
        if not ok:
            for line in (done.stdout + done.stderr).splitlines()[:4]:
                print(f"           {line}")
    else:
        print("  OpenMW   niftest.exe not found, cannot ask the engine")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", help="a .nif file, or a folder to walk")
    args = ap.parse_args()
    if os.path.isdir(args.path):
        found = 0
        for root, _dirs, files in os.walk(args.path):
            for name in sorted(files):
                if name.lower().endswith(".nif"):
                    describe(os.path.join(root, name))
                    found += 1
        if not found:
            print(f"no .nif files under {args.path}")
    else:
        describe(args.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
