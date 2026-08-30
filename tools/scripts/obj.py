#!/usr/bin/env python3
"""Read and write Wavefront OBJ, so a mesh can come in from outside.

    python tools/scripts/obj.py meshes/a/a_ebony_helmet.nif out.obj

OBJ is the easiest interchange format to accept here, and the reason is dull
rather than clever: it is plain text with four line types worth caring about, so
it needs no library and nothing can be silently misread. It also carries texture
coordinates, which is the thing STL lacks and the thing a mesh is useless
without - no UVs means nowhere to put a texture, and the piece renders as flat
plastic however good the sculpt is.

    v  x y z            a vertex
    vt u v              a texture coordinate
    vn x y z            a normal
    f  a/b/c ...        a face, indices 1-based, negative counts from the end

What this does not do is turn an OBJ into something Morrowind will load. That
needs a NIF written from scratch, which is **not proven** - see
`tools/reports/nif.md`. What is proven is swapping geometry into an existing NIF
without changing the layout, which constrains an incoming mesh to the donor's
exact vertex and triangle count. Vanilla helmets run 89 to 177 vertices.
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uvmap import read_mesh  # noqa: E402


def write(path, verts, uv, tris, name="mesh"):
    """Write triangles with texture coordinates. One shared index per vertex."""
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write(f"# {name}: {len(verts)} vertices, {len(tris)} triangles\n")
        f.write(f"o {name}\n")
        for x, y, z in verts:
            # Nine significant figures, not six decimals. At six, two of this
            # helm's 117 vertices came back changed in the last place - enough
            # to fail a byte-for-byte check and exactly the kind of drift that
            # accumulates silently across a round trip.
            f.write(f"v {x:.9g} {y:.9g} {z:.9g}\n")
        for u, v in uv:
            # OBJ's V axis points up, a texture sheet's points down.
            f.write(f"vt {u:.9g} {1.0 - v:.9g}\n")
        for a, b, c in tris:
            f.write(f"f {a + 1}/{a + 1} {b + 1}/{b + 1} {c + 1}/{c + 1}\n")


def read(path):
    """Vertices, UVs and triangles. Quads and n-gons are fanned into triangles.

    OBJ lets a face reference a different vertex and texture index, which a
    mesh with a UV seam always does. Those are split into separate vertices
    here, because that is what the engine's format expects anyway.
    """
    positions, texcoords, faces = [], [], []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            tag = parts[0]
            if tag == "v":
                positions.append([float(x) for x in parts[1:4]])
            elif tag == "vt":
                texcoords.append([float(x) for x in parts[1:3]])
            elif tag == "f":
                corner = []
                for chunk in parts[1:]:
                    bits = chunk.split("/")
                    vi = int(bits[0])
                    ti = int(bits[1]) if len(bits) > 1 and bits[1] else 0
                    vi = vi - 1 if vi > 0 else len(positions) + vi
                    if ti:
                        ti = ti - 1 if ti > 0 else len(texcoords) + ti
                    else:
                        ti = None
                    corner.append((vi, ti))
                for i in range(1, len(corner) - 1):
                    faces.append((corner[0], corner[i], corner[i + 1]))

    seen, verts, uv, tris = {}, [], [], []
    for face in faces:
        indices = []
        for key in face:
            if key not in seen:
                seen[key] = len(verts)
                verts.append(positions[key[0]])
                if key[1] is None:
                    uv.append([0.0, 0.0])
                else:
                    u, v = texcoords[key[1]]
                    uv.append([u, 1.0 - v])
            indices.append(seen[key])
        tris.append(indices)
    return (np.array(verts, np.float64), np.array(uv, np.float64),
            np.array(tris, np.int32))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", help="a .nif inside the game, or a .obj on disk")
    ap.add_argument("out", nargs="?", help="where to write the .obj")
    args = ap.parse_args()

    if args.source.lower().endswith(".obj"):
        verts, uv, tris = read(args.source)
    else:
        verts, uv, tris = read_mesh(args.source)
    print(f"{len(verts)} vertices, {len(tris)} triangles")
    print("bounds  X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f"
          % (verts[:, 0].min(), verts[:, 0].max(), verts[:, 1].min(),
             verts[:, 1].max(), verts[:, 2].min(), verts[:, 2].max()))
    print("uv      U %.3f..%.3f  V %.3f..%.3f"
          % (uv[:, 0].min(), uv[:, 0].max(), uv[:, 1].min(), uv[:, 1].max()))
    if args.out:
        write(args.out, verts, uv, tris,
              os.path.splitext(os.path.basename(args.source))[0])
        print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
