#!/usr/bin/env python3
"""Pose a downloaded suit onto Morrowind's skeleton and cut it into bodyparts.

    python tools/scripts/fit_suit.py model.glb --write            # real texture
    python tools/scripts/fit_suit.py model.glb --write --paint    # diagnostic

This replaces the per-slot box fitting of `build_armour_set.py`, and the tables
of screen corrections that grew on top of it. Nothing here is tuned by eye: every
number comes from one of the two skeletons or from the engine's own source.

## What the engine does with a rigid bodypart (OpenMW 0.51, attach.cpp)

The part's NIF is hung under the skeleton node named for its slot - `Right
Upper Arm`, `Chest`, `Left Foot`. **If that node's name contains "Left", a
scale of (-1, 1, 1) is put between the node and the part.** The `Right` nodes in
`base_anim.nif` are exactly the mirror of the `Left` ones composed with that
scale - measured, not assumed - so one mesh authored in a `Right` node's frame
comes out as the true mirror image on the left. That is how vanilla works, and
it is why no piece is built for the left side here.

The previous route authored every sided piece in a `Left` node's frame and
never applied the scale. The piece was then negated along the node's X, which
for an arm is the bone's own axis: it grew upward from the joint instead of
down. That is the "arms 30 and 70 per cent too high" Faig kept reporting.

## The route

1. Read the model: every distinct skinned primitive, with its joints, weights
   and inverse bind matrices, which give each joint's head in model space.
2. Carry the model's axes into the game's (`-x, z, y`, measured earlier).
3. **Pose it into Morrowind's rest pose.** Each limb bone is swung, never
   twisted, so that it points where the Morrowind bone points, and its head is
   put on the Morrowind joint. Bones Morrowind has no twin for ride rigidly on
   their nearest mapped ancestor. Vertices follow by the model's own weights.
   The swing is the smallest rotation, so an A-pose palm that faced down faces
   the thigh once the arm hangs.
4. Cut by the dominant joint into slots, as before.
5. Put each piece into its node's frame - the `Right` node for sided slots - and
   through the donor's own node chain, so the written vertices land where the
   engine will put them.
6. Read the written file back and compose it the way the engine does. If the
   vertices do not come back where they were meant to be, it stops.
7. Draw front, side and back of the whole figure as the engine would assemble
   it, both sides, next to nothing but itself.
"""

import argparse
import os
import re
import struct
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from glb import Gltf  # noqa: E402
from glb_bodyparts import slot_of  # noqa: E402
from nif_write import _resolve, build, retexture  # noqa: E402
from skeleton import SKELETON, blocks, nodes, world, shape  # noqa: E402
from uvmap import parse_trishape  # noqa: E402

# Model to game: the model is Y-up facing +Z, the game Z-up facing +Y, and the
# model's left (+X) is the game's left (-X).
AXES = np.array([[-1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]])
MIRROR = np.diag([-1.0, 1.0, 1.0])

# The model's bones that have a Morrowind twin.
TWIN = {"pelvis": "Bip01 Pelvis", "spine_01": "Bip01 Spine",
        "spine_03": "Bip01 Spine1", "spine_05": "Bip01 Spine2",
        "neck_01": "Bip01 Neck", "head": "Bip01 Head"}
# Which of them swing, and toward which child in each skeleton.
AIM = {}
for _s, _S in (("l", "L"), ("r", "R")):
    TWIN.update({f"clavicle_{_s}": f"Bip01 {_S} Clavicle",
                 f"upperarm_{_s}": f"Bip01 {_S} UpperArm",
                 f"lowerarm_{_s}": f"Bip01 {_S} Forearm",
                 f"hand_{_s}": f"Bip01 {_S} Hand",
                 f"thigh_{_s}": f"Bip01 {_S} Thigh",
                 f"calf_{_s}": f"Bip01 {_S} Calf",
                 f"foot_{_s}": f"Bip01 {_S} Foot"})
    AIM.update({f"clavicle_{_s}": f"upperarm_{_s}",
                f"upperarm_{_s}": f"lowerarm_{_s}",
                f"lowerarm_{_s}": f"hand_{_s}",
                f"hand_{_s}": f"middle_01_{_s}",
                f"thigh_{_s}": f"calf_{_s}",
                f"calf_{_s}": f"foot_{_s}"})
AIM_MW = {"middle_01_l": "Bip01 L Finger1", "middle_01_r": "Bip01 R Finger1"}

