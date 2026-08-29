#!/usr/bin/env python3
"""Generate the Zenaric particle textures: hexagons in alpha, nothing in geometry.

    python tools/scripts/make_vfx.py --preview      # PNG previews only
    python tools/scripts/make_vfx.py --write        # also the .dds into mod/Textures

*Canon* Part 9 settles the design and this only implements it:

  * **The alpha channel carries the shape.** A hard edge under additive blending
    reads as a rendering fault, so every hexagon is drawn with a soft falloff.
  * **A sparse grid, not one hexagon.** One large hexagon smears; a dense grid
    moires into a swarm. Sparse is the Zenaric casting signature and dense is
    reserved for Corprus, so the two are the same generator with one number
    changed.
  * **Nothing is modelled.** No NIF is touched, no geometry exists. A particle
    is a camera-facing billboard a few dozen pixels across for a fraction of a
    second; shape can only live in the texture.

The colour is taken from the texture already installed rather than invented, so
each school keeps its own light - fire stays warm, frost stays cold - and only
the structure becomes theirs.
"""

import argparse
import os
import struct
import sys

import numpy as np
from PIL import Image

# Effects covered, from the masters: how many magic effects reference each.
TARGETS = {
    "vfx_conj_flare02": 31,
    "vfx_bluecloud": 28,
    "vfx_redglowalpha": 13,
    "vfx_particle064": 9,
    "vfx_summon": 2,
    "vfx_corprus": 1,
}
DENSE = {"vfx_corprus"}          # Canon Part 9 reserves the swarm for Corprus.


def hex_field(size, cell, softness, jitter_seed):
    """Sparse hexagon grid as an alpha field in [0,1].

    Flat-topped hexagons on a staggered grid. Distance to a hexagon is the
    max of three axis projections, which gives the six flats without any
    trigonometry per pixel.
    """
    rng = np.random.default_rng(jitter_seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    field = np.zeros((size, size), np.float32)

    dx = cell * 1.5
    dy = cell * np.sqrt(3.0)
    cols = int(size / dx) + 2
    rows = int(size / dy) + 2

    for r in range(-1, rows):
        for c in range(-1, cols):
            cx = c * dx
            cy = r * dy + (dy * 0.5 if c % 2 else 0.0)
            # A little irregularity: a perfect lattice reads as a texture bug.
            cx += rng.uniform(-cell * 0.18, cell * 0.18)
            cy += rng.uniform(-cell * 0.18, cell * 0.18)
            radius = cell * rng.uniform(0.34, 0.5)

            px = np.abs(x - cx)
            py = np.abs(y - cy)
            # Hexagon distance: max of the three flat-normal projections.
            d = np.maximum(px * 0.8660254 + py * 0.5, py)
            edge = np.clip((radius - d) / (radius * softness), 0.0, 1.0)
            field = np.maximum(field, edge * edge * (3 - 2 * edge))  # smoothstep
    return field


def write_dds(path, rgba):
    """Uncompressed 32-bit BGRA DDS. No compressor needed and the engine reads it."""
    h, w = rgba.shape[:2]
    header = bytearray(128)
    header[0:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)                 # header size
    struct.pack_into("<I", header, 8, 0x1 | 0x2 | 0x4 | 0x1000 | 0x8)  # caps|h|w|pixelformat|pitch
    struct.pack_into("<I", header, 12, h)
    struct.pack_into("<I", header, 16, w)
    struct.pack_into("<I", header, 20, w * 4)              # pitch
    struct.pack_into("<I", header, 76, 32)                 # pixelformat size
    struct.pack_into("<I", header, 80, 0x1 | 0x40)         # alphapixels | rgb
    struct.pack_into("<I", header, 88, 32)                 # bit count
    struct.pack_into("<I", header, 92, 0x00FF0000)         # R mask
    struct.pack_into("<I", header, 96, 0x0000FF00)         # G
    struct.pack_into("<I", header, 100, 0x000000FF)        # B
    struct.pack_into("<I", header, 104, 0xFF000000)        # A
    struct.pack_into("<I", header, 108, 0x1000)            # caps: texture
    bgra = rgba[..., [2, 1, 0, 3]].astype(np.uint8)
    with open(path, "wb") as f:
        f.write(header)
        f.write(bgra.tobytes())


def build(src_path, dense):
    src = np.array(Image.open(src_path).convert("RGBA")).astype(np.float32)
    size = src.shape[0]
    lum = src[..., :3].mean(axis=2)
    bright = lum > 8
    if bright.sum() < 64:
        bright = lum > lum.mean()
    # The light this effect already has, taken from its own brightest pixels.
    colour = src[..., :3][bright].mean(axis=0)
    colour = colour / max(colour.max(), 1.0) * 255.0

    cell = size / 9.0 if dense else size / 5.0
    softness = 0.55 if dense else 0.75
    field = hex_field(size, cell, softness, jitter_seed=7)

    # A faint core keeps the particle from disappearing at distance, where the
    # grid is below a pixel and would otherwise flicker out.
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    core = np.clip(1.0 - r, 0.0, 1.0) ** 3 * (0.35 if dense else 0.22)

    alpha = np.clip(field * (1.0 - core) + core, 0.0, 1.0)
    # Vignette: a square-edged particle shows its own quad against the sky.
    alpha *= np.clip(1.2 - r, 0.0, 1.0) ** 1.5

    out = np.zeros((size, size, 4), np.float32)
    out[..., :3] = colour[None, None, :] * (0.45 + 0.55 * alpha[..., None])
    out[..., 3] = alpha * 255.0
    return np.clip(out, 0, 255)


def preview(rgba, path):
    """On black, which is what additive blending shows."""
    a = rgba[..., 3:4] / 255.0
    Image.fromarray((rgba[..., :3] * a).astype(np.uint8)).save(path)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", default=(
        r"D:\Games\OpenMWMods\graphics-overhaul\TexturePacks"
        r"\VurtsMorrowindVisualResurgence\vfx\Data Files\Textures"))
    ap.add_argument("--preview-dir", default=os.path.join(root, "tools", "vfx"))
    ap.add_argument("--out", default=os.path.join(root, "mod", "Textures"))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.preview_dir, exist_ok=True)
    if args.write:
        os.makedirs(args.out, exist_ok=True)

    for name, effects in TARGETS.items():
        src = os.path.join(args.source, name + ".dds")
        if not os.path.exists(src):
            print(f"  missing source, skipped: {name}")
            continue
        rgba = build(src, name in DENSE)
        kind = "dense (Corprus)" if name in DENSE else "sparse"
        prev = os.path.join(args.preview_dir, name + ".png")
        preview(rgba, prev)
        side = os.path.join(args.preview_dir, name + "-before.png")
        preview(np.array(Image.open(src).convert("RGBA")).astype(np.float32), side)
        print(f"  {name:20} {effects:3} effects  {kind:16} -> "
              f"{os.path.relpath(prev, root)}")
        if args.write:
            write_dds(os.path.join(args.out, name + ".dds"), rgba)
    if not args.write:
        print("\nPreview only. Nothing was written into mod/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
