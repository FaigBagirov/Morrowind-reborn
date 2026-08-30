#!/usr/bin/env python3
"""Cut a rigged glTF body into the bodypart slots Morrowind wears.

    python tools/scripts/glb_bodyparts.py model.glb --out parts/

Morrowind does not skin a body. It dresses one from **separate rigid pieces** -
chest, groin, clavicles, upper arms, forearms, hands, upper legs, knees,
ankles, feet - each its own mesh, each attached to its own bone. So a modern
rigged suit has to be cut apart before any of it can be worn, and where to cut
is the whole question.

**The rig answers it.** A skinned glTF stores, per vertex, which joints move it
and how strongly. Taking the strongest joint and looking up which Morrowind slot
that bone belongs to gives a split along the model's own anatomy - not along a
plane guessed from outside. A vertex on the elbow goes where the artist said the
elbow is.

Cutting by plane was the alternative and it is worse in two ways: it leaves open
holes along the cut that want new geometry, and it puts the seam where the
arithmetic falls rather than where the joint is.

## Each piece comes out in its own bone's frame, and it must

A Morrowind bodypart is not authored in world space. It lives in the frame of
the bone it hangs on - origin at the joint, axes along the bone - and the frames
differ from one bone to the next: measured on the vanilla body, the upper arm,
forearm and thigh run along local X, the knee and calf along Z, the foot along
Y. A piece cut in the model's world space is in its A-pose, arm hanging down and
out, so the upper arm comes out diagonal - 2.34 by 2.51 across two axes that
should be one. Translating and scaling that into a bodypart slot can only
scatter the suit, which is exactly what it did on screen.

The rig carries the cure. `inverseBindMatrices` is the transform from world
space into each joint's own frame, so applying the anchor joint's takes a piece
out of the pose and into the frame Morrowind expects. It is exact - no fitting,
no guessing. Measured afterwards, the arm, thigh and foot then agree with the
vanilla parts axis for axis, and only the calf disagrees, by one discrete
ninety-degree turn.

**Bone-local coordinates are not in world units.** This rig bakes roughly a
tenth into the bind matrices, so a piece that spanned 2.3 in world space spans
0.27 here. Nothing downstream may assume otherwise, and the scale is taken from
the vanilla part rather than carried over.

## What this still does not settle

Whether each piece is then the right *size*. A modern character's proportions
are not Morrowind's, and that is measured against the vanilla part it replaces,
in `nif_write.py`.
"""

import argparse
import os
import re
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glb import Gltf  # noqa: E402
from obj import write as write_obj  # noqa: E402

# Which Morrowind slot each bone belongs to. The names are the standard rig's;
# the numbers Morrowind uses are in the comment beside each.
SLOTS = (
    ("chest", 3, ("spine_",)),
    ("groin", 4, ("pelvis",)),
    ("clavicle", 13, ("clavicle_", "shldrpad")),
    ("upperarm", 8, ("upperarm_",)),
    ("forearm", 7, ("lowerarm_",)),
    ("hand", 5, ("hand_", "thumb_", "index_", "middle_", "ring_", "pinky_",
                 "wrist")),
    ("upperleg", 12, ("thigh_",)),
    ("knee", 11, ()),          # the upper half of the calf, split by height
    ("ankle", 10, ("calf_",)),
    ("foot", 9, ("foot_", "ball_", "toe_")),
    ("neck", 2, ("neck_",)),
    ("head", 0, ("head",)),
)

SIDED = {"clavicle", "upperarm", "forearm", "hand", "upperleg", "knee",
         "ankle", "foot"}


def slot_of(bone):
    """The Morrowind slot a bone belongs to, and which side it is on."""
    low = bone.lower()
    side = ""
    if re.search(r"_l(_|$)", low):
        side = "l"
    elif re.search(r"_r(_|$)", low):
        side = "r"
    for name, _part, keys in SLOTS:
        if any(k in low for k in keys):
            return name, side
    return None, side


def dominant(model, prim):
    """The strongest joint index per vertex, and the joint name list."""
    attrs = prim["attributes"]
    joints = model.accessor(attrs["JOINTS_0"]).astype(np.int32)
    weights = model.accessor(attrs["WEIGHTS_0"]).astype(np.float64)
    best = np.argmax(weights, axis=1)
    return joints[np.arange(len(joints)), best]