NODE = {"chest": "Chest", "groin": "Groin", "head": "Head",
        "clavicle": "Clavicle", "upperarm": "Upper Arm", "forearm": "Forearm",
        "hand": "Hand", "upperleg": "Upper Leg", "knee": "Knee",
        "ankle": "Ankle", "foot": "Foot"}
SIDED = {"clavicle", "upperarm", "forearm", "hand", "upperleg", "knee",
         "ankle", "foot"}
# Slots with no bodypart of their own are folded into a neighbour.
FOLD = {"neck": "chest"}

BODY = "meshes/b/b_n_dark elf_m_%s.nif"
DONOR = {"head": BODY % "neck", "chest": BODY % "ankle",
         "groin": BODY % "groin", "clavicle": "meshes/a/a_daedric_pauldron_cl.nif",
         "upperarm": BODY % "upper arm", "forearm": BODY % "forearm",
         "upperleg": BODY % "upper leg", "knee": BODY % "knee",
         "ankle": BODY % "ankle", "foot": "meshes/a/a_daedric_boots_f.nif",
         "hand": BODY % "ankle"}

# Diagnostic colours: the right side warm, the left side cool, the trunk
# neutral-bright. Each slot differs from its neighbours in hue.
PAINT = {"head": (245, 245, 245), "chest": (255, 215, 0),
         "groin": (230, 0, 200),
         "clavicle_r": (255, 120, 0), "upperarm_r": (220, 20, 20),
         "forearm_r": (255, 150, 150), "hand_r": (140, 0, 0),
         "upperleg_r": (255, 90, 0), "knee_r": (255, 190, 120),
         "ankle_r": (200, 60, 0), "foot_r": (120, 40, 0),
         "clavicle_l": (0, 200, 255), "upperarm_l": (30, 60, 255),
         "forearm_l": (140, 170, 255), "hand_l": (0, 0, 130),
         "upperleg_l": (0, 170, 120), "knee_l": (130, 255, 200),
         "ankle_l": (0, 120, 160), "foot_l": (0, 60, 60)}


def base(name):
    return re.sub(r"(_\d+)+$", "", name)


def swing(a, b):
    """The smallest rotation carrying direction a onto direction b."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v, c = np.cross(a, b), float(a @ b)
    if c < -0.999999:
        axis = np.cross(a, [1.0, 0, 0])
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, [0, 1.0, 0])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1.0 + c)


def read_model(path):
    model = Gltf(path)
    skin = model.json["skins"][0]
    joints = skin["joints"]
    names = [model.json["nodes"][n].get("name", f"node{n}") for n in joints]
    ibm = model.accessor(skin["inverseBindMatrices"]).reshape(-1, 4, 4)
    ibm = ibm.transpose(0, 2, 1)                    # column-major on disk
    heads = np.array([np.linalg.inv(m)[:3, 3] for m in ibm])
    where = {n: i for i, n in enumerate(joints)}
    parent = {}
    for i, node in enumerate(model.json["nodes"]):
        for kid in node.get("children", []):
            if kid in where and i in where:
                parent[where[kid]] = where[i]
    seen, V, U, T, J, W, P = set(), [], [], [], [], [], []
    at = 0
    for mesh in model.json.get("meshes", []):
        for prim in mesh.get("primitives", []):
            a = prim.get("attributes", {})
            if "JOINTS_0" not in a or "POSITION" not in a:
                continue
            v = model.accessor(a["POSITION"]).astype(np.float64)
            mark = (len(v), tuple(np.round(v[0], 5)), tuple(np.round(v[-1], 5)))
            if mark in seen:
                continue
            seen.add(mark)
            V.append(v)
            U.append(model.accessor(a["TEXCOORD_0"]).astype(np.float64)
                     if "TEXCOORD_0" in a else np.zeros((len(v), 2)))
            T.append(model.accessor(prim["indices"]).ravel()
                     .astype(np.int64).reshape(-1, 3) + at)
            J.append(model.accessor(a["JOINTS_0"]).astype(np.int64))
            W.append(model.accessor(a["WEIGHTS_0"]).astype(np.float64))
            P.append(np.full(len(v), len(P)))
            at += len(v)
    w = np.vstack(W)
    w /= np.maximum(w.sum(1, keepdims=True), 1e-9)
    return {"names": names, "heads": heads, "parent": parent,
            "verts": np.vstack(V), "uv": np.vstack(U), "tris": np.vstack(T),
            "joints": np.vstack(J), "weights": w, "prim": np.concatenate(P)}


def pose(m, frames):
    """Every vertex of the model, in game units, in Morrowind's rest pose."""
    names, heads, parent = m["names"], m["heads"], m["parent"]
    by_base = {base(n): i for i, n in enumerate(names)}
    mw = {k: frames[k][1] for k in frames}
    g = lambda i: AXES @ heads[i]                     # noqa: E731

    tall_model = (g(by_base["head"]) - g(by_base["foot_l"]))[2]
    tall_game = mw["Bip01 Head"][2] - mw["Bip01 L Foot"][2]
    scale = tall_game / tall_model

    order, done = [], set()

    def visit(i):
        if i in done:
            return
        if i in parent:
            visit(parent[i])
        done.add(i)
        order.append(i)
    for i in range(len(names)):
        visit(i)

    rot = np.zeros((len(names), 3, 3))
    anchor = np.zeros((len(names), 3))     # where the effective head goes
    origin = np.zeros((len(names), 3))     # the effective head, model side
    pelvis = by_base["pelvis"]
    for i in order:
        b = base(names[i])
        p = parent.get(i)
        prot = rot[p] if p is not None and p in done else np.eye(3)
        if b in TWIN:
            r = prot
            if b in AIM:
                kid = by_base[AIM[b]]
                want = mw[AIM_MW.get(AIM[b], TWIN.get(AIM[b], ""))] \
                    - mw[TWIN[b]]
                r = swing(prot @ (g(kid) - g(i)), want) @ prot
            rot[i], anchor[i], origin[i] = r, mw[TWIN[b]], g(i)
        elif p is not None:
            rot[i], anchor[i], origin[i] = rot[p], anchor[p], origin[p]
        else:
            rot[i], anchor[i] = np.eye(3), mw["Bip01 Pelvis"]
            origin[i] = g(pelvis)

    v = m["verts"] @ AXES.T
    out = np.zeros_like(v)
    for k in range(m["joints"].shape[1]):
        j, w = m["joints"][:, k], m["weights"][:, k:k + 1]
        local = scale * (v - origin[j])
        out += w * (anchor[j] + np.einsum("nij,nj->ni", rot[j], local))

    ratios = {}
    for b, kid in (("upperarm_r", "lowerarm_r"), ("lowerarm_r", "hand_r"),
                   ("thigh_r", "calf_r"), ("calf_r", "foot_r")):
        model_len = np.linalg.norm(g(by_base[kid]) - g(by_base[b])) * scale
        game_len = np.linalg.norm(mw[TWIN[kid]] - mw[TWIN[b]])
        ratios[b] = model_len / game_len
    return out, scale, ratios


