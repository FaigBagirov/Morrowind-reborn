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
MODEL_TO_GAME = "-x,z,y"

# The rigid donors. **None of them may be skinned.** Every cuirass in the game
# is, and putting our geometry into one leaves its bone weights describing the
# vertices we replaced: the engine drives ours by weights that mean nothing and
# the torso collapses into a blade reaching the floor. A donor only carries the
# node, the material and the texture reference - the bone decides placement - so
# any rigid single-shape file serves, which is how the chest and the hand are
# done. Checked, not assumed: only the cuirass came back skinned.
DONOR = {
    "head": BODY % "neck",
    "chest": BODY % "ankle",
    "groin": BODY % "groin",
    "clavicle": "meshes/a/a_daedric_pauldron_cl.nif",
    "upperarm": BODY % "upper arm",
    "forearm": BODY % "forearm",
    "upperleg": BODY % "upper leg",
    "knee": BODY % "knee",
    "ankle": BODY % "ankle",
    "foot": "meshes/a/a_daedric_boots_f.nif",
    "hand": BODY % "ankle",
}
# What each is fitted against, and which shapes of it. `skins.nif` is the Chest
# bodypart and both Hand bodyparts at once, seven shapes in one file.
REFERENCE = {
    "head": ("meshes/b/b_n_dark elf_m_head_01.nif", None),
    "chest": (BODY % "skins", "Tri Chest"),
    "groin": (BODY % "groin", None),
    "clavicle": ("meshes/a/a_daedric_pauldron_cl.nif", None),
    "upperarm": (BODY % "upper arm", None),
    "forearm": (BODY % "forearm", None),
    "upperleg": (BODY % "upper leg", None),
    "knee": (BODY % "knee", None),
    "ankle": (BODY % "ankle", None),
    "foot": (BODY % "foot", None),
    # bone-local, so the A-pose wrist twist cancels; the file stores the hand
    # shapes in the bone's frame already
    "hand": (BODY % "skins", "Left Hand"),
}
# The skeleton node each hangs on, without the side.
# The helmet mesh is painted on its own sheet, so the two pieces cut from it
# wear that one. Everything else is the body sheet.
SHEET = {"head": "zenar_helm.dds"}

# **Which space a piece is fitted in, and it is not one answer for all.**
#
# World space compares a piece against the vanilla part hung on its own bone,
# where up is up for both - which is what the chest, the head and the neck need,
# and what let the chest be fitted at all. But the model stands in an A-pose
# with its arms out, while Morrowind's skeleton has them hanging at the side:
# for a limb the two boxes are in different poses, and fitting one to the other
# squashes it and pulls it inward. Faig saw the forearms pressed towards the
# middle.
#
# A bone's own frame has no pose in it, so limbs are fitted there. The axes
# come from ranking the extents, which was checked against an independent
# measurement - the rotation carrying each bone's own anatomical directions
# into Morrowind's - and the two agree: the forearm needs no turn, the knee
# needs X and Z exchanged.
IN_WORLD = {"chest", "head", "groin"}

# The forearm keeps its length in proportion, anchored at the elbow. The naked
# Forearm bodypart is 8.1 units long and the model's forearm plate nearly
# matches its upper arm; box-fitted it shrank to a stub inside the sleeve and
# Faig reported the forearms invisible.
PROP = {"forearm": ("x", "min")}

# Explicit turns for the two slots whose extents cannot say which way round
# they go - the hand's box is nearly square across the palm and the foot's
# roll is invisible to ranking. Derived anatomically rather than guessed: a
# frame from two measured directions in each skeleton (fingers and forearm for
# the hand, toes and ankle for the foot), one rotated onto the other, snapped
# to the axis grid. Faig saw the left hand fingers-up and the feet a quarter
# turn out; ranking had silently picked the wrong sign.
# The hand ends up needing no turn at all: the model's right cut, read into
# the game's left slot, already points the fingers down with the palm inward.
# Every turn I had put on it was undoing itself.
LOCAL_AXES = {"foot": "-z,-y,-x"}

