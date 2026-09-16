#!/usr/bin/env python3
"""Write a skinned bodypart: our geometry and weights inside a vanilla cuirass.

A rigid chest hung on `Chest` and a rigid groin on `Groin` part at the small of
the back the moment the spine bends - Faig saw it running, black showing
through. Vanilla cuirasses are skinned, so this writes ours the same way.

The donor is `a_bonemold_cuirass_c.nif`: a Bip01 skeleton from Pelvis to the
upper arms and eight skinned shapes named `Tri Chest N`. One shape takes our
geometry, renamed `Tri <slot> 0`; the others are renamed `Tri Unused N`, which
the engine's filter (`attach.cpp`, CopyRigVisitor: name starts with the slot or
"tri " + slot) never copies.

**The rule, measured on the donor, not assumed:** for every bone of a shape,
bone world pose x bone transform is one and the same matrix C (0, 3.31, 98.24
for shape 0). So a vertex lives in C's space and a bone's transform is
inverse(bone world) x C. Ours use the game's own rest pose from base_anim.nif
for the bone worlds, since that skeleton is what drives the part in game.
"""

import struct

import numpy as np

from nif_write import build, normals  # noqa: F401  (build used)
from skeleton import blocks, nodes, world
from skin import read_skin

# The ebony cuirass, not the bonemold one: its "Chest" node carries three
# NiTextureEffect sphere maps ("enviro 01.TGA"), which OpenMW 0.51 applies
# (nifloader.cpp, handleEffect) - vanilla's own steel shine. The node is copied
# with the part because its name matches the slot filter.
DONOR = "meshes/a/a_ebony_cuirass.nif"
# Bones the donor lacks, and who carries their weight instead.
FALLBACK = {"Bip01 L UpperArm": "Bip01 L Clavicle",
            "Bip01 R UpperArm": "Bip01 R Clavicle"}


def _mat(r, t, s):
    m = np.eye(4)
    m[:3, :3] = np.asarray(r, np.float64) * s
    m[:3, 3] = t
    return m


def _start(blob, i):
    kinds = blocks(blob)
    if i >= len(kinds):
        return None
    name, at = kinds[i]
    return at - len(name) - 4


def _end(blob, i):
    nxt = _start(blob, i + 1)
    if nxt is not None:
        return nxt
    roots, = struct.unpack_from("<I", blob, len(blob) - 8)
    return len(blob) - 4 - 4 * roots


def _rename_shape(blob, i, name):
    at = blocks(blob)[i][1]
    length, = struct.unpack_from("<i", blob, at)
    new = name.encode("ascii")
    return blob[:at] + struct.pack("<i", len(new)) + new + blob[at + 4 + length:]


def _retexture_all(blob, texture):
    out, p = bytearray(), 0
    low = blob.lower()
    for ext in (b".dds", b".tga", b".bmp"):
        pass
    i = 0
    while i < len(blob) - 8:
        length, = struct.unpack_from("<I", blob, i)
        if 5 <= length <= 64:
            s = low[i + 4:i + 4 + length]
            if s.endswith((b".dds", b".tga", b".bmp")) and all(32 <= c < 127 for c in s) and b"enviro" not in s:
                out += blob[p:i] + struct.pack("<I", len(texture)) + texture.encode("ascii")
                p = i = i + 4 + length
                continue
        i += 1
    return bytes(out + blob[p:])


