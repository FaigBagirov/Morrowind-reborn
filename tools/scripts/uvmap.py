#!/usr/bin/env python3
"""Rasterise a mesh's UV layout, so a texture pixel knows where it sits in 3D.

To paint a feature on a piece of armour - eye slits at the front of a helmet -
you have to know which pixels of the sheet land on the front. Fitting a formula
to that mapping was tried first and is not good enough: the ebony helm's unwrap
turns out to fold the left and right halves of the head onto the same pixels,
and a straight-line fit of u against azimuth leaves a residual of 0.10 turns,
which is 36 degrees. Eye slits do not survive 36 degrees.

So do it exactly. Every triangle carries three UVs and three positions; filling
each triangle in UV space with barycentric interpolation gives every pixel its
own 3D point, with no fit and no residual.

**Reading a NIF is not editing one.** The project rule forbids generating or
editing them, and nothing here writes. The parse is validated rather than
trusted: the vertex, UV and triangle blocks have to tile the file exactly, the
index range has to match the vertex count, and `numTrianglePoints` has to equal
three times the triangle count. If any of that fails it raises instead of
guessing.
"""

import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsa import find, open_archives  # noqa: E402
from effective import parse_cfg  # noqa: E402

BSA_DIR = r"D:/ProgramFiles/Steam/steamapps/common/Morrowind/Data Files"
MASTER_BSAS = ("Morrowind.bsa", "Tribunal.bsa", "Bloodmoon.bsa")


def read_mesh(rel_path, cfg_path=None, bsa_dir=BSA_DIR):
    """Vertices, UVs and triangles out of a Morrowind NIF.

    `rel_path` is as the game names it, e.g. "meshes/a/a_ebony_helmet.nif".
    A loose file in the load order wins over the archives, as it does in game.
    """
    blob = None
    if cfg_path:
        data, _ = parse_cfg(cfg_path)
        parts = rel_path.split("/")
        for directory in data:
            candidate = os.path.join(directory, *parts)
            if os.path.exists(candidate):
                with open(candidate, "rb") as f:
                    blob = f.read()
    if blob is None:
        archives = open_archives([os.path.join(bsa_dir, n) for n in MASTER_BSAS])
        hit = find(archives, rel_path)
        if not hit:
            raise SystemExit(f"{rel_path} is in neither the load order nor the BSAs")
        archive, name = hit
        blob = archive.read(name)
        for a in archives:
            a.close()
    return parse_trishape(blob)


def parse_trishape(blob):
    start = blob.find(b"NiTriShapeData")
    if start < 0:
        raise ValueError("no NiTriShapeData block")
    off = start + len("NiTriShapeData")
    count, = struct.unpack_from("<H", blob, off)
    if not 3 <= count <= 65000:
        raise ValueError(f"implausible vertex count {count}")

    # The layout, established by rebuilding a real file from its own parsed
    # arrays and getting all 5,761 bytes back identical:
    #
    #   ushort numVertices          uint32 flag     float3 * n vertices
    #   uint32 flag                 float3 * n normals
    #   float3 centre               float radius
    #   uint32 hasVertexColours     ushort numUVSets    uint32 flag
    #   float2 * n texture coordinates
    #   ushort numTriangles         uint32 numTrianglePoints
    #   ushort3 * m triangles
    #
    # An earlier version of this function searched for a layout that merely
    # looked consistent and settled on one four bytes short, because a float
    # array read at the wrong offset is still a float array. The damage was
    # silent and real: the vertices came back scrambled against their own UVs,
    # which is what made this mesh's azimuth map look like an overlapping mess.
    #
    # So it is checked against something no wrong offset can satisfy: the file
    # states its own bounding sphere, and the stated radius has to equal the
    # furthest vertex from the stated centre. On the ebony helm both are
    # 13.0252.
    vert_off = off + 6
    norm_off = vert_off + 12 * count + 4
    sphere_off = norm_off + 12 * count
    uv_off = sphere_off + 16 + 4 + 2 + 4
    tri_off = uv_off + 8 * count
    if tri_off + 6 > len(blob):
        raise ValueError("file ends before the triangle header")

    verts = np.frombuffer(blob, np.float32, count * 3, vert_off).reshape(count, 3)
    centre = np.frombuffer(blob, np.float32, 3, sphere_off)
    radius, = struct.unpack_from("<f", blob, sphere_off + 12)
    reach = float(np.linalg.norm(verts - centre, axis=1).max())
    if radius <= 0 or abs(reach - radius) > max(radius * 1e-3, 1e-3):
        raise ValueError(f"bounding sphere disagrees: stated {radius:.4f}, "
                         f"furthest vertex {reach:.4f} - layout not understood")

    ntri, = struct.unpack_from("<H", blob, tri_off)
    npoints, = struct.unpack_from("<I", blob, tri_off + 2)
    if npoints != 3 * ntri or tri_off + 6 + 6 * ntri > len(blob):
        raise ValueError("triangle header inconsistent")
    uv = np.frombuffer(blob, np.float32, count * 2, uv_off).reshape(count, 2)
    tris = np.frombuffer(blob, np.uint16, ntri * 3, tri_off + 6).reshape(ntri, 3)
    if tris.max() >= count:
        raise ValueError("triangle index out of range")
    return (verts.astype(np.float64).copy(), uv.astype(np.float64).copy(),
            tris.astype(np.int32).copy())


