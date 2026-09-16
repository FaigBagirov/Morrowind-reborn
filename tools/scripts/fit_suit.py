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

# **Rig profiles.** Each names, in the model's own bone names: the bones with a
# Morrowind twin, which of those swing toward which child (model child, game
# child), the two bones that measure height, and which slot a bone feeds.
# Picked by `rig_of` from the names in the file.


def _limbs(model_names, twin, aim):
    """Fill twin and aim for both sides from a per-side name table."""
    for s, S in (("l", "L"), ("r", "R")):
        n = {k: v.format(s=s, S=S) for k, v in model_names.items()}
        twin.update({n["clavicle"]: f"Bip01 {S} Clavicle",
                     n["upperarm"]: f"Bip01 {S} UpperArm",
                     n["forearm"]: f"Bip01 {S} Forearm",
                     n["hand"]: f"Bip01 {S} Hand",
                     n["thigh"]: f"Bip01 {S} Thigh",
                     n["calf"]: f"Bip01 {S} Calf",
                     n["foot"]: f"Bip01 {S} Foot"})
        aim.update({n["clavicle"]: (n["upperarm"], f"Bip01 {S} UpperArm"),
                    n["upperarm"]: (n["forearm"], f"Bip01 {S} Forearm"),
                    n["forearm"]: (n["hand"], f"Bip01 {S} Hand"),
                    n["hand"]: (n["finger"], f"Bip01 {S} Finger1"),
                    n["thigh"]: (n["calf"], f"Bip01 {S} Calf"),
                    n["calf"]: (n["foot"], f"Bip01 {S} Foot")})


def _unreal_slot(name):
    slot, side = slot_of(name)
    return FOLD.get(slot, slot), side


_VALVE_SLOTS = (("head", "head"), ("neck", "chest"), ("pectoral", "chest"),
                ("latt", "chest"), ("spine", "chest"), ("pelvis", "groin"),
                ("clavicle", "clavicle"), ("trapezius", "clavicle"),
                ("shoulder", "clavicle"), ("bicep", "upperarm"),
                ("upperarm", "upperarm"), ("elbow", "forearm"),
                ("forearm", "forearm"), ("ulna", "forearm"),
                ("wrist", "forearm"), ("hand", "hand"), ("finger", "hand"),
                ("attachment", "hand"), ("hip", "upperleg"),
                ("sartorius", "upperleg"), ("quadricep", "upperleg"),
                ("thigh", "upperleg"), ("knee", "knee"), ("calf", "ankle"),
                ("foot", "foot"), ("toe", "foot"))


def _valve_base(name):
    return re.sub(r"^(ValveBiped\.)?(Bip01_)?", "", name)


def _valve_slot(name):
    s = _valve_base(name)
    side = ("l" if re.match(r"L_", s) or s.endswith("LH") else
            "r" if re.match(r"R_", s) or s.endswith("RH") else "")
    low = s.lower()
    for key, slot in _VALVE_SLOTS:
        if key in low:
            return slot, side
    return None, side


RIGS = {
    "unreal": {"base": lambda n: base_name(n), "slot": _unreal_slot,
               # Weights need spine_01 told from spine_05, which base_name
               # folds together; only the two trailing node numbers go.
               "skin_base": lambda n: re.sub(r"_\d+_\d+$", "", n),
               "skin_map": {"pelvis": "Bip01 Pelvis", "spine_01": "Bip01 Spine",
                            "spine_02": "Bip01 Spine1", "spine_03": "Bip01 Spine1",
                            "spine_04": "Bip01 Spine2", "spine_05": "Bip01 Spine2",
                            "neck_01": "Bip01 Neck", "neck_02": "Bip01 Neck"},
               "top": "head", "foot": "foot_l", "root": "pelvis",
               "twin": {"pelvis": "Bip01 Pelvis", "spine_01": "Bip01 Spine",
                        "spine_03": "Bip01 Spine1", "spine_05": "Bip01 Spine2",
                        "neck_01": "Bip01 Neck", "head": "Bip01 Head"},
               "aim": {}, "limbs": {
                   "clavicle": "clavicle_{s}", "upperarm": "upperarm_{s}",
                   "forearm": "lowerarm_{s}", "hand": "hand_{s}",
                   "finger": "middle_01_{s}", "thigh": "thigh_{s}",
                   "calf": "calf_{s}", "foot": "foot_{s}"}},
    "valve": {"base": _valve_base, "slot": _valve_slot,
              "skin_map": {"Pelvis": "Bip01 Pelvis", "Spine": "Bip01 Spine",
                           "Spine1": "Bip01 Spine1", "Spine2": "Bip01 Spine2",
                           "Spine4": "Bip01 Spine2", "Neck1": "Bip01 Neck"},
              "top": "Head1", "foot": "L_Foot", "root": "Pelvis",
              # **The trunk moves as one piece.** Snapping each vertebra to
              # Morrowind's bent the chest: this spine leans back where the
              # game's leans forward, and Spine2 alone moved 7.7 units forward
              # and 7.3 up, which also stood the collar above the helmet. So
              # pelvis-to-neck is swung and scaled onto the game's once, and
              # every trunk bone shares that.
              "trunk": {"bones": {"Spine", "Spine1", "Spine2", "Spine4",
                                  "Neck1"},
                        "from": ("Pelvis", "Bip01 Pelvis"),
                        "to": ("Neck1", "Bip01 Neck")},
              "twin": {"Pelvis": "Bip01 Pelvis", "Head1": "Bip01 Head"},
              "aim": {}, "limbs": {
                  "clavicle": "{S}_Clavicle", "upperarm": "{S}_UpperArm",
                  "forearm": "{S}_Forearm", "hand": "{S}_Hand",
                  "finger": "{S}_Finger1", "thigh": "{S}_Thigh",
                  "calf": "{S}_Calf", "foot": "{S}_Foot"}},
}


