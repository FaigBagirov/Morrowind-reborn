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

3. **Cut into each bone's own frame.** The same step multiplies every vertex by
   its anchor joint's inverse bind matrix. A Morrowind bodypart is authored in
   the frame of the bone it hangs on, not in world space, so a piece left in the
   model's A-pose arrives diagonal, and no amount of moving or scaling can put
   it right. This is the step whose absence scattered the first suit.

4. **One piece per slot, not two.** The engine mirrors a bodypart for the
   opposite side: `a_daedric_boots_f` serves both feet, `a_daedric_pauldron_cl`
   both shoulders. Checked in the records, not assumed.

5. **Fit against the vanilla naked body, not against armour.** `nif_write.py`
   aligns each piece to the vanilla bodypart of the same slot - the same
   anatomy, in the frame the game expects - which gives rotation, size and
   position at once, and keeps the pieces in proportion with each other because
   every one of those parts came off a single body. The two rules tried before
   this are in the traps below, with what they measured.

6. **Build on a donor.** `nif_write.py` replaces one shape inside an existing
   NIF, which supplies the node, the material and the texture reference. Where
   the vanilla part is single-shape it is the donor as well, so the frame a
   piece is fitted to and the frame it is written into are the same by
   construction.

7. **Repoint the texture.** Without `--texture` the new mesh wears the donor's
   own, since that filename is baked into the donor's NiSourceTexture block.

8. **Recolour through the ordinary converter**, so the import belongs to the
   same suit as everything else rather than looking like a guest.

9. **Give it to the game.** A mesh in a data directory is invisible: Morrowind
   reaches a worn piece through two hops, an armour record naming a bodypart
   and the bodypart naming the mesh. `bodyparts.py` emits one bodypart per
   built piece and repoints the armour records at them, and `transform.py`
   calls it. Only the shape changes - name, class, weight, armour rating and
   enchantment stay as the load order left them.

       python tools/scripts/transform.py --profile momw
           --plugins <play openmw.cfg> --out-name scifi-rewrite-momw --write
       tools/bin/tes3conv.exe tools/build/scifi-rewrite-momw.json
           tools/build/scifi-rewrite-momw.esp --overwrite

## The traps, each of which cost a round

* **Frames, and this is the big one.** Morrowind's bone frames follow no single
  convention. Measured on the vanilla body: the upper arm, forearm and thigh run
  along local X, the knee and calf along Z, the foot along Y, and the chest has
  up along Z with left-right along X. This rig runs every bone along its own X -
  measured, not assumed, by transforming each bone's child into its parent's
  frame. So most slots need no turn at all and the calf needs a quarter of one.
* **Fitting to an armour donor's bounding box does not work.** The donor boxes
  do not correspond to the body - the one single-shape chest donor the game
  offers is 62 units deep because of its skirt - so every piece took its own
  unrelated scale and the suit came apart on screen.
* **Neither does aligning principal axes and choosing the flip by overlap.** The
  four candidates scored within 0.002 to 0.009 of each other on values of 0.06
  to 0.18, so the choice was noise; widening the search to all 24 axis-aligned
  rotations did not help and contradicted the extents outright. Armour and a
  naked limb do not overlap well enough to measure anything that way. **The
  extents do work**, and they are what is used.
* **Rank the axes only where the ranking means something.** A hip is nearly
  cubic and its three lengths sit within a fifth of each other, so ranking them
  measures noise. Below a clear lead the axes are left alone; where that is not
  good enough - the chest - the turn is read off the rig and passed in with
  `--axes`.
* **Bone-local units are not world units.** This rig bakes roughly a tenth into
  its bind matrices. Never carry a scale across that boundary.
* **Axes.** Morrowind bodyparts are Y-up with +Z forward, the same as glTF, so
  a *world-space* piece needs no swap. Swapping is a ninety-degree roll about
  the ear-to-ear axis and looks like a helmet nodding at the floor.
* **Donors are not interchangeable.** Each must be a bodypart of the same slot
  and must have exactly one shape, since this writer replaces one. Every slot
  has such a donor except Hand: twelve hand meshes parse and not one of them is
  single-shape.
* **Only one side needs building.** The engine mirrors a bodypart for the
  opposite side, and the mods leave the left slots empty for exactly that
  reason. Filling them is work for nothing.
* **The build must not scan its own output.** Once the plugin is installed it
  sits last in the load order and wins every record it defines - already
  converted - so the next build reads `Zenar` back as the effective text,
  matches no rule, and silently emits a plugin with the renames missing. It
  happened once: 347 records became 21, and nothing warned because every step
  succeeded. `transform.py` now excludes anything under its own build
  directory. **If a rebuild ever comes out suspiciously small, check this
  first**, and compare against `--profile vanilla`, which cannot be affected.
* **Node transforms are not read.** Vertices are compared raw, so a donor whose
  NiNode carries a rotation would be fitted against a frame that is not quite
  its own. It has not bitten yet, and it is not checked for.
* **Licence.** A downloaded model usually carries one. See `CREDITS.md`.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