# Corrections Faig called from the screen, each verified against a rendered
# candidate sheet before being written down - three 180-degree turns are
# possible per piece and a wireframe can compare them where prose cannot.
# The thigh and upper arm hung upside down, the pauldron faced backward, the
# hand needed its fingers turned from forward to down (folded into LOCAL_AXES
# above), the head floated at 70 per cent of its own height, and the upper
# arms sat a touch too close to the body - the shift is world -1.8 on X,
# expressed in the arm bone's frame.
POST_AXES = {"upperleg": "-x,y,-z", "upperarm": "-x,y,-z",
             "clavicle": "-x,-y,z",
             # palms were facing backward; a quarter roll about the finger
             # axis turns them in against the thigh
             "hand": "x,-z,y"}

# **A post-shift is applied in the frame the piece was fitted in**, which for a
# world-fitted slot is the bodypart's own frame, not the world. Writing the
# head's drop as a world vector moved it 13 units sideways instead - measured,
# our head centre sat at x 13.05 against the vanilla 0.05, which is exactly the
# sideways drift Faig saw. Every entry here is the world movement wanted, put
# through the node's rotation first.
# And the conversion is measured, not derived: the local-to-world map is found
# numerically by nudging the piece one unit along each local axis and reading
# where its centre goes, then solved. Deriving it by hand went wrong twice -
# once by ignoring the donor's own rotation, once by dividing where it should
# have multiplied - and each mistake moved the head sideways instead of down.
#   head      world (-3, 0, -3)      hand  world (0, 0, -4)
#   upperarm  world (-1.8, 0, -3)    - the outward spread and the drop together
# The arm segments are left level with their vanilla twins. Nudging them has
# now missed in both directions on Faig's screen, so they sit where the
# measurement puts them until there is a landmark to aim at.
POST_SHIFT = {"hand": "0.099,0.002,-0.008",
              "head": "-8.682,2.37,-1.503"}

# The groin carries the model's tabard - hip cloth, front straps, a tail of
# fabric that hangs to the knees. Box-fitted it was crushed into the crotch;
# hung, the cloth falls below the box the way the author drew it.
HANG = {"groin"}

# A helmet fitted per axis into an elf head's box comes out flattened at the
# sides, which is exactly what Faig reported. Proportions are kept instead.
UNIFORM = {"head"}

# The chest gets no clearance. Clearance exists so armour sits over a body, and
# the chest replaces the body rather than covering it - with 8 per cent it
# reached down to 67.3 where the vanilla torso stops at 71.4, and rode on the
# thighs.
CLEARANCE = {"chest": 1.0, "groin": 1.0,
             # the Daedric pauldron donor box is grander than the author's
             # shoulder line; ninety per cent of it hugs instead of floating
             "clavicle": 0.9}

NODE = {"head": "Head", "chest": "Chest",
        "groin": "Groin", "clavicle": "%s Clavicle",
        "upperarm": "%s Upper Arm", "forearm": "%s Forearm",
        "upperleg": "%s Upper Leg", "knee": "%s Knee", "ankle": "%s Ankle",
        "foot": "%s Foot", "hand": "%s Hand"}

# **Both sides are built, and that is not waste.** The vanilla armour records
# leave every left slot empty and let the engine mirror the right one. Mirroring
# negates an axis of the *local* coordinates, which is harmless for a vanilla
# part sitting on its own bone and ruinous for ours, which carry an offset from
# the world-space fit: Faig's left leg was missing outright and his forearms
# were pushed in towards the middle. Filling both slots removes the mirror from
# the question.
SIDED = ("clavicle", "upperarm", "forearm", "upperleg", "knee", "ankle",
         "foot", "hand")

# **Which side of the model to cut for a slot, and it is not always the left.**
# The model's left is the game's right - measured: the model's left hand sits
# at x +4.26 while the game's is at -16.7. For a limb that hardly matters,
# since an arm is nearly symmetric; for a hand it matters completely, and Faig
# saw the hands swapped. So the asymmetric pieces take the model's right cut,
# which the engine then reads as the game's left. The foot is here for the same
# reason, before it is reported.
FROM_RIGHT = {"hand", "foot"}


