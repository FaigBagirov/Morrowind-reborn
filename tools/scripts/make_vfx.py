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


def _hex_distance(x, y, cx, cy, angle):
    """Distance to a flat-topped hexagon centred at (cx, cy), rotated by angle.

    max of the three flat-normal projections. No trigonometry per pixel beyond
    the one rotation, and the six sides stay straight - which is the point: a
    blob does not read as manufactured, and manufactured is the whole idea.
    """
    ca, sa = np.cos(angle), np.sin(angle)
    dx = x - cx
    dy = y - cy
    px = np.abs(dx * ca - dy * sa)
    py = np.abs(dx * sa + dy * ca)
    return np.maximum(px * 0.8660254 + py * 0.5, py)


def _segment_distance(x, y, ax, ay, bx, by):
    """Distance from each pixel to the segment AB."""
    vx, vy = bx - ax, by - ay
    length2 = vx * vx + vy * vy
    if length2 < 1e-6:
        return np.hypot(x - ax, y - ay)
    t = np.clip(((x - ax) * vx + (y - ay) * vy) / length2, 0.0, 1.0)
    return np.hypot(x - (ax + t * vx), y - (ay + t * vy))


def hex_field(size, cell, dense, seed):
    """Plates, filaments and motes.

    Three passes, and each is there for a reason the first draft got wrong:

    * **Plates, not blobs.** The hexagon is drawn as a bright rim with a dim
      interior, and the rim is only a couple of pixels of falloff wide. A filled
      soft hexagon reads as a smudge at particle size; an outlined one keeps its
      six sides. Each plate is rotated a little so the field is not a lattice.
    * **Filaments.** Short tapering threads between neighbouring plates. This is
      what makes it read as a swarm with something holding it together rather
      than as confetti.
    * **Motes.** Sub-pixel specks in the gaps, at low alpha. They fill the empty
      space without adding structure, and they are what stops the gaps looking
      deliberate.
    """
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    plates = np.zeros((size, size), np.float32)
    threads = np.zeros((size, size), np.float32)
    motes = np.zeros((size, size), np.float32)

    dx = cell * 1.5
    dy = cell * np.sqrt(3.0)
    centres = []
    for r in range(-1, int(size / dy) + 2):
        for c in range(-1, int(size / dx) + 2):
            cx = c * dx + rng.uniform(-cell * 0.2, cell * 0.2)
            cy = r * dy + (dy * 0.5 if c % 2 else 0.0)
            cy += rng.uniform(-cell * 0.2, cell * 0.2)
            if -cell < cx < size + cell and -cell < cy < size + cell:
                # Wide size variation. A field of one-size plates reads as a
                # pattern; nanites are a population, not a print.
                scale = rng.choice([0.16, 0.24, 0.34], p=[0.45, 0.35, 0.20])
                # Corprus is the same material, damaged. Half its plates lose a
                # side or two, which healthy casting never shows - that is the
                # distinction Part 9 wanted, made of shape rather than density.
                broken = ()
                if dense and rng.random() < 0.55:
                    broken = tuple(rng.choice(6, size=rng.integers(1, 3),
                                              replace=False))
                centres.append((cx, cy, scale * cell * rng.uniform(0.85, 1.15),
                                rng.uniform(0.0, np.pi / 3), broken))

    edge = max(size / 512.0, 1.0) * (1.1 if dense else 1.4)
    for cx, cy, radius, angle, broken in centres:
        d = _hex_distance(x, y, cx, cy, angle)
        rim = np.clip(1.0 - np.abs(d - radius) / edge, 0.0, 1.0)
        fill = np.clip((radius - d) / (radius * 0.9), 0.0, 1.0) ** 2
        if broken:
            # Which of the six sides a pixel belongs to, in the plate's own
            # frame. Knock out the chosen ones and the plate reads as a piece
            # of something rather than a shape.
            theta = np.arctan2(y - cy, x - cx) - angle
            sector = np.floor(((theta + np.pi) % (2 * np.pi))
                              / (np.pi / 3)).astype(np.int8)
            keep = np.ones_like(rim)
            for side in broken:
                keep[sector == side] = 0.0
            rim = rim * keep
            fill = fill * 0.35
        plates = np.maximum(plates, rim * rim * (3 - 2 * rim))
        plates = np.maximum(plates, fill * (0.30 if dense else 0.22))

    # Filaments: each plate reaches for one or two neighbours, never all of
    # them - a fully connected mesh reads as a net rather than as a swarm.
    width = max(size / 512.0, 0.6) * (1.3 if dense else 1.1)
    for i, (cx, cy, radius, _a, _brk) in enumerate(centres):
        near = sorted(
            ((np.hypot(cx - ox, cy - oy), ox, oy)
             for j, (ox, oy, _r, _b, _k) in enumerate(centres) if j != i),
            key=lambda t: t[0])[:3]
        for dist, ox, oy in near[:rng.integers(1, 3)]:
            if dist > cell * 2.2:
                continue
            d = _segment_distance(x, y, cx, cy, ox, oy)
            line = np.clip(1.0 - d / width, 0.0, 1.0)
            along = np.clip(1.0 - _segment_distance(x, y, cx, cy, cx, cy)
                            / (dist + 1e-3), 0.0, 1.0)
            threads = np.maximum(threads, line * (0.44 + 0.26 * along))

    for _ in range(int(size * (3.0 if dense else 1.8))):
        mx, my = rng.uniform(0, size, 2)
        rad = rng.uniform(0.6, 1.8) * max(size / 512.0, 1.0)
        d = np.hypot(x - mx, y - my)
        motes = np.maximum(motes, np.clip(1.0 - d / rad, 0.0, 1.0)
                           * rng.uniform(0.12, 0.34))

    return np.clip(plates + threads * (1.0 - plates) * 0.95
                   + motes * (1.0 - plates), 0.0, 1.0)


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


