#!/usr/bin/env python3
"""Read glTF and GLB, so a model downloaded from the web can be looked at.

    python tools/scripts/glb.py model.glb
    python tools/scripts/glb.py model.glb --extract helmet --out helmet.obj

GLB is the format to ask for when a site offers a choice. It is one file
carrying geometry, texture coordinates and the texture images together, so
nothing is lost between the download and here, and inside it is open glTF: a
JSON header plus a binary blob. No library is needed, which is the whole reason
to prefer it.

## A budget I quoted and got wrong

The first thing this tool was used for was to check a downloaded helmet against
what Morrowind can carry, and it corrected me. I had said 50 to 620 vertices a
shape, taken from the vanilla Daedric set. **Those are 2002 counts, not a
limit.** Measured across 828 mesh files in the modpack already installed:
median 986 vertices, ninetieth percentile 3,407, largest 14,696. The armour
being worn while I said it, `DaedricArmorM.nif`, is 8,230 across 18 shapes.

So a 3,000-vertex helmet needs no decimation at all. What blocks it is writing
the NIF, not the polygon count.
"""

import argparse
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from obj import write as write_obj  # noqa: E402

# glTF component types, and how many values each element holds.
COMPONENT = {5120: "i1", 5121: "u1", 5122: "i2", 5123: "u2",
             5125: "u4", 5126: "f4"}
COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
         "MAT2": 4, "MAT3": 9, "MAT4": 16}


class Gltf:
    def __init__(self, path):
        with open(path, "rb") as f:
            blob = f.read()
        if blob[:4] == b"glTF":
            self.json, self.bin = self._unwrap(blob)
        else:
            self.json = json.loads(blob.decode("utf-8"))
            self.bin = self._external(path)

    @staticmethod
    def _unwrap(blob):
        _magic, _version, total = struct.unpack_from("<4sII", blob, 0)
        if total != len(blob):
            raise ValueError(f"header says {total} bytes, file is {len(blob)}")
        head, body, off = None, b"", 12
        while off < len(blob):
            length, kind = struct.unpack_from("<II", blob, off)
            chunk = blob[off + 8:off + 8 + length]
            if kind == 0x4E4F534A:
                head = json.loads(chunk.decode("utf-8"))
            elif kind == 0x004E4942:
                body = chunk
            off += 8 + length
        if head is None:
            raise ValueError("no JSON chunk")
        return head, body

    def _external(self, path):
        buffers = self.json.get("buffers", [])
        if not buffers or "uri" not in buffers[0]:
            return b""
        with open(os.path.join(os.path.dirname(path), buffers[0]["uri"]),
                  "rb") as f:
            return f.read()

    def accessor(self, index):
        """One accessor as an array, honouring the byte stride."""
        acc = self.json["accessors"][index]
        view = self.json["bufferViews"][acc["bufferView"]]
        dtype = np.dtype("<" + COMPONENT[acc["componentType"]])
        width = COUNT[acc["type"]]
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = view.get("byteStride") or dtype.itemsize * width
        if stride == dtype.itemsize * width:
            flat = np.frombuffer(self.bin, dtype,
                                 acc["count"] * width, start)
            return flat.reshape(acc["count"], width)
        rows = np.empty((acc["count"], width), dtype)
        for i in range(acc["count"]):
            rows[i] = np.frombuffer(self.bin, dtype, width, start + i * stride)
        return rows

    def primitives(self):
        """(mesh name, index, vertices, uv, triangles) for every primitive."""
        for mesh in self.json.get("meshes", []):
            for i, prim in enumerate(mesh.get("primitives", [])):
                attrs = prim.get("attributes", {})
                if "POSITION" not in attrs:
                    continue
                verts = self.accessor(attrs["POSITION"]).astype(np.float64)
                if "TEXCOORD_0" in attrs:
                    uv = self.accessor(attrs["TEXCOORD_0"]).astype(np.float64)
                else:
                    uv = np.zeros((len(verts), 2))
                if "indices" in prim:
                    idx = self.accessor(prim["indices"]).ravel().astype(np.int32)
                    tris = idx.reshape(-1, 3)
                else:
                    tris = np.arange(len(verts), dtype=np.int32).reshape(-1, 3)
                material = prim.get("material")
                name = mesh.get("name") or "mesh"
                mat = (self.json.get("materials", [{}])[material].get("name")
                       if material is not None else None)
                yield name, i, mat, verts, uv, tris


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("--extract", metavar="SUBSTRING",
                    help="write the primitive whose material or name matches")
    ap.add_argument("--out", help="destination .obj for --extract")
    args = ap.parse_args()

    model = Gltf(args.path)
    print(f"glTF {model.json.get('asset', {}).get('version')} from "
          f"{model.json.get('asset', {}).get('generator')}")
    print(f"{len(model.json.get('meshes', []))} meshes, "
          f"{len(model.json.get('images', []))} images, "
          f"{len(model.json.get('skins', []))} skin(s)")

    print(f"\n{'MESH':<14}{'MATERIAL':<14}{'VERTS':>8}{'TRIS':>8}  "
          f"{'UV':<4} SIZE")
    total_v = total_t = 0
    for name, i, mat, verts, uv, tris in model.primitives():
        size = np.round(verts.max(axis=0) - verts.min(axis=0), 3)
        has_uv = "yes" if uv.any() else "NO"
        print(f"{name[:13]:<14}{str(mat)[:13]:<14}{len(verts):>8}"
              f"{len(tris):>8}  {has_uv:<4} {size}")
        total_v += len(verts)
        total_t += len(tris)
        if args.extract and args.out:
            hay = f"{name} {mat}".lower()
            if args.extract.lower() in hay:
                write_obj(args.out, verts, uv, tris, name)
                print(f"    -> written to {args.out}")
    print(f"\ntotal {total_v} vertices, {total_t} triangles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