def rig_of(names):
    kind = "valve" if any(n.startswith("ValveBiped.") for n in names) \
        else "unreal"
    rig = RIGS[kind]
    if not rig["aim"]:
        _limbs(rig["limbs"], rig["twin"], rig["aim"])
    return kind, rig

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


def base_name(name):
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
    """Every skinned primitive of every skin, joints merged by name.

    A model may carry one skeleton per body region, each a copy with the same
    bone names (the Claymore has five), so joints are identified by name and
    each primitive's joint indices go through its own skin's table.
    """
    model = Gltf(path)
    js = model.json
    nodes_js = js["nodes"]
    label_of = lambda n: nodes_js[n].get("name", f"node{n}")  # noqa: E731
    names, heads, index, tables = [], [], {}, []
    for skin in js.get("skins", []):
        ibm = model.accessor(skin["inverseBindMatrices"]).reshape(-1, 4, 4)
        ibm = ibm.transpose(0, 2, 1)                # column-major on disk
        table = []
        for jn, mat in zip(skin["joints"], ibm):
            nm = label_of(jn)
            if nm not in index:
                index[nm] = len(names)
                names.append(nm)
                heads.append(np.linalg.inv(mat)[:3, 3])
            table.append(index[nm])
        tables.append(np.array(table))
    up = {k: i for i, n in enumerate(nodes_js) for k in n.get("children", [])}
    parent = {}
    for skin in js.get("skins", []):
        for jn in skin["joints"]:
            p = up.get(jn)
            while p is not None and label_of(p) not in index:
                p = up.get(p)
            if p is not None and index[label_of(p)] != index[label_of(jn)]:
                parent.setdefault(index[label_of(jn)], index[label_of(p)])

    materials, items, rough_maps = {}, [], []

    def material(prim):
        mi = prim.get("material")
        pbr = js["materials"][mi].get("pbrMetallicRoughness", {}) \
            if mi is not None else {}
        factor = tuple(round(c, 4) for c in pbr.get("baseColorFactor",
                                                     [1, 1, 1, 1]))
        tex = pbr.get("baseColorTexture")
        img = js["textures"][tex["index"]].get("source") if tex else None
        key = (img, factor)
        if key not in materials:
            materials[key] = len(items)
            items.append(key)
            mr = pbr.get("metallicRoughnessTexture")
            rough_maps.append(js["textures"][mr["index"]].get("source")
                              if mr else None)
        return materials[key]

    seen, V, U, T, J, W, M = set(), [], [], [], [], [], []
    at = 0
    for node in nodes_js:
        if "mesh" not in node or node.get("skin") is None:
            continue
        table = tables[node["skin"]]
        for prim in js["meshes"][node["mesh"]]["primitives"]:
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
            J.append(table[model.accessor(a["JOINTS_0"]).astype(np.int64)])
            W.append(model.accessor(a["WEIGHTS_0"]).astype(np.float64))
            M.append(np.full(len(v), material(prim)))
            at += len(v)
    w = np.vstack(W)
    w /= np.maximum(w.sum(1, keepdims=True), 1e-9)
    kind, rig = rig_of(names)
    return {"names": names, "heads": np.array(heads), "parent": parent,
            "verts": np.vstack(V), "uv": np.vstack(U), "tris": np.vstack(T),
            "joints": np.vstack(J), "weights": w, "mat": np.concatenate(M),
            "items": items, "mr": rough_maps, "gltf": model, "rig": rig, "kind": kind}