def write(donor, slot, world_verts, uv, tris, weights, bone_names, frames,
          texture):
    """donor: bytes. world_verts in the game's rest-pose world. weights: list
    per vertex of [(bone name, w)]. Returns (blob, read-back error)."""
    blob = donor
    skins = read_skin(blob)
    target = skins[0]
    tree = nodes(blob)
    file_world = world(blob)
    b0 = tree[target["bones"][0]]["name"]
    r, p, s = file_world[b0]
    info = target["bone_info"][0]
    C = _mat(r, p, s) @ _mat(info["rotation"], info["translation"], info["scale"])
    Cinv = np.linalg.inv(C)
    for ref, bi in zip(target["bones"], target["bone_info"]):
        rr, pp, ss = file_world[tree[ref]["name"]]
        other = _mat(rr, pp, ss) @ _mat(bi["rotation"], bi["translation"], bi["scale"])
        if np.abs(other - C).max() > 1e-2:
            raise SystemExit(f"donor breaks the rule at {tree[ref]['name']}: "
                             f"{np.abs(other - C).max():.4f}")

    merged = []
    for pairs in weights:
        acc = {}
        for name, w in pairs:
            name = FALLBACK.get(name, name)
            acc[name] = acc.get(name, 0.0) + w
        merged.append(list(acc.items()))
    weights = merged
    bone_names = sorted({b for pairs in weights for b, _w in pairs})

    node_index = {n["name"]: i for i, n in tree.items()}
    missing = [b for b in bone_names if b not in node_index]
    if missing:
        raise SystemExit(f"donor has no nodes for {missing}")

    # our vertices in C's space, both facings
    n = len(world_verts)
    local = (np.c_[world_verts, np.ones(n)] @ Cinv.T)[:, :3]
    verts2 = np.vstack([local, local])
    uv2 = np.vstack([uv, uv])
    faces = np.vstack([tris, tris[:, ::-1] + n])

    # 1. geometry: replace the target shape's NiTriShapeData
    shape_i = target["shape_index"]
    data_ref, = struct.unpack_from("<i", blob, _end(blob, shape_i) - 8)
    body = blocks(blob)[data_ref][1]
    blob = blob[:body] + _shape_data(verts2, uv2, faces) + blob[_end(blob, data_ref):]

    # 2. skin data: bones, transforms, spheres, weights
    per_bone = {b: [] for b in bone_names}
    for v, pairs in enumerate(weights):
        for name, w in pairs:
            per_bone[name].append((v, w))
            per_bone[name].append((v + n, w))
    data = bytearray()
    t = target["transform"]
    data += struct.pack("<9f", *np.ravel(t["rotation"]))
    data += struct.pack("<3f", *t["translation"]) + struct.pack("<f", t["scale"])
    data += struct.pack("<Ii", len(bone_names), -1)
    for name in bone_names:
        rb, pb, sb = frames[name]
        T = np.linalg.inv(_mat(rb, pb, sb)) @ C
        scale = float(np.cbrt(np.linalg.det(T[:3, :3])))
        data += struct.pack("<9f", *np.ravel(T[:3, :3] / scale))
        data += struct.pack("<3f", *T[:3, 3]) + struct.pack("<f", scale)
        idx = [v for v, _w in per_bone[name]]
        pts = (np.c_[verts2[idx], np.ones(len(idx))] @ T.T)[:, :3] if idx \
            else np.zeros((1, 3))
        centre = pts.mean(0)
        data += struct.pack("<4f", *centre, float(np.linalg.norm(pts - centre, axis=1).max()))
        data += struct.pack("<H", len(per_bone[name]))
        for v, w in per_bone[name]:
            data += struct.pack("<Hf", v, w)
    target = read_skin(blob)[0]
    dstart = _start(blob, target["data_index"])
    dname = blocks(blob)[target["data_index"]][0]
    body = blocks(blob)[target["data_index"]][1]
    blob = blob[:body] + bytes(data) + blob[_end(blob, target["data_index"]):]
    assert dstart + 4 + len(dname) == body

    # 3. skin instance: our bone refs
    target = read_skin(blob)[0]
    at = blocks(blob)[target["instance_index"]][1]
    inst = struct.pack("<iiI", target["data_index"], target["root"], len(bone_names))
    inst += struct.pack(f"<{len(bone_names)}i", *[node_index[b] for b in bone_names])
    blob = blob[:at] + inst + blob[_end(blob, target["instance_index"]):]

    # 4. names: ours matches the slot, the rest never do
    for k, sk in enumerate(read_skin(blob)):
        blob = _rename_shape(blob, sk["shape_index"],
                             f"Tri {slot} 0" if k == 0 else f"Tri Unused {k}")
    blob = _retexture_all(blob, texture)
    blob = _only_child_shape(blob, read_skin(blob)[0]["shape_index"])
    for i, node in nodes(blob).items():
        if node["name"] == "Chest" and slot != "Chest":
            blob = _rename_shape(blob, i, slot)

    # read back as the engine composes it
    from uvmap import parse_trishape  # noqa: F401
    back = read_skin(blob)[0]
    tree = nodes(blob)
    dref = struct.unpack_from("<i", blob, _end(blob, back["shape_index"]) - 8)[0]
    vb = _parse_verts(blob, _start(blob, dref))
    acc = np.zeros((len(vb), 3))
    tot = np.zeros(len(vb))
    for ref, bi in zip(back["bones"], back["bone_info"]):
        rb, pb, sb = frames[tree[ref]["name"]]
        M = _mat(rb, pb, sb) @ _mat(bi["rotation"], bi["translation"], bi["scale"])
        for v, w in bi["weights"]:
            acc[v] += w * (M @ np.r_[vb[v], 1.0])[:3]
            tot[v] += w
    err = float(np.abs(acc[:n] - world_verts).max())
    return blob, err, float(np.abs(tot - 1).max())