def label(m, posed, knee_fraction=0.5):
    names, parent = m["names"], m["parent"]
    cache = {}

    def resolve(i):
        if i not in cache:
            j, steps = i, 0
            while j is not None and steps < 64:
                slot, side = slot_of(names[j])
                if slot:
                    slot = FOLD.get(slot, slot)
                    cache[i] = f"{slot}_{side}" if slot in SIDED else slot
                    break
                j, steps = parent.get(j), steps + 1
            else:
                cache[i] = None
        return cache.get(i)

    dom = m["joints"][np.arange(len(m["joints"])),
                      np.argmax(m["weights"], axis=1)]
    lab = [resolve(int(j)) for j in dom]
    pieces = defaultdict(list)
    for tri in m["tris"]:
        votes = defaultdict(int)
        for c in tri:
            if lab[c]:
                votes[lab[c]] += 1
        if votes:
            pieces[max(votes.items(), key=lambda kv: kv[1])[0]].append(tri)
    for side in ("l", "r"):
        key = f"ankle_{side}"
        if key in pieces:
            got = np.array(pieces[key])
            z = posed[got].mean(axis=1)[:, 2]
            cut = z.min() + (z.max() - z.min()) * knee_fraction
            pieces[f"knee_{side}"] = got[z > cut]
            pieces[key] = got[z <= cut]
    return {k: np.array(v) for k, v in pieces.items() if len(v)}


def grow(tris_piece, all_tris, rings=1):
    have = set(np.unique(tris_piece).tolist())
    got = {tuple(t) for t in tris_piece.tolist()}
    for _ in range(rings):
        touch = np.isin(all_tris, list(have)).any(axis=1)
        new = [tuple(t) for t in all_tris[touch].tolist() if tuple(t) not in got]
        got.update(new)
        have.update(i for t in new for i in t)
    return np.array(sorted(got))


