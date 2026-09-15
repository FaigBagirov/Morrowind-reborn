#!/usr/bin/env python3
"""Read and write the skinning blocks of a Morrowind (4.0.0.2) NIF.

Layout read from OpenMW 0.51 (`components/nif/data.cpp`: NiSkinInstance::read,
NiSkinData::read, ReadNiSkinDataBoneInfo) and checked against a vanilla
cuirass: every block parsed here must end exactly where the next block's
length-prefixed class name begins, or `read_skin` raises.

    NiSkinInstance  data ref, root ref, uint32 n, n bone refs
    NiSkinData      transform (9 rot, 3 pos, 1 scale), uint32 n, partition ref,
                    n x [transform, sphere(4), uint16 count, count x (uint16 vertex, float weight)]
    NiTriShape      ...NiAVObject fields..., data ref, skin ref   (last 8 bytes)

How the engine uses it (`nifloader.cpp`, `riggeometry.cpp`): a bone's
transform is its inverse bind matrix, the data transform is applied on top,
and bones are matched to the actor's skeleton by name.
"""

import struct

from skeleton import blocks


def _start(kinds, i, size):
    """Byte where block i begins (its class-name length prefix)."""
    if i >= len(kinds):
        return size
    name, at = kinds[i]
    return at - len(name) - 4


def _transform(blob, p):
    vals = struct.unpack_from("<13f", blob, p)
    return {"rotation": [list(vals[0:3]), list(vals[3:6]), list(vals[6:9])],
            "translation": list(vals[9:12]), "scale": vals[12]}, p + 52


def read_skin(blob):
    kinds = blocks(blob)
    size = len(blob)
    shape_of = {}
    for i, (kind, _at) in enumerate(kinds):
        if kind == "NiTriShape":
            end = _start(kinds, i + 1, size)
            skin_ref, = struct.unpack_from("<i", blob, end - 4)
            if skin_ref >= 0:
                shape_of[skin_ref] = i
    out = []
    for i, (kind, at) in enumerate(kinds):
        if kind != "NiSkinInstance":
            continue
        data_ref, root, count = struct.unpack_from("<iiI", blob, at)
        bones = list(struct.unpack_from(f"<{count}i", blob, at + 12))
        instance_end = at + 12 + 4 * count
        p = kinds[data_ref][1]
        transform, p = _transform(blob, p)
        n, _partition = struct.unpack_from("<Ii", blob, p)
        p += 8
        info = []
        for _ in range(n):
            bone, p = _transform(blob, p)
            bone["sphere"] = list(struct.unpack_from("<4f", blob, p))
            p += 16
            nv, = struct.unpack_from("<H", blob, p)
            p += 2
            pairs = struct.unpack_from("<" + "Hf" * nv, blob, p)
            bone["weights"] = list(zip(pairs[0::2], pairs[1::2]))
            p += 6 * nv
            info.append(bone)
        for idx, end in ((i, instance_end), (data_ref, p)):
            if idx + 1 >= len(kinds):
                # the last block ends at the footer: uint32 roots + refs
                roots, = struct.unpack_from("<I", blob, end)
                if end + 4 + 4 * roots == size:
                    continue
            if end != _start(kinds, idx + 1, size):
                raise ValueError(f"block {idx} parsed to {end}, next starts "
                                 f"at {_start(kinds, idx + 1, size)}")
        out.append({"shape_index": shape_of.get(i), "instance_index": i,
                    "data_index": data_ref, "root": root, "bones": bones,
                    "transform": transform, "bone_info": info,
                    "instance_end": instance_end, "data_end": p})
    return out
