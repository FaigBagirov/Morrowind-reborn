#!/usr/bin/env python3
"""Write a Morrowind NIF carrying geometry from somewhere else.

    python tools/scripts/nif_write.py helmet.obj --donor meshes/a/a_ebony_helmet.nif --out new.nif

The project rule against generating NIFs rested on a sentence in Canon Part 9 -
"the engine validates models on load and rejects machine-assembled files" -
which had never been tested by anyone here. It is false, measured twice: OpenMW's
own `niftest` accepts a mesh a script reshaped, and accepts this, a file carrying
3,269 vertices of downloaded geometry where the donor had 117.

## How it is done, and why it is safe to do this way

Not from nothing. A **donor** file supplies everything except the geometry - the
node, the material, the texture reference, the trailing bytes - and only its
`NiTriShapeData` block is replaced. In this format blocks refer to each other by
index rather than by offset and carry no length field, so a block that changes
size breaks nothing after it.

The layout of that block was not guessed. It was established by parsing a real
file and rebuilding it from its own arrays until all 5,761 bytes came back
identical:

    ushort numVertices        uint32 flag      float3 * n vertices
    uint32 flag               float3 * n normals
    float3 centre             float radius
    uint32 hasVertexColours   ushort numUVSets    uint32 flag
    float2 * n texture coordinates
    ushort numTriangles       uint32 numTrianglePoints
    ushort3 * m triangles

The three `flag` words are copied from the donor rather than invented. They read
as neither 0 nor 1 in the file examined, so what they mean is **not known**;
passing them through is honest and works, and writing a guess would not be.

## What it does not do

* **Rigging.** Morrowind dresses a body from separate rigid parts, so a helmet
  needs none. Anything spanning a joint would.
* **Judging the result.** `niftest` reads a file; it does not wear one. Whether
  the piece sits on the head, faces forward and does not clip is a question for
  the game.
* **Collision.** The donor's own is carried through unexamined.
"""

import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from obj import read as read_obj  # noqa: E402
from uvmap import read_mesh  # noqa: E402

MARKER = b"NiTriShapeData"


def donor_parts(blob):
    """Everything of the donor that is kept, plus its three unexplained words."""
    start = blob.find(MARKER)
    if start < 0:
        raise ValueError("donor has no NiTriShapeData block")
    body = start + len(MARKER)
    count, = struct.unpack_from("<H", blob, body)
    flag_a, = struct.unpack_from("<I", blob, body + 2)
    verts_end = body + 6 + 12 * count
    flag_b, = struct.unpack_from("<I", blob, verts_end)
    sphere = verts_end + 4 + 12 * count
    flag_c, = struct.unpack_from("<I", blob, sphere + 22)
    uv_off = sphere + 26
    tri_off = uv_off + 8 * count
    ntri, = struct.unpack_from("<H", blob, tri_off)
    tail = blob[tri_off + 6 + 6 * ntri:]
    return blob[:body], (flag_a, flag_b, flag_c), tail


def retexture(blob, name):
    """Point the donor's texture reference somewhere else.

    Without this a mesh built on the ebony helm wears the ebony helm's texture,
    because that filename is baked into the donor's NiSourceTexture block. The
    string is length-prefixed and nothing in this format stores block offsets,
    so a replacement of any length is safe.
    """
    for ext in (b".bmp", b".dds", b".tga", b".png"):
        at = blob.lower().find(ext)
        while at > 0:
            # walk back to a plausible length prefix and check it matches
            for back in range(4, 80):
                start = at + 4 - back
                if start < 4:
                    break
                length, = struct.unpack_from("<I", blob, start - 4)
                if length == back and _printable(blob[start:start + back]):
                    old = blob[start:start + back].decode("ascii")
                    new = name.encode("ascii")
                    return (blob[:start - 4] + struct.pack("<I", len(new))
                            + new + blob[start + back:]), old
            at = blob.lower().find(ext, at + 1)
    raise ValueError("no texture filename found in the donor")


def _printable(chunk):
    return all(32 <= c < 127 for c in chunk)


def normals(verts, tris):
    """Area-weighted per-vertex normals, which is what the format stores."""
    out = np.zeros_like(verts)
    corner = verts[tris]
    face = np.cross(corner[:, 1] - corner[:, 0], corner[:, 2] - corner[:, 0])
    for k in range(3):
        np.add.at(out, tris[:, k], face)
    length = np.linalg.norm(out, axis=1, keepdims=True)
    return np.where(length > 1e-12, out / np.maximum(length, 1e-12),
                    np.array([0.0, 0.0, 1.0]))