def pose(m, frames):
    """Every vertex of the model, in game units, in Morrowind's rest pose."""
    names, heads, parent, rig = m["names"], m["heads"], m["parent"], m["rig"]
    by_base = {rig["base"](n): i for i, n in enumerate(names)}
    mw = {k: frames[k][1] for k in frames}
    g = lambda i: AXES @ heads[i]                     # noqa: E731

    tall_model = (g(by_base[rig["top"]]) - g(by_base[rig["foot"]]))[2]
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

    twin, aim = rig["twin"], rig["aim"]
    rot = np.zeros((len(names), 3, 3))
    anchor = np.zeros((len(names), 3))     # where the effective head goes
    origin = np.zeros((len(names), 3))     # the effective head, model side
    root = by_base[rig["root"]]
    size = np.ones(len(names))
    trunk = rig.get("trunk")
    if trunk:
        (fb, fm), (tb, tm) = trunk["from"], trunk["to"]
        model_span = g(by_base[tb]) - g(by_base[fb])
        game_span = mw[tm] - mw[fm]
        trunk_rot = swing(model_span, game_span)
        trunk_size = np.linalg.norm(game_span) / (scale * np.linalg.norm(model_span))
    for i in order:
        b = rig["base"](names[i])
        p = parent.get(i)
        prot = rot[p] if p is not None else np.eye(3)
        if trunk and b in trunk["bones"]:
            rot[i], anchor[i], origin[i] = trunk_rot, mw[trunk["from"][1]],                 g(by_base[trunk["from"][0]])
            size[i] = trunk_size
        elif b in twin:
            r = prot
            if b in aim and aim[b][0] in by_base:
                kid = by_base[aim[b][0]]
                want = mw[aim[b][1]] - mw[twin[b]]
                r = swing(prot @ (g(kid) - g(i)), want) @ prot
            rot[i], anchor[i], origin[i] = r, mw[twin[b]], g(i)
        elif p is not None:
            rot[i], anchor[i], origin[i] = rot[p], anchor[p], origin[p]
            size[i] = size[p]
        else:
            rot[i], anchor[i] = np.eye(3), mw["Bip01 Pelvis"]
            origin[i] = g(root)

    # Second pass for helper bones (Valve's Bicep, Ulna, Wrist...). They hang
    # off the clavicle or the upper arm rather than in the chain, so the
    # hierarchy never swings them the way their slot swings: left alone they
    # stay in the T-pose and stick out sideways. Each follows the main bone of
    # the slot it feeds, and its own children follow it.
    main_bone = {"clavicle": "clavicle", "upperarm": "upperarm",
                 "forearm": "forearm", "hand": "hand", "upperleg": "thigh",
                 "knee": "calf", "ankle": "calf", "foot": "foot"}
    for i in order:
        b = rig["base"](names[i])
        if b in twin or (trunk and b in trunk["bones"]):
            continue
        slot, side = rig["slot"](names[i])
        f = None
        if slot in main_bone and side:
            want = rig["limbs"][main_bone[slot]].format(s=side, S=side.upper())
            f = by_base.get(want)
        if f is None:
            f = parent.get(i)
        if f is not None:
            rot[i], anchor[i], origin[i] = rot[f], anchor[f], origin[f]
            size[i] = size[f]

    # **Blend only bones that turn alike.** A vertex split between a bone
    # that swings down with the arm and one that does not (Valve's bicep
    # against the clavicle, ~80 degrees apart) lands halfway between the two
    # and draws a spike out of the shoulder. Weights on bones turned more
    # than 25 degrees away from the vertex's strongest bone are dropped.
    v = m["verts"] @ AXES.T
    out = np.zeros_like(v)
    joints, weights = m["joints"], m["weights"].copy()
    strongest = joints[np.arange(len(joints)), weights.argmax(1)]
    for k in range(joints.shape[1]):
        turn = np.einsum("nij,nij->n", rot[strongest], rot[joints[:, k]])
        weights[(turn - 1) / 2 < np.cos(np.radians(25)), k] = 0.0
    weights /= np.maximum(weights.sum(1, keepdims=True), 1e-9)
    for k in range(joints.shape[1]):
        j, w = joints[:, k], weights[:, k:k + 1]
        local = scale * size[j][:, None] * (v - origin[j])
        out += w * (anchor[j] + np.einsum("nij,nj->ni", rot[j], local))

    ratios = {}
    for b, (kid, mwkid) in aim.items():
        if kid in by_base and kid in twin and b in by_base:
            model_len = np.linalg.norm(g(by_base[kid]) - g(by_base[b])) * scale
            ratios[b] = model_len / np.linalg.norm(mw[mwkid] - mw[twin[b]])
    return out, scale, ratios