def split(path, out_dir, knee_fraction=0.5, overlap=2):
    model = Gltf(path)
    skin = model.json["skins"][0]
    bones = [model.json["nodes"][n].get("name", f"node{n}")
             for n in skin["joints"]]
    # Column-major in the file, so transpose to get row-vector matrices.
    bind = model.accessor(skin["inverseBindMatrices"])
    bind = bind.reshape(-1, 4, 4).transpose(0, 2, 1)

    # **A bone with no slot inherits its parent's.** A rig carries more than
    # the dozen bones Morrowind knows: this one has hip and strap cloth, a
    # tail, and elbow deformers, and matching only the names left 9 per cent of
    # the vertices and 7.8 per cent of the triangles belonging to nothing at
    # all. They were dropped, and the holes showed on screen as a torso you
    # could see the floor through. Walking up the hierarchy needs no list of
    # names and works on the next model too.
    where = {n: i for i, n in enumerate(skin["joints"])}
    parent = {}
    for i, node in enumerate(model.json["nodes"]):
        for kid in node.get("children", []):
            parent[kid] = i
    inherited = 0

    def resolve(index):
        nonlocal inherited
        node = skin["joints"][index]
        steps = 0
        while node is not None and steps < 64:
            here = where.get(node)
            if here is not None:
                name, side = slot_of(bones[here])
                if name:
                    if steps:
                        inherited += 1
                    return name, side
            node = parent.get(node)
            steps += 1
        return None, ""

    global _BONES
    _BONES = bones
    pieces = {}

    # **Every distinct skinned primitive, not just the first.** This model
    # carries the body and the helmet as separate meshes, each listed three
    # times over with a different material - and stopping at the first meant
    # the helmet never arrived, which is where the collar lives. Faig had
    # already noticed the neck coming from the helmet rather than the body.
    # Primitives are recognised by their POSITION accessor, so the duplicates
    # are read once.
    chunks, seen = [], set()
    for mesh in model.json.get("meshes", []):
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            if "JOINTS_0" not in attrs or "POSITION" not in attrs:
                continue
            # Recognised by the geometry, not by the accessor index: the
            # duplicates are three separate accessors holding the same points.
            v = model.accessor(attrs["POSITION"])
            mark = (len(v), tuple(np.round(v[0], 5)), tuple(np.round(v[-1], 5)))
            if mark in seen:
                continue
            seen.add(mark)
            chunks.append(prim)

    all_verts, all_uv, all_tris, all_joint = [], [], [], []
    at = 0
    for prim in chunks:
        attrs = prim["attributes"]
        v = model.accessor(attrs["POSITION"]).astype(np.float64)
        u = (model.accessor(attrs["TEXCOORD_0"]).astype(np.float64)
             if "TEXCOORD_0" in attrs else np.zeros((len(v), 2)))
        t = model.accessor(prim["indices"]).ravel().astype(np.int32).reshape(-1, 3)
        all_verts.append(v)
        all_uv.append(u)
        all_tris.append(t + at)
        all_joint.append(dominant(model, prim))
        at += len(v)
    if not chunks:
        return pieces
    verts = np.vstack(all_verts)
    uv = np.vstack(all_uv)
    tris = np.vstack(all_tris)
    joint = np.concatenate(all_joint)
    print(f"read {len(chunks)} distinct skinned primitives, "
          f"{len(verts)} vertices")
    if True:
        if True:

            label = np.empty(len(verts), object)
            settled = {}
            for i, ji in enumerate(joint):
                if ji not in settled:
                    settled[ji] = resolve(int(ji))
                name, side = settled[ji]
                label[i] = None if name is None else (
                    f"{name}_{side}" if name in SIDED and side else name)
            missing = sum(1 for x in label if x is None)
            print(f"bones resolved through a parent: {inherited}; "
                  f"vertices still unplaced: {missing} of {len(label)}")

            # A triangle belongs where its majority of corners belong.
            for tri in tris:
                votes = defaultdict(int)
                for c in tri:
                    if label[c]:
                        votes[label[c]] += 1
                if not votes:
                    continue
                key = max(votes.items(), key=lambda kv: kv[1])[0]
                pieces.setdefault(key, []).append(tri)

            # The calf carries two Morrowind slots. Split it by height, which is
            # what the game does too - knee above, ankle below.
            for side in ("l", "r"):
                key = f"ankle_{side}"
                if key not in pieces:
                    continue
                got = np.array(pieces[key])
                mid = verts[got].reshape(-1, 3)[:, 1]
                cut = mid.min() + (mid.max() - mid.min()) * knee_fraction
                high = verts[got].mean(axis=1)[:, 1] > cut
                if high.any() and (~high).any():
                    pieces[f"knee_{side}"] = got[high].tolist()
                    pieces[key] = got[~high].tolist()

            # **Grow every piece into its neighbours.** A body cut at the
            # joints leaves each piece open at both ends, and an open end is a
            # hole: backfaces are culled, so the player looks straight through
            # the seam. Faig saw exactly that - no knee, no throat, "thread-like"
            # edges where a cut ran. Morrowind's own parts avoid it by
            # overlapping, and this is how they get to.
            #
            # A ring is every triangle touching a vertex already in the piece.
            # Two of them is enough to hide a seam and cheap: it costs vertices
            # in the overlap only.
            # Taken after the calf has been split, or the ankle's core would
            # be the whole calf and the piece would be fitted to twice its
            # length. It came out 16 units where its reference is 24.
            core = {k: [list(t) for t in v] for k, v in pieces.items()}
            if overlap:
                whole = [tuple(t) for t in tris]
                for key in list(pieces):
                    have = {int(i) for t in pieces[key] for i in t}
                    got = {tuple(t) for t in pieces[key]}
                    for _ring in range(overlap):
                        added = [t for t in whole
                                 if t not in got and any(i in have for i in t)]
                        got.update(added)
                        have.update(int(i) for t in added for i in t)
                    pieces[key] = [list(t) for t in got]

            _emit(pieces, verts, uv, out_dir, joint, bind)
            # The un-grown piece as well. **The overlap must not be fitted.**
            # A grown piece squeezed into the vanilla part's box makes the limb
            # itself shorter and spends the difference on the seam. So the
            # transform is measured from the core and applied to the grown one,
            # which then sticks out past the joint exactly as intended.
            _emit(core, verts, uv, out_dir, joint, bind, suffix="_core")
            return pieces
    return pieces


