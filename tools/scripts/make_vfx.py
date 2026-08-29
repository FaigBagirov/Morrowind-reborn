#!/usr/bin/env python3
"""Generate the Zenaric particle textures: hexagons in alpha, nothing in geometry.

    python tools/scripts/make_vfx.py --preview      # PNG previews only
    python tools/scripts/make_vfx.py --write        # also the .dds into tools/build

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

**Coverage.** The first pass shipped the six textures with the highest effect
counts. Faig's read of it in game was that only the summons had changed, and the
arithmetic says why: six files are 85 of 142 effects, so well over a third of
the game's casting still looked vanilla. A conversion that covers some of the
schools reads as a bug rather than as a style. The target list is therefore
taken from the masters - every texture any magic effect names - instead of being
a hand-picked top six.
"""

import argparse
import collections
import io
import os
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dds import write_bgra, write_dxt  # noqa: E402
from bsa import find, open_archives  # noqa: E402
from effective import parse_cfg  # noqa: E402
from wo1_survey import stream_records  # noqa: E402

MASTERS = ("Morrowind.json", "Tribunal.json", "Bloodmoon.json")
BSA_DIR = r"D:/ProgramFiles/Steam/steamapps/common/Morrowind/Data Files"
PLAY_CFG = r"D:/Backups/OneDrive/All/Documents/My Games/OpenMW/play/openmw.cfg"

DENSE = {"vfx_corprus"}          # Canon Part 9 reserves the swarm for Corprus.

# How many plates across the texture, sparse and dense.
#
# Faig's note after seeing the first iteration in game was: smaller. The floor
# on that is set by the rim, not by taste - a plate needs roughly four pixels of
# radius before six straight sides read at all, so past about thirty across at
# 512 the hexagons flatten into rings and then into grit. Measured on a strip of
# 20 / 26 / 32 / 40; 40 was crumbs.
#
# The way under the floor is resolution rather than cell size. At 1024 a plate
# with the same pixel crispness covers half as much of the texture, so 36 across
# is finer than 20 was and still hexagonal. DXT5 pays for the resolution: 1024
# compressed is the same file as 512 uncompressed used to be.
PLATES = {False: 36, True: 54}

# `tx_firealpha00a` is the one texture a magic effect names that is not a magic
# texture. The `tx_` prefix is Bethesda's for ordinary world surfaces, and where
# it resolves says the rest: not in Vurt's vfx pack but in Morrowind Enhanced
# Textures, a landscape and architecture pack. It is the flame sheet - torches,
# braziers, campfires - and one magic effect, Light, happens to borrow it.
# Overriding it would put hexagons on every fire in the game in order to convert
# a single spell. Left alone; `tools/reports/vfx.md` records the way to reach
# Light without touching it.
EXCLUDE = {"tx_firealpha00a": "world flame texture, shared with every fire"}

# The way to reach Light without overwriting the flame sheet: generate a private
# copy under a name nothing else uses, and point the effect record at it from
# the load context. The colour is still sampled from the flame, so Light keeps
# the warm light it has always had. `mod/scripts/rewrite/apply.lua` does the
# redirect, guarded - if the engine refuses the write, Light stays vanilla and
# nothing else is affected.
REDIRECT = {"vfx_zen_light": "tx_firealpha00a"}


def effect_textures(cache_dir):
    """{texture stem: [effect ids]}, from the masters, the last master winning.

    An effect an expansion redefines is one effect, not two, and the texture
    that counts is the one the last definition names.
    """
    latest = {}
    for name in MASTERS:
        path = os.path.join(cache_dir, name)
        if not os.path.exists(path):
            continue
        for rec in stream_records(path):
            if rec.get("type") != "MagicEffect":
                continue
            texture = str(rec.get("texture") or "").strip().lower()
            if texture:
                latest[str(rec.get("effect_id"))] = os.path.splitext(texture)[0]
    out = collections.defaultdict(list)
    for effect, stem in sorted(latest.items()):
        out[stem].append(effect)
    return out


def installed_sources(stems, cfg_path, skip):
    """Where each texture resolves in the player's own load order.

    The engine takes the last data directory that has the file, so this does the
    same. Our own output directories are skipped: they are listed in that config
    too, and sampling the colour out of the file we generated last time would
    walk the palette a little further from the mod's every time it is run.
    """
    data, _ = parse_cfg(cfg_path)
    skip = {os.path.normcase(os.path.abspath(s)) for s in skip}
    found = {}
    for directory in data:
        if os.path.normcase(os.path.abspath(directory)) in skip:
            continue
        try:
            present = {f.lower(): f
                       for f in os.listdir(os.path.join(directory, "Textures"))}
        except OSError:
            continue
        for stem in stems:
            for ext in (".dds", ".tga", ".png"):
                hit = present.get(stem + ext)
                if hit:
                    found[stem] = os.path.join(directory, "Textures", hit)
                    break
    return found


