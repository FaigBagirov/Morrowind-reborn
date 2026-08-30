#!/usr/bin/env python3
"""Read Morrowind's skeleton, and hang bodyparts on it.

    python tools/scripts/skeleton.py --body        # the vanilla naked body
    python tools/scripts/skeleton.py --ours        # our imported suit

Every round of the armour import so far has been settled by a screenshot, and a
screenshot of a character in a dim room cannot say whether a piece is misplaced,
mis-sized or simply dark. This assembles the figure here instead: each bodypart
put where `base_anim.nif` says its attachment node is, drawn from the front and
the side.

**It checks itself.** `--body` assembles the vanilla naked parts. If those come
out as a human being, the block parse, the hierarchy and the transform order are
all right, and what `--ours` then shows can be believed. If they do not, nothing
downstream is worth reading.

## Parsing without knowing every block

A NIF is a list of blocks, each preceded by its length-prefixed type name, and
the contents differ per type - so walking it properly would mean implementing
dozens of layouts. It is not needed. The block *starts* can be found by their
type names alone, and the file's own header says how many blocks there are, so
the scan has an oracle: if the count does not match, the parse is wrong and this
raises rather than guessing. Only NiNode is then decoded, which is the one
layout this needs.
"""

import argparse
import os
import re
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nif_write import _resolve  # noqa: E402
from uvmap import parse_trishape, read_mesh  # noqa: E402

SKELETON = "meshes/base_anim.nif"

# Which skeleton node each bodypart hangs on. These are the names OpenMW uses,
# and they are present in base_anim.nif - checked, not assumed.
BONE = {
    "chest": "Chest", "groin": "Groin", "neck": "Neck", "head": "Head",
    "clavicle": "Left Clavicle", "upperarm": "Left Upper Arm",
    "forearm": "Left Forearm", "wrist": "Left Wrist", "hand": "Left Hand",
    "upperleg": "Left Upper Leg", "knee": "Left Knee",
    "ankle": "Left Ankle", "foot": "Left Foot",
}
# and the same slots on the other side, which the engine mirrors
OTHER = {k: v.replace("Left", "Right") for k, v in BONE.items()
         if v.startswith("Left")}

VANILLA = {
    "chest": None,          # skinned, no rigid mesh to hang
    "groin": "meshes/b/b_n_dark elf_m_groin.nif",
    "upperarm": "meshes/b/b_n_dark elf_m_upper arm.nif",
    "forearm": "meshes/b/b_n_dark elf_m_forearm.nif",
    "wrist": "meshes/b/b_n_dark elf_m_wrist.nif",
    "upperleg": "meshes/b/b_n_dark elf_m_upper leg.nif",
    "knee": "meshes/b/b_n_dark elf_m_knee.nif",
    "ankle": "meshes/b/b_n_dark elf_m_ankle.nif",
    "foot": "meshes/b/b_n_dark elf_m_foot.nif",
    "neck": "meshes/b/b_n_dark elf_m_neck.nif",
    "head": "meshes/b/b_n_dark elf_m_head_01.nif",
}

# A block's class name, as opposed to a node's own name - which is stored the
# same way, length-prefixed ASCII, and is why an unrestricted scan overshot by
# seven on the skeleton. Every class in this format begins "Ni", bar a short
# list of Morrowind's own.
CLASS = re.compile(rb"^(Ni[A-Za-z0-9_]{1,29}|RootCollisionNode|AvoidNode"
                   rb"|BoundingBox)$")


def blocks(blob):
    """Every block's type and offset, in file order, checked against the count.

    The header ends with a version line, the version word and the block count.
    A block is a length-prefixed class name followed by its data, so the class
    names can be found without decoding anything - and the count says whether
    the scan found exactly the blocks that are there.
    """
    line = blob.index(b"\n") + 1
    _version, count = struct.unpack_from("<II", blob, line)
    found, at = [], line + 8
    while at < len(blob) - 4:
        length, = struct.unpack_from("<I", blob, at)
        if 3 <= length <= 32:
            name = blob[at + 4:at + 4 + length]
            if CLASS.match(name):
                found.append((name.decode(), at + 4 + length))
                at += 4 + length
                continue
        at += 1
    if len(found) != count:
        raise ValueError(f"header says {count} blocks, scan found {len(found)}")
    return found