SKINNED = ("chest", "groin")


def tarnish(pic):
    """Old, darkened silver (Faig, 2026-09-16, for the Zenar suit).

    Blue becomes grey metal of the same lightness - painted over rather than
    cut, so the chest keeps its plates. Everything darkens with a gamma, which
    sinks the mid-grey grooves on legs and back further than the highlights;
    silver gets a faint warm tarnish, gold a further darkening.
    """
    from PIL import Image
    a = np.asarray(pic).astype(np.float64) / 255.0
    rgb = a[..., :3]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    blue = (b > r + 0.04) & (sat > 0.10)
    gold = (r > b + 0.12) & (g > b + 0.05) & (sat > 0.20) & ~blue
    # dark navy by its own lightness went black; steel-grey instead
    rgb[blue] = (0.45 + 0.5 * lum[blue])[:, None]
    rgb = np.power(rgb, 1.35) * 0.45        # Faig: darker, then a little lighter
    rgb[~gold] *= np.array([1.0, 0.975, 0.93])
    # Faig: gold read dark and pale - more saturated, not darkened further
    gl = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])[gold][:, None]
    rgb[gold] = (gl + (rgb[gold] - gl) * 1.9) * 1.25
    a[..., :3] = np.clip(rgb, 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8), "RGBA")


def skin_bone(m, i):
    """The Morrowind bone a model joint weighs on, within the cuirass donor's
    skeleton (Pelvis to the upper arms)."""
    rig, names, parent = m["rig"], m["names"], m["parent"]
    j, steps = i, 0
    while j is not None and steps < 64:
        b = rig.get("skin_base", rig["base"])(names[j])
        if b in rig["skin_map"]:
            return rig["skin_map"][b]
        slot, side = rig["slot"](names[j])
        S = side.upper() if side else ""
        if slot == "clavicle" and S:
            return f"Bip01 {S} Clavicle"
        if slot in ("upperarm", "forearm", "hand") and S:
            return f"Bip01 {S} UpperArm"
        if slot == "head":
            return "Bip01 Neck"
        if slot in ("groin", "upperleg", "knee", "ankle", "foot"):
            return "Bip01 Pelvis"
        j, steps = parent.get(j), steps + 1
    return "Bip01 Spine2"


def skin_weights(m, used, keep=3):
    """Per used vertex, up to `keep` (bone, weight) pairs, normalised."""
    cache = {}
    out = []
    for v in used:
        acc = defaultdict(float)
        for j, w in zip(m["joints"][v], m["weights"][v]):
            if w > 0:
                if j not in cache:
                    cache[j] = skin_bone(m, int(j))
                acc[cache[j]] += float(w)
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:keep]
        total = sum(w for _b, w in top) or 1.0
        out.append([(b, w / total) for b, w in top if w / total > 0.01])
    return out