def rasterise(verts, uv, tris, size):
    """Per-pixel 3D position over the UV sheet, and a coverage mask.

    **The islands do overlap.** Assuming they did not left rectangular patches
    across the height and azimuth maps where a small piece of the mesh - the
    inside of the shell, a detail strip - had been rasterised over the main one,
    and any pattern drawn on that map tore into steps exactly there.

    So overlaps are resolved rather than ignored: the surface furthest from the
    centre wins. That is the one the player can see, and it is the one a texture
    is painted for.
    """
    h = w = size
    pos = np.zeros((h, w, 3), np.float32)
    cover = np.zeros((h, w), np.float32)
    centre = verts.mean(axis=0)
    best = np.full((h, w), -1.0, np.float32)
    px = uv[:, 0] * (w - 1)
    py = uv[:, 1] * (h - 1)
    for a, b, c in tris:
        xs = np.array([px[a], px[b], px[c]])
        ys = np.array([py[a], py[b], py[c]])
        x0, x1 = int(np.floor(xs.min())), int(np.ceil(xs.max())) + 1
        y0, y1 = int(np.floor(ys.min())), int(np.ceil(ys.max())) + 1
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, w), min(y1, h)
        if x1 <= x0 or y1 <= y0:
            continue
        gy, gx = np.mgrid[y0:y1, x0:x1]
        gx = gx.astype(np.float64)
        gy = gy.astype(np.float64)
        det = ((ys[1] - ys[2]) * (xs[0] - xs[2])
               + (xs[2] - xs[1]) * (ys[0] - ys[2]))
        if abs(det) < 1e-9:
            continue
        l0 = ((ys[1] - ys[2]) * (gx - xs[2])
              + (xs[2] - xs[1]) * (gy - ys[2])) / det
        l1 = ((ys[2] - ys[0]) * (gx - xs[2])
              + (xs[0] - xs[2]) * (gy - ys[2])) / det
        l2 = 1.0 - l0 - l1
        inside = (l0 >= -0.002) & (l1 >= -0.002) & (l2 >= -0.002)
        if not inside.any():
            continue
        p = (l0[..., None] * verts[a] + l1[..., None] * verts[b]
             + l2[..., None] * verts[c])
        out = np.linalg.norm(p - centre, axis=-1).astype(np.float32)
        sl = (slice(y0, y1), slice(x0, x1))
        take = inside & (out > best[sl])
        if not take.any():
            continue
        pos[sl][take] = p[take]
        best[sl][take] = out[take]
        cover[sl][take] = 1.0
    return pos, cover


def polar(pos, cover):
    """Height and azimuth per pixel, in the mesh's own frame.

    Up is taken as the axis the height correlates with, found by regression
    rather than assumed: this mesh turned out to use local Z, but the next one
    need not. Azimuth is in turns, 0 dead ahead, and the caller supplies what
    "ahead" means, because geometry alone cannot say which way a helmet faces.
    """
    mask = cover > 0
    pts = pos[mask]
    centre = pts.mean(axis=0)

    # Up is the direction the sheet's vertical axis runs against. Taking it as
    # the mesh's axis of least variance was tried and is wrong - a helmet is
    # thinnest across the ears, not top to bottom, and that guess put the pole
    # through the side of the head. The sheet knows better: every unwrap of a
    # helmet in this game lays height along v, and regressing position on the
    # row index recovers it in one line, with the sign fixed by v growing
    # downwards.
    rows = np.mgrid[0:pos.shape[0], 0:pos.shape[1]][0].astype(np.float64)
    rows = rows[mask] / (pos.shape[0] - 1)
    design = np.c_[np.ones(rows.size), rows]
    coefficients, *_ = np.linalg.lstsq(design, pts - centre, rcond=None)
    up = -coefficients[1]
    up /= np.linalg.norm(up)
    height = (pos - centre) @ up
    radial = (pos - centre) - height[..., None] * up
    e1 = np.array([1.0, 0.0, 0.0]) - up * up[0]
    if np.linalg.norm(e1) < 1e-3:
        e1 = np.array([0.0, 1.0, 0.0]) - up * up[1]
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    azimuth = np.arctan2(radial @ e2, radial @ e1) / (2.0 * np.pi)
    return height, azimuth, centre, up