def _emit(pieces, verts, uv, out_dir, joint, bind, suffix=""):
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    if not suffix:
        print(f"{'SLOT':<16}{'VERTS':>8}{'TRIS':>8}  BONE-LOCAL SIZE   ANCHOR")
    for key in sorted(pieces):
        tris = np.array(pieces[key], np.int32)
        used = np.unique(tris)
        remap = {old: new for new, old in enumerate(used)}
        sub = np.array([[remap[i] for i in t] for t in tris], np.int32)
        pv, puv = verts[used], uv[used]

        # Into the frame of the joint that moves most of this piece. The
        # majority joint rather than a named one, because the name that anchors
        # a slot differs between rigs and the weights do not.
        anchor = Counter(joint[used].tolist()).most_common(1)[0][0]
        world = pv
        pv = (np.c_[pv, np.ones(len(pv))] @ bind[anchor].T)[:, :3]

        size = np.round(pv.max(axis=0) - pv.min(axis=0), 3)
        if not suffix:
            print(f"{key:<16}{len(pv):>8}{len(sub):>8}  {str(size):<18}"
                  f"{_bone_name(anchor)}")
        if out_dir:
            write_obj(os.path.join(out_dir, key + suffix + ".obj"),
                      pv, puv, sub, key)
            # The world-space copy as well. Not every Morrowind bodypart is
            # rigid: **every cuirass in the game is skinned**, carrying the
            # whole Bip01 skeleton, so its vertices live in the character's
            # space rather than in a bone's. A chest cut into a bone's frame
            # cannot be fitted to one of those, and there is no rigid chest
            # anywhere in the three masters to fit instead.
            write_obj(os.path.join(out_dir, key + suffix + "_world.obj"),
                      world, puv, sub, key)


_BONES = []


def _bone_name(i):
    return _BONES[i] if i < len(_BONES) else str(i)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("--out", help="directory for the per-slot .obj files")
    ap.add_argument("--knee", type=float, default=0.5,
                    help="where along the calf the knee slot ends")
    ap.add_argument("--overlap", type=int, default=1,
                    help="rings of triangles each piece steals from its "
                         "neighbours, so the seams do not show as holes")
    args = ap.parse_args()
    split(args.path, args.out, args.knee, args.overlap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