# Per slot: the donor that supplies the NIF around the geometry, and the
# reference that says how the piece should sit inside it.
#
# **The reference is the vanilla naked bodypart wherever one exists**, because
# it is the same anatomy in the frame the game expects, and because every part
# of that body came off one body - which is what holds the pieces in proportion
# with each other. Where it is single-shape it doubles as the donor.
#
# Two slots have no vanilla twin. Morrowind draws a naked torso from the
# skeleton itself: its Chest bodypart is `b_n_..._skins.nif`, a decal seven
# units across, and a naked body has no clavicle at all. Those two fall back to
# an armour donor, and to the median scale of the slots that were measured.
BODY = "meshes/b/b_n_dark elf_m_%s.nif"
SLOTS = {
    # slot: (donor, reference or None to reuse the donor, forced axes or None)
    "chest": ("meshes/a/a_adamantium_cuirass_c.nif", None, "-z,y,x"),
    "groin": (BODY % "groin", None, None),
    "clavicle": ("meshes/a/a_daedric_pauldron_cl.nif", None, None),
    "upperarm": (BODY % "upper arm", None, None),
    "forearm": (BODY % "forearm", None, None),
    "upperleg": (BODY % "upper leg", None, None),
    "knee": (BODY % "knee", None, None),
    "ankle": (BODY % "ankle", None, None),
    # the naked foot carries two shapes and this writer replaces one, so the
    # boot supplies the container while the foot still supplies the fitting
    "foot": ("meshes/a/a_daedric_boots_f.nif", BODY % "foot", None),
}
MEASURED = {s for s, (d, _r, _a) in SLOTS.items() if d.startswith("meshes/b/")}

# The chest turn is read off the rig, not guessed. In the chest bone's frame the
# clavicles sit at plus and minus Z and the neck at plus X, so up is X and
# left-right is Z. On Morrowind's side the cuirass is mirror-symmetric about X,
# scoring 0.86, and its cross-section runs wide, narrow, wide along Z -
# shoulders, waist, skirt hem - so there up is Z and left-right is X. The two
# frames are a quarter turn apart. The sign sends the shoulder end to the deeper
# end of the donor, 23.5 units against 16.9, a chest being deeper than a hem.

# which cut piece feeds each slot; a left-side cut serves both sides
SOURCE = {"chest": "chest", "groin": "groin", "clavicle": "clavicle_l",
          "upperarm": "upperarm_l", "forearm": "forearm_l",
          "upperleg": "upperleg_l", "knee": "knee_l", "ankle": "ankle_l",
          "foot": "foot_l"}

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
    ap.add_argument("--clearance", type=float, default=1.08,
                    help="how much bigger than the naked body, so armour sits "
                         "over it rather than inside it")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    parts = os.path.join(args.scratch, "parts")
    os.makedirs(parts, exist_ok=True)
    print("cutting by bone, into each bone's own frame ...")
    done = run([os.path.join(HERE, "glb_bodyparts.py"), args.model,
                "--out", parts])
    print(done.stdout.rstrip() or done.stderr.rstrip())
    if done.returncode:
        return 1

    mesh_dir = os.path.join(args.out, "Meshes", "zenar")
    if args.write:
        os.makedirs(mesh_dir, exist_ok=True)
    scales, rows = {}, []

    def make(slot, fallback=None):
        donor, ref, turn = SLOTS[slot]
        source = os.path.join(parts, SOURCE[slot] + ".obj")
        if not os.path.exists(source):
            rows.append("%-11s%-28s  no cut piece" % (slot, ""))
            return None
        target = os.path.join(mesh_dir, slot + ".nif")
        call = [os.path.join(HERE, "nif_write.py"), source, "--donor", donor,
                "--reference", ref or donor, "--out", target,
                "--texture", args.texture, "--clearance", str(args.clearance)]
        if turn:
            call += ["--axes=" + turn]
        if fallback:
            call += ["--fixed-scale", str(fallback)]
        if not args.write:
            rows.append("%-11s%-28s  dry run"
                        % (slot, os.path.basename(ref or donor)))
            return None
        made = run(call)
        if made.returncode:
            last = (made.stderr.strip().splitlines() or ["failed"])[-1]
            rows.append("%-11s%-28s  %s"
                        % (slot, os.path.basename(ref or donor), last[:40]))
            return None
        said = [x for x in made.stdout.splitlines() if x.startswith("aligned")]
        scale = float(said[0].split("scale ")[1].split(",")[0]) if said else 0.0
        ok = (os.path.exists(NIFTEST)
              and subprocess.run([NIFTEST, target],
                                 capture_output=True).returncode == 0)
        rows.append("%-11s%-28s%7.1f%9d  %s"
                    % (slot, os.path.basename(ref or donor), scale,
                       os.path.getsize(target),
                       "accepts" if ok else "REJECTS"))
        return scale if ok else None

    # The slots with a vanilla twin go first: their scales are anatomy, measured
    # limb against limb. The two without one then borrow the median, which is
    # what keeps a torso in proportion with the arms hanging off it.
    for slot in SLOTS:
        if slot in MEASURED:
            got = make(slot)
            if got:
                scales[slot] = got
    median = sorted(scales.values())[len(scales) // 2] if scales else 1.0
    for slot in SLOTS:
        if slot not in MEASURED:
            make(slot, fallback=median)

    print("\n%-11s%-28s%7s%9s  ENGINE"
          % ("SLOT", "REFERENCE", "SCALE", "BYTES"))
    for line in rows:
        print(line)
    built = sum(1 for r in rows if r.endswith("accepts"))
    if scales:
        print("\nscale off the vanilla body: %.1f to %.1f, median %.1f - and "
              "the median is what the chest and clavicle use."
              % (min(scales.values()), max(scales.values()), median))
    print("\n%d of %d pieces built and accepted." % (built, len(SLOTS)))
    print("Hand is not in the list: no hand bodypart has a single shape.")
    if not args.write:
        print("Dry run. Pass --write to build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