def nodes(blob):
    """Name, local transform and children of every NiNode, by block index."""
    out = {}
    for index, (kind, at) in enumerate(blocks(blob)):
        if kind not in ("NiNode", "NiBSAnimationNode", "NiBSParticleNode",
                        "RootCollisionNode", "AvoidNode"):
            continue
        length, = struct.unpack_from("<i", blob, at)
        name = blob[at + 4:at + 4 + length].decode("latin-1")
        p = at + 4 + length + 8 + 2                 # extra, controller, flags
        translation = np.frombuffer(blob, np.float32, 3, p).astype(np.float64)
        rotation = np.frombuffer(blob, np.float32, 9, p + 12).reshape(3, 3)
        scale, = struct.unpack_from("<f", blob, p + 48)
        p += 52 + 12                                 # scale, velocity
        properties, = struct.unpack_from("<I", blob, p)
        p += 4 + 4 * properties
        has_box, = struct.unpack_from("<I", blob, p)
        # A bounding box is an int, a translation, a rotation and an extent:
        # 4 + 12 + 36 + 12. Sixty-four, not the fifty-two I first wrote, which
        # put the child count twelve bytes into the extent and asked for four
        # billion children.
        p += 4 + (64 if has_box else 0)
        children, = struct.unpack_from("<I", blob, p)
        if children > 512:
            raise ValueError(f"{name}: {children} children is not a parse")
        kids = struct.unpack_from(f"<{children}i", blob, p + 4)
        out[index] = {"name": name, "t": translation,
                      "r": np.array(rotation, np.float64), "s": float(scale),
                      "kids": [k for k in kids if k >= 0]}
    return out


def world(blob):
    """Every named node's world transform, composed down the tree."""
    tree = nodes(blob)
    child = {k for n in tree.values() for k in n["kids"]}
    roots = [i for i in tree if i not in child]
    out, stack = {}, [(i, np.eye(3), np.zeros(3), 1.0) for i in roots]
    while stack:
        index, rot, pos, scale = stack.pop()
        node = tree.get(index)
        if node is None:
            continue
        r = rot @ node["r"]
        p = pos + rot @ (node["t"] * scale)
        s = scale * node["s"]
        out[node["name"]] = (r, p, s)
        for kid in node["kids"]:
            stack.append((kid, r, p, s))
    return out


def shape(blob):
    """The NiTriShape's own transform, which is not always identity.

    **This is easy to miss and it is load-bearing.** The vanilla upper leg
    carries a rotation swapping X and Z and a translation of ten units; the
    ankle beside it carries none. Ignore it and the thigh assembles lying
    across the hips instead of hanging from them - which is exactly how it
    first came out here.

    It cancels out in the fitting, where the donor and the reference are the
    same file and both sides are in the same raw space. It does not cancel in
    an assembly, and it does not cancel when a donor and a reference are
    different files.
    """
    for kind, at in blocks(blob):
        if kind != "NiTriShape":
            continue
        length, = struct.unpack_from("<i", blob, at)
        p = at + 4 + length + 8 + 2
        return (np.array(np.frombuffer(blob, np.float32, 9, p + 12)
                         .reshape(3, 3), np.float64),
                np.frombuffer(blob, np.float32, 3, p).astype(np.float64),
                float(struct.unpack_from("<f", blob, p + 48)[0]))
    return np.eye(3), np.zeros(3), 1.0


def all_shapes(blob, only=None):
    """Every NiTriShape in a file, each already through its own transform.

    Multi-shape files are the normal case for the parts this cannot otherwise
    reach. `b_n_..._skins.nif` is the Dark Elf's Chest bodypart *and* his Hand
    bodypart at once - seven shapes, three per hand and one torso - which is why
    reading only the first one made the chest measure seven units across.
    """
    out = []
    shapes = [at for kind, at in blocks(blob) if kind == "NiTriShape"]
    datas = [at for kind, at in blocks(blob) if kind == "NiTriShapeData"]
    for at, data in zip(shapes, datas):
        length, = struct.unpack_from("<i", blob, at)
        name = blob[at + 4:at + 4 + length].decode("latin-1")
        if only and only.lower() not in name.lower():
            continue
        p = at + 4 + length + 8 + 2
        move = np.frombuffer(blob, np.float32, 3, p).astype(np.float64)
        turn = np.array(np.frombuffer(blob, np.float32, 9, p + 12)
                        .reshape(3, 3), np.float64)
        size, = struct.unpack_from("<f", blob, p + 48)
        verts, _uv, tris = parse_trishape(blob[data - len("NiTriShapeData"):])
        out.append(((verts * size) @ turn.T + move, tris, name))
    return out


