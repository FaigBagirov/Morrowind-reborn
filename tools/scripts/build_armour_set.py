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

# From the model's axes into the game's, measured both ways rather than assumed.
# Morrowind's toes reach 9.7 units past the ankle node along +Y and 7.2 the
# other way, so the game faces +Y; the model's foot runs +Z from its ankle, and
# glTF is Y-up, so the model faces +Z with up along +Y. And the sides are
# opposite: the game's left hand sits at x -16.7 to -12.1 while the model's is
# at +4.26, so the model's left is the game's -X.
#
# The chest was on backwards and mirrored until this was measured - it had
# x,z,-y, which points the breastplate at the character's own spine.
MODEL_TO_GAME = "-x,z,y"
SLOTS = {
    # slot: (donor, reference or None to reuse the donor, forced axes, trim)
    # Fitted in world space against the naked torso, hung on the Chest node -
    # see BONE below. The donor is only a container now; its skirt no longer
    # decides anything.
    # **The donor must not be skinned.** Every cuirass in the game is, and
    # putting our geometry into one leaves its bone weights describing the 1302
    # vertices we replaced: the engine then drives our 1978 by weights that mean
    # nothing, and the whole torso collapses into a thin blade reaching to the
    # floor. That is what Faig was seeing as a cloak down the middle and two
    # cones meeting at the knee. A rigid single-shape file serves instead - the
    # bone decides placement, the donor only carries node, material and texture,
    # exactly as for the hand.
    "chest": (BODY % "ankle", "meshes/b/b_n_dark elf_m_skins.nif",
              MODEL_TO_GAME, None),
    "groin": (BODY % "groin", None, MODEL_TO_GAME, None),
    "clavicle": ("meshes/a/a_daedric_pauldron_cl.nif", None, MODEL_TO_GAME, None),
    "upperarm": (BODY % "upper arm", None, MODEL_TO_GAME, None),
    "forearm": (BODY % "forearm", None, MODEL_TO_GAME, None),
    "upperleg": (BODY % "upper leg", None, MODEL_TO_GAME, None),
    "knee": (BODY % "knee", None, MODEL_TO_GAME, None),
    "ankle": (BODY % "ankle", None, MODEL_TO_GAME, None),
    # the naked foot carries two shapes and this writer replaces one, so the
    # boot supplies the container while the foot still supplies the fitting
    "foot": ("meshes/a/a_daedric_boots_f.nif", BODY % "foot", MODEL_TO_GAME, None),
    # The hand had no donor for a long time and the reason was a
    # misunderstanding: **the donor does not have to be a hand.** It supplies
    # the node, the material and the texture reference; where the piece goes is
    # decided by the bone. So any single-shape file whose own shape transform is
    # identity will do, and the vanilla ankle is one. The reference is the real
    # hand, three shapes of it, out of the file that also holds the torso.
    "hand": (BODY % "ankle", BODY % "skins", MODEL_TO_GAME, None),
}
MEASURED = {s for s, (d, *_) in SLOTS.items() if d.startswith("meshes/b/")}

# Slots fitted in world space instead: the skeleton node they hang on, and
# which shapes of the reference file to use. **This is the better way round**
# and the limbs would be no worse for it - up means up on both sides, so no
# axis has to be ranked or forced. It is used where the old way could not
# reach: the only chest donor in the game wears a skirt, and the naked torso
# turned out to be hiding in the hands file.
# **Every slot, not just the two that could not be done otherwise.** Ranking a
# piece's axes by length settles which one runs along the limb and nothing more:
# the roll about that axis is undetermined whenever the other two are close, and
# on the foot they are 6.3 against 6.2. Faig saw the foot a quarter turn out.
# In world space up is up and forward is forward for both sides at once, so
# there is nothing left to rank.
IN_WORLD = {
    "chest": ("Chest", "Tri Chest"),
    "groin": ("Groin", None),
    "clavicle": ("Left Clavicle", None),
    "upperarm": ("Left Upper Arm", None),
    "forearm": ("Left Forearm", None),
    "upperleg": ("Left Upper Leg", None),
    "knee": ("Left Knee", None),
    "ankle": ("Left Ankle", None),
    "foot": ("Left Foot", None),
    "hand": ("Left Hand", "Left Hand"),
}