def label(m, posed, knee_fraction=0.5):
    names, parent = m["names"], m["parent"]
    cache = {}

    def resolve(i):
        if i not in cache:
            j, steps = i, 0
            while j is not None and steps < 64:
                slot, side = m["rig"]["slot"](names[j])
                if slot:
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
    ap.add_argument("--set", default="zenar",
                    help="mesh folder and texture prefix; bodyparts.SETS says "
                         "which armour records it replaces")
    ap.add_argument("--atlas-size", type=int, default=2048)
    ap.add_argument("--tone", choices=["none", "tarnished"], default="none",
                    help="recolour the textures before the atlas")
    ap.add_argument("--flat-colour", default="",
                    help="r,g,b for flat black materials (Wolf's body)")
    ap.add_argument("--skin", action="store_true",
                    help="chest and groin as skinned meshes that bend with "
                         "the spine, instead of rigid pieces")
    ap.add_argument("--gain", type=float, default=2.0,
                    help="specular brightness; the engine has no reflections")
    ap.add_argument("--drop-flat-dark", default="",
                    help="comma-separated pieces whose dark flat-colour "
                         "(untextured) material is cut; textures untouched")
    ap.add_argument("--drop-blue", default="",
                    help="comma-separated pieces whose dark blue texels are cut")
    ap.add_argument("--drop", default="",
                    help="regex of bone names whose geometry is left out")
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
    print(f"rig: {m['kind']}, {len(m['names'])} joints, "
          f"{len(m['items'])} materials")
    if args.drop:
        # Parts Faig does not want, cut by the bones that carry them - a cloth
        # tabard hangs on its own dynamic bones, so it comes away whole.
        pattern = re.compile(args.drop, re.I)
        dom = m["joints"][np.arange(len(m["joints"])), m["weights"].argmax(1)]
        gone = np.array([bool(pattern.search(n)) for n in m["names"]])[dom]
        keep = gone[m["tris"]].sum(1) < 2
        print(f"dropped {int((~keep).sum())} triangles on bones matching {args.drop!r}")
        m["tris"] = m["tris"][keep]
    pieces = label(m, posed)
    if args.drop_blue or args.drop_flat_dark:
        # Faig: nothing blue left around the waist. The cloth bones took the
        # long tabard; what stays is painted on the body sheet, so it goes by
        # the colour of the texel each triangle sits on.
        from model_textures import images as _imgs
        sheets = _imgs(m["gltf"])
        cut = 0
        flat_only = set(filter(None, args.drop_flat_dark.split(",")))
        for key in filter(None, (args.drop_blue + "," + args.drop_flat_dark).split(",")):
            if key not in pieces:
                continue
            keep = []
            for tri in pieces[key]:
                u, v = m["uv"][tri].mean(0)
                img, factor = m["items"][m["mat"][tri[0]]]
                if img is not None and key in flat_only:
                    keep.append(tri)
                    continue
                if img is None:
                    # a flat colour: Wolf's joint rings are its black body
                    # material, seen as black circles on the ankles
                    r, g, b = (int(c * 255) for c in factor[:3])
                    if b + 10 >= r and r + g + b < 330:
                        cut += 1
                    else:
                        keep.append(tri)
                    continue
                pic = sheets[img]
                x = min(int(u % 1.0 * pic.width), pic.width - 1)
                y = min(int(v % 1.0 * pic.height), pic.height - 1)
                r, g, b = pic.getpixel((x, y))[:3]
                if b + 10 >= r and r + g + b < 330:
                    cut += 1
                else:
                    keep.append(tri)
            pieces[key] = np.array(keep)
        print(f"dropped {cut} dark triangles from "
              f"{args.drop_blue} {args.drop_flat_dark}")

    mesh_dir = os.path.join(args.out, "Meshes", args.set)
    tex_dir = os.path.join(args.out, "Textures")
    if args.write:
        os.makedirs(mesh_dir, exist_ok=True)
        os.makedirs(tex_dir, exist_ok=True)

    # One texture per bodypart file, so every material goes on one atlas.
    from atlas import build_atlas, remap_uv
    from model_textures import images as gltf_images
    sheets = gltf_images(m["gltf"])
    items = []
    flat = tuple(int(c) for c in args.flat_colour.split(","))         if args.flat_colour else None
    for img, factor in m["items"]:
        if img is None:
            colour = tuple(int(round(c * 255)) for c in factor[:3])
            if flat and sum(colour) < 60:
                # Faig: Wolf's black body material shows in the running
                # cracks and as black hands; grey-blue like its plates
                colour = flat
            items.append(colour)
            continue
        pic = sheets[img].convert("RGBA")
        if args.tone == "tarnished":
            pic = tarnish(pic)
        if factor[:3] != (1, 1, 1):
            arr = np.asarray(pic).astype(np.float64)
            arr[..., :3] *= np.array(factor[:3])
            from PIL import Image
            pic = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        items.append(pic)
    sheet, rects = build_atlas(items, args.atlas_size)
    uv_atlas = np.zeros_like(m["uv"])
    for k, rect in enumerate(rects):
        pick = m["mat"] == k
        uv_atlas[pick] = remap_uv(m["uv"][pick], rect)
    atlas_name = f"{args.set}_atlas.dds"
    if args.write and not args.paint:
        from dds import write_dxt
        write_dxt(os.path.join(tex_dir, atlas_name), np.asarray(sheet), "dxt1")
        # Shine: a specular atlas in the same layout, which OpenMW picks up
        # as `<texture>_spec.dds`. Built from each material's own
        # metallic-roughness map (spec_maps.py); flat colours get a dim sheen.
        from PIL import Image as _Image
        from spec_maps import spec_map
        spec_items = []
        for item, mr in zip(items, m["mr"]):
            if isinstance(item, tuple):
                spec_items.append(tuple(min(255, int(c * 0.35 * args.gain))
                                        for c in item[:3]) + (20,))
                continue
            rough = sheets[mr] if mr is not None else                 _Image.new("RGB", (4, 4), (0, 128, 0))
            spec_items.append(_Image.fromarray(spec_map(item, rough, args.gain),
                                               "RGBA"))
        spec_sheet, _r = build_atlas(spec_items, args.atlas_size)
        write_dxt(os.path.join(tex_dir, f"{args.set}_atlas_spec.dds"),
                  np.asarray(spec_sheet), "dxt5")
    preview, worst = [], 0.0
    env_donor = None
    for key in sorted(pieces):
        slot, side = (key[:-2], key[-1]) if key[-2:] in ("_l", "_r") else (key, "")
        if slot not in DONOR or side == "l":
            continue
        node = f"Right {NODE[slot]}" if side else NODE[slot]
        # arms bend at the elbow between two rigid pieces: a wider overlap
        tris = grow(pieces[key], m["tris"],
                    rings=3 if slot in ("upperarm", "forearm") else 1)
        used = np.unique(tris)
        remap = np.full(len(m["verts"]), -1)
        remap[used] = np.arange(len(used))
        tris = remap[tris]
        target = posed[used]
        if args.skin and slot in SKINNED:
            import skin_write
            with open(_resolve(skin_write.DONOR), "rb") as f:
                donor = f.read()
            tex = f"{args.set}_dbg_{slot}.dds" if args.paint else atlas_name
            if args.paint:
                donor = emissive(donor)
                if args.write:
                    paint_texture(os.path.join(tex_dir, tex), PAINT[slot])
            weights = skin_weights(m, used)
            bones = sorted({b for pairs in weights for b, _w in pairs})
            env = None
            if not args.paint:
                with open(_resolve(skin_write.ENV_DONOR), "rb") as f:
                    env = f.read()
            written, err, wsum = skin_write.write(
                donor, NODE[slot], target, uv_atlas[used], tris, weights,
                bones, frames, tex, env)
            worst = max(worst, err)
            if err > 1e-3 or wsum > 1e-3:
                raise SystemExit(f"{slot}: skinned read-back {err:.4f} off, "
                                 f"weights off by {wsum:.4f}")
            if args.write:
                with open(os.path.join(mesh_dir, slot + ".nif"), "wb") as f:
                    f.write(written)
            preview.append((target, tris, PAINT[slot]))
            print(f"  {key:<12}{'skinned':<17}{len(used):>6} verts  "
                  f"bones {', '.join(b.replace('Bip01 ', '') for b in bones)}")
            continue
        r, p, s = frames[node]
        local = ((target - p) @ r) / s

        with open(_resolve(DONOR[slot]), "rb") as f:
            donor = f.read()
        cr, cp, cs = chain(donor)
        in_shape = ((local - cp) @ cr) / cs

        faces = np.vstack([tris, tris[:, ::-1] + len(used)])
        verts2 = np.vstack([in_shape, in_shape])
        uv2 = np.vstack([uv_atlas[used]] * 2)
        sides = ("r", "l") if side else ("",)
        for sd in sides:
            name = f"{slot}_l" if sd == "l" else slot
            blob = donor
            tex = atlas_name
            if args.paint:
                tex = f"{args.set}_dbg_{name}.dds"
                blob = emissive(blob)
                if args.write:
                    paint_texture(os.path.join(tex_dir, tex),
                                  PAINT[f"{slot}_{sd}" if sd else slot])
            blob, _was = retexture(blob, tex)
            written = build(blob, verts2, uv2, faces)
            if not args.paint:
                # Steel: the ebony cuirass's sphere-map NiTextureEffect, added
                # to every rigid piece (envmap.py, written by gpt-oss-20b to
                # Claude's test). The skinned pieces get theirs from the donor.
                from envmap import add_env_map
                import skin_write
                if env_donor is None:
                    with open(_resolve(skin_write.ENV_DONOR), "rb") as f:
                        env_donor = f.read()
                written = add_env_map(written, env_donor)
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