def unplace(verts, frame):
    """Back out of world space into the bodypart's own frame.

    The inverse of `place`, and the step that lets a piece be fitted where
    everyone can see what up means and then written where the engine wants it.
    """
    r, p, s = frame
    return ((verts - p) @ r) / s


def place(verts, frame):
    """A part's vertices where the skeleton puts them."""
    r, p, s = frame
    return (verts * s) @ r.T + p


def draw(pieces, path, size=900):
    """Front and side, orthographic, with a floor line for scale."""
    from PIL import Image, ImageDraw
    every = np.vstack([v for v, _t in pieces])
    lo, hi = every.min(0), every.max(0)
    centre = (lo + hi) / 2.0
    span = float((hi - lo).max()) * 1.12
    img = Image.new("RGB", (size, size // 2), (16, 16, 18))
    pen = ImageDraw.Draw(img)
    for panel, (a, b, label) in enumerate(((0, 2, "front"), (1, 2, "side"))):
        wide = size // 2
        for verts, tris in pieces:
            x = ((verts[:, a] - centre[a]) / span + 0.5) * (wide - 40) + 20
            y = (0.5 - (verts[:, b] - centre[b]) / span) * (size // 2 - 40) + 20
            px = np.c_[x + panel * wide, y]
            for t in tris:
                pen.polygon([tuple(px[i]) for i in t] + [tuple(px[t[0]])],
                            outline=(225, 228, 235))
        pen.text((panel * wide + 12, 10), label, fill=(140, 140, 150))
    img.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ours", action="store_true",
                    help="our built suit instead of the vanilla naked body")
    ap.add_argument("--out", default=os.path.join("tools", "reports"))
    args = ap.parse_args()

    with open(_resolve(SKELETON), "rb") as f:
        frames = world(f.read())
    print(f"skeleton: {len(frames)} named nodes")

    built = os.path.join("tools", "build", "armour-momw", "Meshes", "zenar")
    pieces, report = [], []
    if args.ours:
        # Every file on disk, both sides. The first version drew only the left
        # pieces, and a right pauldron flipped onto its back went to the game
        # unseen - the self-check has to see everything the player will.
        for name in sorted(os.listdir(built)):
            if not name.endswith(".nif"):
                continue
            slot = name[:-4]
            base, side = (slot[:-2], slot[-1]) if slot[-2:] in ("_l", "_r")                 else (slot, "")
            bone = BONE.get(base)
            if not bone:
                continue
            if side == "r":
                bone = bone.replace("Left", "Right")
            with open(os.path.join(built, name), "rb") as f:
                blob = f.read()
            verts, _uv, tris = parse_trishape(blob)
            put = place(place(verts, shape(blob)), frames[bone])
            pieces.append((put, tris))
            report.append((slot, bone, put[:, 2].min(), put[:, 2].max()))
    for slot, bone in BONE.items():
        if args.ours:
            break
        if True:
            rel = VANILLA.get(slot)
            if not rel:
                continue
            verts, _uv, tris = read_mesh(rel)
            with open(_resolve(rel), "rb") as f:
                blob = f.read()
        verts = place(verts, shape(blob))
        for name in (bone, OTHER.get(slot)):
            if not name or name not in frames:
                continue
            put = place(verts, frames[name])
            pieces.append((put, tris))
            if name == bone:
                report.append((slot, name, put[:, 2].min(), put[:, 2].max()))
    for slot, name, low, high in report:
        print(f"  {slot:<10}{name:<18}height {low:8.1f} .. {high:8.1f}")
    if not pieces:
        raise SystemExit("nothing to assemble")
    tall = np.vstack([v for v, _t in pieces])[:, 2]
    print(f"\nassembled height {tall.max() - tall.min():.1f} units, "
          f"floor at {tall.min():.1f}")
    out = os.path.join(args.out,
                       "figure-ours.png" if args.ours else "figure-body.png")
    print(draw(pieces, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