def vanilla_sources(stems, bsa_dir, out_dir):
    """The vanilla originals, extracted out of the three BSAs and cached."""
    archives = open_archives([os.path.join(bsa_dir, n) for n in
                              ("Morrowind.bsa", "Tribunal.bsa", "Bloodmoon.bsa")])
    os.makedirs(out_dir, exist_ok=True)
    found = {}
    for stem in stems:
        for ext in (".dds", ".tga"):
            hit = find(archives, "textures/" + stem + ext)
            if hit:
                archive, name = hit
                path = os.path.join(out_dir, stem + ext)
                if not os.path.exists(path):
                    with open(path, "wb") as f:
                        f.write(archive.read(name))
                found[stem] = path
                break
    for archive in archives:
        archive.close()
    return found


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


def _window(cx, cy, reach, size):
    """The slice pair covering a square of half-side `reach` around (cx, cy)."""
    x0 = max(int(np.floor(cx - reach)), 0)
    x1 = min(int(np.ceil(cx + reach)) + 1, size)
    y0 = max(int(np.floor(cy - reach)), 0)
    y1 = min(int(np.ceil(cy + reach)) + 1, size)
    if x1 <= x0 or y1 <= y0:
        return None
    return (slice(y0, y1), slice(x0, x1))


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
        # Only the pixels a plate can reach. The first version evaluated every
        # plate, thread and mote over the whole canvas, which at 512 was merely
        # slow and at 1024 was ten minutes a profile. A plate contributes where
        # `rim` is non-zero, so within hexagon distance radius + edge; hexagon
        # distance is never below 0.866 of the euclidean one, so dividing by
        # that cannot clip a contributing pixel. Measured against the old code:
        # one colour byte in 1,048,576 lands a level apart, none in alpha.
        w = _window(cx, cy, (radius + edge) / 0.8660254 + 2.0, size)
        if w is None:
            continue
        xs, ys = x[w], y[w]
        d = _hex_distance(xs, ys, cx, cy, angle)
        rim = np.clip(1.0 - np.abs(d - radius) / edge, 0.0, 1.0)
        fill = np.clip((radius - d) / (radius * 0.9), 0.0, 1.0) ** 2
        if broken:
            # Which of the six sides a pixel belongs to, in the plate's own
            # frame. Knock out the chosen ones and the plate reads as a piece
            # of something rather than a shape.
            theta = np.arctan2(ys - cy, xs - cx) - angle
            sector = np.floor(((theta + np.pi) % (2 * np.pi))
                              / (np.pi / 3)).astype(np.int8)
            keep = np.ones_like(rim)
            for side in broken:
                keep[sector == side] = 0.0
            rim = rim * keep
            fill = fill * 0.35
        np.maximum(plates[w], rim * rim * (3 - 2 * rim), out=plates[w])
        np.maximum(plates[w], fill * (0.30 if dense else 0.22), out=plates[w])

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
            # A square on the segment's midpoint, half-side half the length plus
            # the thread width, holds every pixel the thread can reach.
            w = _window((cx + ox) / 2.0, (cy + oy) / 2.0,
                        dist / 2.0 + width + 2.0, size)
            if w is None:
                continue
            xs, ys = x[w], y[w]
            d = _segment_distance(xs, ys, cx, cy, ox, oy)
            line = np.clip(1.0 - d / width, 0.0, 1.0)
            along = np.clip(1.0 - _segment_distance(xs, ys, cx, cy, cx, cy)
                            / (dist + 1e-3), 0.0, 1.0)
            np.maximum(threads[w], line * (0.44 + 0.26 * along), out=threads[w])

    for _ in range(int(size * (3.0 if dense else 1.8))):
        mx, my = rng.uniform(0, size, 2)
        rad = rng.uniform(0.6, 1.8) * max(size / 512.0, 1.0)
        amp = rng.uniform(0.12, 0.34)
        w = _window(mx, my, rad + 2.0, size)
        if w is None:
            continue
        d = np.hypot(x[w] - mx, y[w] - my)
        np.maximum(motes[w], np.clip(1.0 - d / rad, 0.0, 1.0) * amp,
                   out=motes[w])

    return np.clip(plates + threads * (1.0 - plates) * 0.95
                   + motes * (1.0 - plates), 0.0, 1.0)


def load_rgba(path):
    with open(path, "rb") as f:
        return np.array(Image.open(io.BytesIO(f.read())).convert("RGBA"),
                        dtype=np.float32)