def slots():
    """Every piece to build: its name, cut, donor, reference, node and turn."""
    out = {}
    for slot, donor in DONOR.items():
        ref, shape = REFERENCE[slot]
        # **One piece per slot, authored left; the engine mirrors it.** That
        # is how vanilla works - both Daedric pauldron records reference the
        # same `_cl` bodypart and the right slot mirrors it natively. My own
        # mirror pass through base_anim's rest pose put both pauldrons on the
        # left: the game hangs parts on *animated* bones, and the rest pose is
        # not what plays. The engine's mirror lives on the right side of that
        # problem; mine could not.
        side = "_r" if slot in FROM_RIGHT else "_l"
        cut = (slot + side) if slot in SIDED else slot
        out[slot] = {
            "slot": slot,
            "cut": cut + ("_world" if slot in IN_WORLD else ""),
            "donor": donor,
            "reference": ref,
            "shape": shape,
            "node": NODE[slot] % "Left" if "%s" in NODE[slot] else NODE[slot],
            "axes": MODEL_TO_GAME,
        }
    return out


SLOTS = slots()

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

    def make(key):
        spec = SLOTS[key]
        source = os.path.join(parts, spec["cut"] + ".obj")
        if not os.path.exists(source):
            rows.append("%-12s%-22s  no cut piece" % (key, ""))
            return None
        core = os.path.join(parts, spec["cut"].replace("_world", "_core_world")
                            + ".obj")
        target = os.path.join(mesh_dir, key + ".nif")
        call = [os.path.join(HERE, "nif_write.py"), source,
                "--core", core, "--donor", spec["donor"],
                "--reference", spec["reference"], "--out", target,
                "--texture", SHEET.get(spec["slot"], args.texture),
                "--clearance", str(CLEARANCE.get(spec["slot"], args.clearance)),
                "--double"]
        if spec["slot"] in IN_WORLD:
            call += ["--bone", spec["node"], "--axes=" + spec["axes"]]
        if spec["slot"] in UNIFORM:
            call += ["--uniform"]
        if spec["slot"] in HANG:
            call += ["--hang"]
        if spec["shape"]:
            call += ["--shape", spec["shape"]]
        if spec["slot"] in PROP:
            axis, anchor = PROP[spec["slot"]]
            call += ["--prop-axis", axis, "--prop-anchor", anchor]
        if spec["slot"] in LOCAL_AXES:
            call += ["--axes=" + LOCAL_AXES[spec["slot"]]]
        if spec["slot"] in POST_AXES:
            call += ["--post-axes=" + POST_AXES[spec["slot"]]]
        if spec["slot"] in POST_SHIFT:
            call += ["--post-shift=" + POST_SHIFT[spec["slot"]]]
        if not args.write:
            rows.append("%-12s%-22s  dry run" % (key, spec["node"]))
            return None
        made = run(call)
        if made.returncode:
            last = (made.stderr.strip().splitlines() or ["failed"])[-1]
            rows.append("%-12s%-22s  %s" % (key, spec["node"], last[:40]))
            return None
        said = [x for x in made.stdout.splitlines() if x.startswith("aligned")]
        scale = float(said[0].split("scale ")[1].split(",")[0]) if said else 0.0
        ok = (os.path.exists(NIFTEST)
              and subprocess.run([NIFTEST, target],
                                 capture_output=True).returncode == 0)
        rows.append("%-12s%-22s%7.1f%9d  %s"
                    % (key, spec["node"], scale, os.path.getsize(target),
                       "accepts" if ok else "REJECTS"))
        return scale if ok else None

    for key in SLOTS:
        got = make(key)
        if got:
            scales[key] = got
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
    print("One piece per sided slot, authored left; the engine mirrors it "
          "for the right slot, exactly as vanilla pauldrons work.")
    if not args.write:
        print("Dry run. Pass --write to build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