def fit(verts, donor_verts, swap=True):
    """Put an incoming mesh where the donor's is, at the donor's size.

    glTF and most exporters are Y-up with +Z toward the viewer; Morrowind is
    Z-up. The scale is uniform and taken from the tightest of the three axes, so
    proportions survive and nothing pokes out of the space the original piece
    occupied.
    """
    if swap:
        verts = np.column_stack([verts[:, 0], -verts[:, 2], verts[:, 1]])
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    lo0, hi0 = donor_verts.min(axis=0), donor_verts.max(axis=0)
    scale = float(np.min((hi0 - lo0) / np.maximum(hi - lo, 1e-9)))
    return (verts - (lo + hi) / 2.0) * scale + (lo0 + hi0) / 2.0, scale


def build(donor_blob, verts, uv, tris):
    head, (flag_a, flag_b, flag_c), tail = donor_parts(donor_blob)
    if len(verts) > 65535:
        raise SystemExit(f"{len(verts)} vertices - the index type is 16-bit")
    nrm = normals(verts, tris)
    centre = (verts.min(axis=0) + verts.max(axis=0)) / 2.0
    radius = float(np.linalg.norm(verts - centre, axis=1).max())

    out = bytearray()
    out += struct.pack("<H", len(verts)) + struct.pack("<I", flag_a)
    out += np.asarray(verts, np.float32).tobytes()
    out += struct.pack("<I", flag_b)
    out += np.asarray(nrm, np.float32).tobytes()
    out += struct.pack("<3f", *centre) + struct.pack("<f", radius)
    out += struct.pack("<I", 0) + struct.pack("<H", 1) + struct.pack("<I", flag_c)
    out += np.asarray(uv, np.float32).tobytes()
    out += struct.pack("<H", len(tris)) + struct.pack("<I", 3 * len(tris))
    out += np.asarray(tris, np.uint16).tobytes()
    return head + bytes(out) + tail


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", help="an .obj carrying the new geometry")
    ap.add_argument("--donor", required=True,
                    help="a game mesh to borrow everything else from")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-swap", action="store_true",
                    help="the source is already Z-up")
    ap.add_argument("--no-fit", action="store_true",
                    help="leave the source at its own scale and position")
    ap.add_argument("--texture", metavar="NAME",
                    help="repoint the donor's texture reference, e.g. "
                         "zenar_helm.dds - without this the new mesh wears "
                         "the donor's own texture")
    args = ap.parse_args()

    verts, uv, tris = read_obj(args.source)
    donor_verts, _duv, _dtris = read_mesh(args.donor)
    print(f"incoming {len(verts)} vertices, {len(tris)} triangles")
    print(f"donor    {len(donor_verts)} vertices")

    if not args.no_fit:
        verts, scale = fit(verts, donor_verts, swap=not args.no_swap)
        print(f"fitted   scale {scale:.3f}"
              f"{'' if args.no_swap else ', axes swapped to Z-up'}")
    print("bounds   X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f"
          % (verts[:, 0].min(), verts[:, 0].max(), verts[:, 1].min(),
             verts[:, 1].max(), verts[:, 2].min(), verts[:, 2].max()))

    with open(_resolve(args.donor), "rb") as f:
        blob = f.read()
    if args.texture:
        blob, was = retexture(blob, args.texture)
        print(f"texture  {was} -> {args.texture}")
    written = build(blob, verts, uv, tris)
    with open(args.out, "wb") as f:
        f.write(written)
    print(f"written  {args.out}, {len(written):,} bytes "
          f"(donor was {len(blob):,})")
    print("Now ask the engine:  niftest.exe " + args.out)
    return 0


def _resolve(rel):
    """The donor as a real file, extracted from a BSA if it only lives there."""
    if os.path.exists(rel):
        return rel
    from bsa import find, open_archives
    from uvmap import BSA_DIR, MASTER_BSAS
    archives = open_archives([os.path.join(BSA_DIR, n) for n in MASTER_BSAS])
    hit = find(archives, rel.replace("\\", "/").lower())
    if not hit:
        raise SystemExit(f"donor not found: {rel}")
    scratch = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "build", "donor-" + os.path.basename(rel))
    scratch = os.path.abspath(scratch)
    os.makedirs(os.path.dirname(scratch), exist_ok=True)
    with open(scratch, "wb") as f:
        f.write(hit[0].read(hit[1]))
    return scratch


if __name__ == "__main__":
    sys.exit(main())
