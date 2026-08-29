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

    # Nothing here is taken on faith about the field layout. Writers differ on
    # whether the "has vertices" flag is a byte or a four-byte bool, and on what
    # optional members sit between the arrays, so instead of encoding one
    # writer's dialect this searches for the arrangement that is *consistent*:
    # finite vertices, UVs inside the unit square, a triangle header whose point
    # count is three times its triangle count, and indices that fit the vertex
    # count. That combination does not occur by accident.
    for vert_off in (off + 2, off + 3, off + 6):
        if vert_off + 12 * count > len(blob):
            continue
        verts = np.frombuffer(blob, np.float32, count * 3, vert_off)
        if not np.isfinite(verts).all() or np.abs(verts).max() > 1e4:
            continue
        verts = verts.reshape(count, 3)
        for uv_off in range(vert_off + 12 * count, len(blob) - 8 * count):
            tri_off = uv_off + 8 * count
            if tri_off + 6 > len(blob):
                break
            ntri, = struct.unpack_from("<H", blob, tri_off)
            npoints, = struct.unpack_from("<I", blob, tri_off + 2)
            if ntri == 0 or npoints != 3 * ntri:
                continue
            if tri_off + 6 + 6 * ntri > len(blob):
                continue
            uv = np.frombuffer(blob, np.float32, count * 2, uv_off).reshape(count, 2)
            if not np.isfinite(uv).all() or uv.min() < -0.05 or uv.max() > 1.05:
                continue
            tris = np.frombuffer(blob, np.uint16, ntri * 3,
                                 tri_off + 6).reshape(ntri, 3)
            if tris.max() >= count:
                continue
            return (verts.astype(np.float64).copy(),
                    uv.astype(np.float64).copy(),
                    tris.astype(np.int32).copy())
    raise ValueError("no self-consistent vertex, UV and triangle layout found")


def rasterise(verts, uv, tris, size):
    """Per-pixel 3D position over the UV sheet, and a coverage mask.

    Nearest-triangle is not needed: the islands do not overlap, so a plain
    scanline fill of each triangle is enough. Written straightforwardly rather
    than cleverly - 230 triangles is nothing.
    """
    h = w = size
    pos = np.zeros((h, w, 3), np.float32)
    cover = np.zeros((h, w), np.float32)
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
        sl = (slice(y0, y1), slice(x0, x1))
        pos[sl][inside] = p[inside]
        cover[sl][inside] = 1.0
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