def build(src, field, dense, size=512):
    """One texture: the shared hexagon field, wearing this effect's own light.

    The field is one array for every sparse texture and a second one for
    Corprus. That is not a shortcut, it is the fiction - one technology has one
    structure. What differs between schools is the light it is lit by, and that
    is sampled from what is installed rather than chosen.
    """
    lum = src[..., :3].mean(axis=2)
    bright = lum > 8
    if bright.sum() < 64:
        bright = lum > lum.mean()
    # The light this effect already has, taken from its own brightest pixels.
    colour = src[..., :3][bright].mean(axis=0)
    colour = colour / max(colour.max(), 1.0) * 255.0

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


def emit(path, rgba, fmt):
    """Write one texture, mipmapped either way.

    Mips are not a separate command any more. Without them the GPU samples a
    full-size texture for a particle a few pixels across and it shimmers as the
    particle moves - and a second command is a step that gets forgotten, which
    is how 36 mipless textures nearly shipped once already.
    """
    if fmt == "dxt5":
        write_dxt(path, rgba, "dxt5")
    else:
        write_bgra(path, rgba)


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
    ap.add_argument("--config", default=PLAY_CFG,
                    help="the openmw.cfg whose load order resolves the sources")
    ap.add_argument("--bsa-dir", default=BSA_DIR)
    ap.add_argument("--cache-dir", default=os.path.join(root, "tools", "cache"))
    ap.add_argument("--preview-dir", default=os.path.join(root, "tools", "vfx"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--format", choices=["dxt5", "rgba"], default="dxt5",
                    help="dxt5 keeps 1024 at the cost 512 uncompressed had")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    if args.out is None:
        args.out = os.path.join(root, "tools", "build",
                                f"vfx-{args.profile}", "Textures")
    preview_dir = os.path.join(args.preview_dir, args.profile)

    effects = effect_textures(args.cache_dir)
    total = sum(len(v) for v in effects.values())
    stems = sorted(s for s in effects if s not in EXCLUDE)
    print(f"{total} magic effects name {len(effects)} textures")
    for stem in sorted(s for s in effects if s in EXCLUDE):
        print(f"  excluded: {stem:22} {EXCLUDE[stem]} "
              f"({len(effects[stem])} effect: "
              f"{', '.join(effects[stem])})")

    # Two builds for the same reason the plugin has two: what is installed
    # underneath differs, and the colour is sampled from it.
    lookup = stems + sorted(set(REDIRECT.values()) - set(stems))
    if args.profile == "momw":
        sources = installed_sources(
            lookup, args.config,
            skip=[os.path.join(root, "tools", "build", "vfx-momw"),
                  os.path.join(root, "tools", "build", "vfx-vanilla")])
    else:
        sources = vanilla_sources(
            lookup, args.bsa_dir,
            os.path.join(root, "tools", "build", "vfx-src-vanilla"))

    os.makedirs(preview_dir, exist_ok=True)
    if args.write:
        os.makedirs(args.out, exist_ok=True)

    fields, covered, written = {}, 0, 0
    for stem in stems:
        src_path = sources.get(stem)
        if not src_path:
            print(f"  ! no source found, skipped: {stem}")
            continue
        dense = stem in DENSE
        if dense not in fields:
            # Small and many. The first pass put five plates across the texture,
            # which at particle size is a handful of slabs - Faig's word was
            # megaliths, and he was right. A swarm has to be a population, so a
            # single plate lands on a few pixels of screen and the eye reads the
            # cloud rather than the pieces. PLATES carries the count and why.
            cell = args.size / float(PLATES[dense])
            fields[dense] = hex_field(args.size, cell, dense, seed=7)
        src = load_rgba(src_path)
        rgba = build(src, fields[dense], dense, args.size)
        preview(rgba, os.path.join(preview_dir, stem + ".png"))
        preview(src, os.path.join(preview_dir, stem + "-before.png"))
        covered += len(effects[stem])
        kind = "dense (Corprus)" if dense else "sparse"
        origin = os.path.basename(os.path.dirname(os.path.dirname(src_path)))
        print(f"  {stem:22} {len(effects[stem]):3} effects  {kind:16} {origin}")
        if args.write:
            emit(os.path.join(args.out, stem + ".dds"), rgba, args.format)
            written += 1
    for name, borrowed in sorted(REDIRECT.items()):
        src_path = sources.get(borrowed)
        if not src_path:
            print(f"  ! no source found, skipped: {name} (from {borrowed})")
            continue
        rgba = build(load_rgba(src_path), fields[False], False, args.size)
        preview(rgba, os.path.join(preview_dir, name + ".png"))
        print(f"  {name:22} {len(effects.get(borrowed, [])):3} effects  "
              f"{'redirect':16} colour from {borrowed}")
        if args.write:
            emit(os.path.join(args.out, name + ".dds"), rgba, args.format)
            written += 1
            covered += len(effects.get(borrowed, []))

    print(f"\n{covered} of {total} magic effects converted, "
          f"{written} textures written at {args.size}px {args.format}")
    if not args.write:
        print("Preview only. Nothing was written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