def _only_child_shape(blob, keep):
    """Detach every NiTriShape but `keep` from the nodes that hold them.

    The engine copies the slot-named node whole, children and all
    (CopyRigVisitor walks up to the parent whose name matches). Renamed but
    still attached, the donor's own ebony shapes were drawn with our texture
    and their old weights - a dark mini-skirt swinging left and right.
    Detached blocks stay in the file, unreferenced, and are never loaded.
    """
    kinds = blocks(blob)
    shapes = {i for i, (k, _a) in enumerate(kinds) if k == "NiTriShape"}
    for i, (kind, at) in enumerate(kinds):
        if kind != "NiNode":
            continue
        p = at
        length, = struct.unpack_from("<i", blob, p)
        p += 4 + length + 4 + 4 + 2 + 12 + 36 + 4 + 12
        props, = struct.unpack_from("<I", blob, p)
        p += 4 + 4 * props
        has_box, = struct.unpack_from("<I", blob, p)
        p += 4 + (64 if has_box else 0)
        count, = struct.unpack_from("<I", blob, p)
        kids = list(struct.unpack_from(f"<{count}i", blob, p + 4))
        kept = [k for k in kids if k not in shapes or k == keep]
        if kept != kids:
            blob = (blob[:p] + struct.pack(f"<I{len(kept)}i", len(kept), *kept)
                    + blob[p + 4 + 4 * count:])
            kinds = blocks(blob)
    return blob


def _shape_data(verts, uv, tris):
    """A whole NiTriShapeData body, written rather than patched.

    The cuirass donor carries vertex colours, which the rigid writer's layout
    does not expect - it cut the file at the wrong byte. Here every field is
    ours: vertices, normals, bound, no colours, one UV set, triangles, no
    match groups.
    """
    if len(verts) > 65535:
        raise SystemExit(f"{len(verts)} vertices - the index type is 16-bit")
    nrm = normals(verts, tris)
    centre = (verts.min(axis=0) + verts.max(axis=0)) / 2.0
    radius = float(np.linalg.norm(verts - centre, axis=1).max())
    out = bytearray(struct.pack("<HI", len(verts), 1))
    out += np.asarray(verts, np.float32).tobytes()
    out += struct.pack("<I", 1) + np.asarray(nrm, np.float32).tobytes()
    out += struct.pack("<3ff", *centre, radius)
    out += struct.pack("<I", 0)                       # no vertex colours
    out += struct.pack("<HI", 1, 1) + np.asarray(uv, np.float32).tobytes()
    out += struct.pack("<HI", len(tris), 3 * len(tris))
    out += np.asarray(tris, np.uint16).tobytes()
    out += struct.pack("<H", 0)                       # no match groups
    return bytes(out)


def _parse_verts(blob, data_block_start):
    at = data_block_start + 4 + len("NiTriShapeData")
    count, = struct.unpack_from("<H", blob, at)
    return np.frombuffer(blob, np.float32, count * 3, at + 6).reshape(-1, 3).astype(np.float64)