def build(src_path, dense, size=512):
    src = np.array(Image.open(src_path).convert("RGBA")).astype(np.float32)
    lum = src[..., :3].mean(axis=2)
    bright = lum > 8
    if bright.sum() < 64:
        bright = lum > lum.mean()
    # The light this effect already has, taken from its own brightest pixels.
    colour = src[..., :3][bright].mean(axis=0)
    colour = colour / max(colour.max(), 1.0) * 255.0

    # Small and many. The first pass put five plates across the texture, which
    # at particle size is a handful of slabs - Faig's word was megaliths, and he
    # was right. A swarm has to be a population: roughly twenty across for
    # casting and thirty for Corprus, so a single plate lands on a few pixels of
    # screen and the eye reads the cloud rather than the pieces.
    cell = size / 30.0 if dense else size / 20.0
    field = hex_field(size, cell, dense, seed=7)

    # A faint core keeps the particle from disappearing at distance, where the
    # grid is below a pixel and would otherwise flicker out.
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    core = np.clip(1.0 - r, 0.0, 1.0) ** 4 * (0.18 if dense else 0.10)

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
    ap.add_argument("--profile", choices=["vanilla", "momw"], default="momw",
                    help="which installed textures to take the colour from")
    ap.add_argument("--source", default=None)
    ap.add_argument("--preview-dir", default=os.path.join(root, "tools", "vfx"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    # Two builds for the same reason the plugin has two: what is installed
    # underneath differs, and the colour is sampled from it.
    if args.source is None:
        args.source = (
            os.path.join(root, "tools", "build", "vfx-src-vanilla")
            if args.profile == "vanilla" else
            r"D:\Games\OpenMWMods\graphics-overhaul\TexturePacks"
            r"\VurtsMorrowindVisualResurgence\vfx\Data Files\Textures")
    if args.out is None:
        args.out = os.path.join(root, "tools", "build",
                                f"vfx-{args.profile}", "Textures")
    args.preview_dir = os.path.join(args.preview_dir, args.profile)

    os.makedirs(args.preview_dir, exist_ok=True)
    if args.write:
        os.makedirs(args.out, exist_ok=True)

    for name, effects in TARGETS.items():
        src = os.path.join(args.source, name + ".dds")
        if not os.path.exists(src):
            print(f"  missing source, skipped: {name}")
            continue
        rgba = build(src, name in DENSE, args.size)
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