def chain(blob):
    """The donor's first shape: rotation, translation and scale from the root."""
    tree = nodes(blob)
    kinds = blocks(blob)
    target = next(i for i, (k, _a) in enumerate(kinds) if k == "NiTriShape")
    up = {k: i for i, n in tree.items() for k in n["kids"]}
    path, i = [], target
    while i in up:
        i = up[i]
        path.append(i)
    r, p, s = np.eye(3), np.zeros(3), 1.0
    for i in reversed(path):
        n = tree[i]
        p = p + s * (r @ n["t"])
        r = r @ n["r"]
        s *= n["s"]
    sr, sp, ss = shape(blob)
    return r @ sr, p + s * (r @ sp), s * ss


def emissive(blob):
    """Make the donor's material light itself, so a dark room hides nothing."""
    at = blob.find(b"NiMaterialProperty")
    if at < 0:
        raise SystemExit("donor has no NiMaterialProperty")
    p = at + len(b"NiMaterialProperty")
    length, = struct.unpack_from("<i", blob, p)
    p += 4 + length + 4 + 4 + 2                 # name, extra, controller, flags
    colours = struct.pack("<12f", *([1.0] * 12))  # ambient diffuse specular emit
    return blob[:p] + colours + blob[p + 48:]


def paint_texture(path, rgb, size=256, cells=8):
    """A slot colour with a grid of F glyphs, which read backwards if mirrored."""
    from PIL import Image, ImageDraw
    from dds import write_bgra
    img = Image.new("RGBA", (size, size), tuple(rgb) + (255,))
    pen = ImageDraw.Draw(img)
    step = size // cells
    dark = (0, 0, 0, 255) if sum(rgb) > 300 else (255, 255, 255, 255)
    for cy in range(cells):
        for cx in range(cells):
            x, y = cx * step + step // 4, cy * step + step // 6
            w, h = step // 2, step * 2 // 3
            pen.rectangle([x, y, x + w // 4, y + h], fill=dark)
            pen.rectangle([x, y, x + w, y + h // 5], fill=dark)
            pen.rectangle([x, y + h * 2 // 5, x + w * 3 // 4, y + h * 3 // 5],
                          fill=dark)
    write_bgra(path, np.asarray(img))


def render(pieces, path, size=520):
    """Front, side and back, orthographic, flat shaded, z-buffered."""
    from PIL import Image, ImageDraw
    every = np.vstack([v for v, _t, _c in pieces])
    lo, hi = every.min(0), every.max(0)
    centre, span = (lo + hi) / 2, float((hi - lo).max()) * 1.06
    views = (("front", lambda v: (-v[:, 0], v[:, 2], v[:, 1]), np.array([0, 1.0, 0])),
             ("side", lambda v: (v[:, 1], v[:, 2], v[:, 0]), np.array([1.0, 0, 0])),
             ("back", lambda v: (v[:, 0], v[:, 2], -v[:, 1]), np.array([0, -1.0, 0])))
    canvas = np.zeros((size, size * 3, 3), np.uint8) + 36
    for panel, (name, proj, look) in enumerate(views):
        zbuf = np.full((size, size), -np.inf)
        img = canvas[:, panel * size:(panel + 1) * size]
        for verts, tris, rgb in pieces:
            x, y, d = proj(verts - centre)
            px = (x / span + 0.5) * size
            py = (0.5 - y / span) * size
            nrm = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]],
                           verts[tris[:, 2]] - verts[tris[:, 0]])
            ln = np.linalg.norm(nrm, axis=1)
            for t, n, l in zip(tris, nrm, ln):
                if l < 1e-12:
                    continue
                xs, ys, ds = px[t], py[t], d[t]
                x0, x1 = int(max(xs.min(), 0)), int(min(xs.max() + 1, size))
                y0, y1 = int(max(ys.min(), 0)), int(min(ys.max() + 1, size))
                if x0 >= x1 or y0 >= y1:
                    continue
                gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5,
                                     np.arange(y0, y1) + 0.5)
                den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + \
                    (xs[2] - xs[1]) * (ys[0] - ys[2])
                if abs(den) < 1e-12:
                    continue
                a = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
                b = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
                c = 1 - a - b
                inside = (a >= 0) & (b >= 0) & (c >= 0)
                depth = a * ds[0] + b * ds[1] + c * ds[2]
                sub = zbuf[y0:y1, x0:x1]
                win = inside & (depth > sub)
                if not win.any():
                    continue
                sub[win] = depth[win]
                shade = 0.35 + 0.65 * abs(float(n @ look)) / l
                img[y0:y1, x0:x1][win] = np.clip(np.array(rgb) * shade, 0, 255)
    out = Image.fromarray(canvas)
    pen = ImageDraw.Draw(out)
    for panel, (name, _p, _l) in enumerate(views):
        pen.text((panel * size + 8, 6), name, fill=(170, 170, 170))
    out.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model")
    ap.add_argument("--out", default=os.path.join(ROOT, "tools", "build",
                                                  "armour-dev"))
    ap.add_argument("--texture", default="zenar_body.dds")
    ap.add_argument("--helm-texture", default="zenar_helm.dds")
    ap.add_argument("--paint", action="store_true",
                    help="diagnostic colours, self-lit, left and right apart")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    with open(_resolve(SKELETON), "rb") as f:
        frames = world(f.read())
    m = read_model(args.model)
    posed, scale, ratios = pose(m, frames)
    print(f"model: {len(m['verts'])} vertices, {len(m['tris'])} triangles; "
          f"scale {scale:.4f}")
    print("limb length, model over game: " +
          ", ".join(f"{k} {v:.2f}" for k, v in ratios.items()))
    pieces = label(m, posed)
    # One shape per file, so one sheet per piece. The helmet is its own
    # primitive with its own sheet; where its collar was cut into the chest by
    # the neck bones, it goes back on the helmet.
    counts = np.bincount(m["prim"])
    body = int(np.argmax(counts))
    if "head" in pieces:
        for key in list(pieces):
            if key == "head":
                continue
            odd = m["prim"][pieces[key][:, 0]] != body
            if odd.any():
                pieces["head"] = np.vstack([pieces["head"], pieces[key][odd]])
                pieces[key] = pieces[key][~odd]

    mesh_dir = os.path.join(args.out, "Meshes", "zenar")
    tex_dir = os.path.join(args.out, "Textures")
    if args.write:
        os.makedirs(mesh_dir, exist_ok=True)
        os.makedirs(tex_dir, exist_ok=True)
    preview, worst = [], 0.0
    for key in sorted(pieces):
        slot, side = (key[:-2], key[-1]) if key[-2:] in ("_l", "_r") else (key, "")
        if slot not in DONOR or side == "l":
            continue
        node = f"Right {NODE[slot]}" if side else NODE[slot]
        tris = grow(pieces[key], m["tris"])
        used = np.unique(tris)
        remap = np.full(len(m["verts"]), -1)
        remap[used] = np.arange(len(used))
        tris = remap[tris]
        target = posed[used]
        r, p, s = frames[node]
        local = ((target - p) @ r) / s

        with open(_resolve(DONOR[slot]), "rb") as f:
            donor = f.read()
        cr, cp, cs = chain(donor)
        in_shape = ((local - cp) @ cr) / cs

        faces = np.vstack([tris, tris[:, ::-1] + len(used)])
        verts2 = np.vstack([in_shape, in_shape])
        uv2 = np.vstack([m["uv"][used]] * 2)
        sides = ("r", "l") if side else ("",)
        for sd in sides:
            name = f"{slot}_l" if sd == "l" else slot
            blob = donor
            tex = args.texture if m["prim"][used[0]] == body else args.helm_texture
            if args.paint:
                tex = f"zenar_dbg_{name}.dds"
                blob = emissive(blob)
                if args.write:
                    paint_texture(os.path.join(tex_dir, tex),
                                  PAINT[f"{slot}_{sd}" if sd else slot])
            blob, _was = retexture(blob, tex)
            written = build(blob, verts2, uv2, faces)
            back, _uv, _t = parse_trishape(written)
            br, bp, bs = chain(written)
            again = bp + bs * (back[:len(used)] @ br.T)
            err = float(np.abs(again - local).max())
            worst = max(worst, err)
            if err > 1e-3:
                raise SystemExit(f"{name}: read back {err:.4f} off")
            if args.write:
                with open(os.path.join(mesh_dir, name + ".nif"), "wb") as f:
                    f.write(written)
            # as the engine assembles it
            nr, npos, ns = frames[node.replace("Right", "Left") if sd == "l" else node]
            flip = MIRROR if sd == "l" else np.eye(3)
            placed = npos + ns * ((local @ flip.T) @ nr.T)
            colour = PAINT[f"{slot}_{sd}" if sd else slot]
            preview.append((placed, tris, colour))
        print(f"  {key:<12}{node:<17}{len(used):>6} verts  "
              f"z {target[:, 2].min():6.1f} .. {target[:, 2].max():6.1f}")
    print(f"read-back error at most {worst:.2e}")
    os.makedirs(os.path.join(ROOT, "tools", "reports"), exist_ok=True)
    print(render(preview, os.path.join(ROOT, "tools", "reports",
                                       "suit-preview.png")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