# **The chest is not like the others, and the reason is structural.** Every
# cuirass in the three masters is a *skinned* mesh: it carries the whole Bip01
# skeleton and its vertices sit in the character's space, not in the chest
# bone's. There is no rigid single-shape chest anywhere to use instead - the
# search returns zero. So the chest is cut in world space rather than into a
# bone frame, and turned from the model's convention into the character's:
# model Y is up and becomes Z, model Z is forward and becomes -Y.
#
# Which end of the donor is the top was measured, not reasoned. Bip01 sits at
# Z 76.06 and `Tri Chest` runs from -41.4 to +20.9 about it, which puts the
# shoulders at +20.9 and the skirt hem at -41.4, down by the knees. An earlier
# guess here - that the shoulders were the deeper end, 23.5 units against 16.9 -
# was wrong, and the trim now keeps the upper half.
#
# One thing this does not fix: the donor is skinned, and its bone weights still
# describe the geometry we replaced. The engine accepts the file and draws it,
# but that mismatch is unexamined.

# which cut piece feeds each slot; a left-side cut serves both sides
SOURCE = {slot: ("chest" if slot == "chest" else
                 slot if slot in ("groin",) else slot + "_l") + "_world"
          for slot in ("chest", "groin", "clavicle", "upperarm", "forearm",
                       "upperleg", "knee", "ankle", "foot", "hand")}

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
    ap.add_argument("--overlap", type=int, default=1,
                    help="rings of triangles each piece steals from its "
                         "neighbours, so a seam does not read as a hole")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    parts = os.path.join(args.scratch, "parts")
    os.makedirs(parts, exist_ok=True)
    print("cutting by bone, into each bone's own frame ...")
    done = run([os.path.join(HERE, "glb_bodyparts.py"), args.model,
                "--out", parts, "--overlap", str(args.overlap)])
    print(done.stdout.rstrip() or done.stderr.rstrip())
    if done.returncode:
        return 1

    mesh_dir = os.path.join(args.out, "Meshes", "zenar")
    if args.write:
        os.makedirs(mesh_dir, exist_ok=True)
    scales, rows = {}, []

    def make(slot, fallback=None):
        donor, ref, turn, cut = SLOTS[slot]
        source = os.path.join(parts, SOURCE[slot] + ".obj")
        if not os.path.exists(source):
            rows.append("%-11s%-28s  no cut piece" % (slot, ""))
            return None
        target = os.path.join(mesh_dir, slot + ".nif")
        core = os.path.join(parts, SOURCE[slot].replace("_world", "_core_world")
                            + ".obj")
        call = [os.path.join(HERE, "nif_write.py"), source, "--donor", donor,
                "--core", core,
                "--reference", ref or donor, "--out", target,
                "--texture", args.texture, "--clearance", str(args.clearance)]
        if turn:
            call += ["--axes=" + turn]
        if cut:
            call += ["--trim", cut]
        if slot in IN_WORLD:
            bone, which = IN_WORLD[slot]
            call += ["--bone", bone]
            if which:
                call += ["--shape", which]
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

    # Every slot is now fitted against something in its own frame - the vanilla
    # naked part for the limbs, a rigid pauldron for the clavicle, and for the
    # chest a skinned cuirass with the piece cut in character space to match.
    # The median fallback these last two used is gone with it.
    for slot in SLOTS:
        got = make(slot)
        if got:
            scales[slot] = got
    median = sorted(scales.values())[len(scales) // 2] if scales else 1.0

    print("\n%-11s%-28s%7s%9s  ENGINE"
          % ("SLOT", "REFERENCE", "SCALE", "BYTES"))
    for line in rows:
        print(line)
    built = sum(1 for r in rows if r.endswith("accepts"))
    if scales:
        print("\nscale off the vanilla body: %.1f to %.1f, median %.1f - and "
              "They differ because Morrowind's body is not this model's: its "
              "Forearm bodypart spans 8.1 units where its Ankle spans 24.3."
              % (min(scales.values()), max(scales.values()), median))
    print("\n%d of %d pieces built and accepted." % (built, len(SLOTS)))
    print("The hand rides a donor of its own: any single-shape file with an "
          "identity transform, the bone decides the rest.")
    if not args.write:
        print("Dry run. Pass --write to build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
