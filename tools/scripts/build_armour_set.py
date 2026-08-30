#!/usr/bin/env python3
"""Turn a downloaded suit of armour into Morrowind bodyparts, in one command.

    python tools/scripts/build_armour_set.py model.glb --write

This is the whole pipeline, and it exists because the alternative is a list of
commands in a report that nobody re-runs correctly. `tools/build/` is
gitignored, so anything not written down here is lost the moment the shell
history is.

## The route, and why each step is where it is

1. **Extract.** `glb.py` reads the container - glTF is a JSON header plus a
   binary blob, no library needed. GLB is the format to ask a site for: one
   file carrying geometry, texture coordinates and images together.

2. **Cut by bone, never by plane.** `glb_bodyparts.py` takes each vertex's
   strongest joint and looks up which Morrowind slot that bone belongs to.
   Morrowind does not skin a body, it dresses one from separate rigid pieces,
   so the suit must come apart - and the rig already knows where the elbow is.
   A plane leaves open holes and puts the seam where the arithmetic falls.

3. **One piece per slot, not two.** The engine mirrors a bodypart for the
   opposite side: `a_daedric_boots_f` serves both feet, `a_daedric_pauldron_cl`
   both shoulders. Checked in the records, not assumed.

4. **Build on a donor.** `nif_write.py` replaces one shape inside an existing
   NIF, which supplies the node, the material and the texture reference. The
   donor must be a bodypart **of the same slot**, because its node transform is
   what positions the piece on the bone.

5. **Repoint the texture.** Without `--texture` the new mesh wears the donor's
   own, since that filename is baked into the donor's NiSourceTexture block.

6. **Recolour through the ordinary converter**, so the import belongs to the
   same suit as everything else rather than looking like a guest.

## The traps, each of which cost a round

* **Axes.** Morrowind bodyparts are Y-up with +Z forward, the same as glTF, so
  **no swap**. Swapping is a ninety-degree roll about the ear-to-ear axis and
  looks like a helmet nodding at the floor.
* **Scale.** A bounding-box fit is conservative when a mesh carries spikes. The
  helmet needed 1.55.
* **Height.** A box fit can centre a piece and still hang it too low, because
  the bodypart's origin is its attachment point. `--lift` moves it along the
  bone.
* **Donors are not interchangeable.** Each must be a bodypart of the same slot
  and must have exactly one shape, since this writer replaces one. Every slot
  has such a donor except Hand: twelve hand meshes parse and not one of them is
  single-shape. The list below is what works, found by trying rather than
  assumed.
* **Licence.** A downloaded model usually carries one. See `CREDITS.md`.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

# slot -> donor bodypart of that slot, chosen because it parses. Hand is absent
# on purpose: twelve hand meshes parse but not one of them has a single shape,
# and this writer replaces one. That is an open problem, not an oversight.
DONORS = {
    "chest": "meshes/a/a_adamantium_cuirass_c.nif",
    "groin": "meshes/a/a_daedric_greaves_g.nif",
    "clavicle": "meshes/a/a_daedric_pauldron_cl.nif",
    "upperarm": "meshes/a/a_ebony_pauldron_ua.nif",
    "forearm": "meshes/a/a_ebony_pauldron_fa.nif",
    "upperleg": "meshes/a/a_ebony_greaves_ul.nif",
    "knee": "meshes/a/a_ebony_greaves_k.nif",
    "ankle": "meshes/a/a_daedric_boots_a.nif",
    "foot": "meshes/a/a_daedric_boots_f.nif",
}
# which cut piece feeds each slot; a left-side cut serves both sides
SOURCE = {"chest": "chest", "groin": "groin", "clavicle": "clavicle_l", "upperarm": "upperarm_l",
          "forearm": "forearm_l", "upperleg": "upperleg_l", "knee": "knee_l",
          "ankle": "ankle_l", "foot": "foot_l"}

NIFTEST = r"D:/Program Files/OpenMW 0.51.0/niftest.exe"


def run(args, **kw):
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model", help="the .glb to import")
    ap.add_argument("--out", default=os.path.join(ROOT, "tools", "build",
                                                  "armour-momw"))
    ap.add_argument("--scratch", default=os.path.join(ROOT, "tools", "build",
                                                      "import"))
    ap.add_argument("--texture", default="zenar_body.dds")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    parts = os.path.join(args.scratch, "parts")
    os.makedirs(parts, exist_ok=True)
    print("cutting by bone ...")
    done = run([os.path.join(HERE, "glb_bodyparts.py"), args.model,
                "--out", parts])
    print(done.stdout.rstrip() or done.stderr.rstrip())
    if done.returncode:
        return 1

    mesh_dir = os.path.join(args.out, "Meshes", "zenar")
    if args.write:
        os.makedirs(mesh_dir, exist_ok=True)

    print(f"\n{'SLOT':<11}{'DONOR':<30}{'BYTES':>8}  ENGINE")
    built = 0
    for slot, donor in DONORS.items():
        source = os.path.join(parts, SOURCE[slot] + ".obj")
        if not os.path.exists(source):
            print(f"{slot:<11}{'-- no cut piece --':<30}")
            continue
        target = os.path.join(mesh_dir, slot + ".nif")
        if not args.write:
            print(f"{slot:<11}{os.path.basename(donor):<30}   (dry run)")
            continue
        made = run([os.path.join(HERE, "nif_write.py"), source,
                    "--donor", donor, "--out", target,
                    "--texture", args.texture])
        if made.returncode:
            last = (made.stderr.strip().splitlines() or ["failed"])[-1]
            print(f"{slot:<11}{os.path.basename(donor):<30}  {last[:44]}")
            continue
        ok = (os.path.exists(NIFTEST)
              and subprocess.run([NIFTEST, target],
                                 capture_output=True).returncode == 0)
        print(f"{slot:<11}{os.path.basename(donor):<30}"
              f"{os.path.getsize(target):>8}  "
              f"{'accepts' if ok else 'REJECTS'}")
        built += ok

    print(f"\n{built} of {len(DONORS)} pieces built and accepted.")
    print("Hand is not in the list: no hand bodypart has a single shape.")
    if not args.write:
        print("Dry run. Pass --write to build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
