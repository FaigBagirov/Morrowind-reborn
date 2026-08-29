#!/usr/bin/env python3
"""Retexture the Zenaric armour: white ceramic plate, dark mechanism, gold trim.

    python tools/scripts/make_armour.py            # PNG contact sheets only
    python tools/scripts/make_armour.py --write    # also the .dds into tools/build

**Textures only. No geometry.** Canon Part 9 and the project rules both forbid
generating NIFs - the engine validates models on load and rejects
machine-assembled ones. So the silhouette stays what it is: the spikes, the
horned helm, the sculpted plates. That is not a limitation here, it is the
brief. Faig asked for the reference look *with notes of the original Daedric
armour*, and the notes are exactly what the mesh and its normal map already
carry, for free.

What changes is the material. Daedric armour is charcoal chitin with red-hot
veins; Zenaric armour is manufactured - pale ceramic plate over a dark
mechanism, with gold at every joint and seam, and the emissive lines amber
rather than red.

## Where the structure comes from

The diffuse is nearly useless as a source of tone: median luminance 0.094, p90
0.191, so the whole sculpt lives in a narrow dark band and stretching it alone
amplifies compression noise into dirt.

The **specular map** is where the information is - mean 0.244, p25 0.110, p75
0.353 - and it carries the same sculpt. More than that, it carries a judgement
we would otherwise have to guess: the artist painted hard armour bright and
cloth, leather and mail dark, so it separates plate from underlayer better than
anything we could infer. `plate` is built from it, and it decides whether a
pixel becomes ceramic or mechanism.

Tone mixes both - the specular for range and the diffuse for fine grain.

Gold goes where the original is red-dominant, which is precisely the trim, the
veins and the seams the artist already picked out. Nothing is placed by hand.

## What is not touched

`_n` and `_s` are not written at all, so the mod's own normal and specular maps
keep being used - our data directory only overrides the files it contains. The
sculpt and the gloss are the original artist's, and they are the best part.

Dremora skin (`DremoraNeck`, `DremoraEars`, `daefacehair`) is deliberately left
alone: that is a creature's body, not equipment, and turning it white is a
separate decision about what the Zenar look like.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dds import write_dxt  # noqa: E402
from effective import parse_cfg  # noqa: E402

PLAY_CFG = r"D:/Backups/OneDrive/All/Documents/My Games/OpenMW/play/openmw.cfg"
FOLDER = "jy_daedric"

# The worn set from Daedric Lord Armor, plus the weapon it ships. Every one of
# these has a specular map, which is what the conversion runs on.
PIECES = ("daecuir", "daeboots", "daegaunt", "daegreaves",
          "daefacei", "daefacet", "daeneck", "daedrickatana")

# The palette. Four colours and two ramps: a plate lit and a plate in shadow, a
# mechanism lit and in shadow. Gold sits on top of whichever it lands on.
# Silver-grey, cool, and a step under the darkest of the four shown. The first
# pass was bone white; Faig's correction was the grey of his reference render,
# "a bit more silvery", then "a touch darker than the darkest one you offered" -
# which was 0.60. The blue channel leads, and that is what separates silver from
# grey paint.
CERAMIC = np.array([0.50, 0.525, 0.565])   # plate, lit
CERAMIC_DARK = np.array([0.12, 0.13, 0.155])
MECH = np.array([0.16, 0.165, 0.185])     # what shows between the plates
MECH_DARK = np.array([0.030, 0.032, 0.038])
GOLD = np.array([1.00, 0.74, 0.32])
GOLD_DARK = np.array([0.30, 0.20, 0.07])


def load(path, size=None):
    im = Image.open(path).convert("RGBA")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.array(im).astype(np.float32) / 255.0


def _norm(a, lo, hi):
    return np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0)


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def _blur(mask, radius):
    """Take the speckle out of the plate mask.

    Thresholding a compressed specular map leaves salt-and-pepper wherever it
    sits near the crossover, and on a large flat plate that reads as dirt rather
    than as material.
    """
    im = Image.fromarray((mask * 255).astype(np.uint8))
    return np.array(im.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255.0


def _split(tone, radius):
    """Large-scale form, and the fine grain riding on it.

    The artist's fine veining is grunge painted on charcoal, where it barely
    shows. Stretched to a white plate it becomes a black web and the piece reads
    as cracked porcelain rather than as a material. Low-passing the tone keeps
    the sculpted form and lets the grain be dialled down without flattening the
    plate into plastic.
    """
    im = Image.fromarray(np.clip(tone * 255, 0, 255).astype(np.uint8))
    form = np.array(im.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255.0
    return form, tone - form


def _kant(plate, blur=1.4, gain=7.0):
    """The dark outline every plate should have.

    Faig asked for the edges and piping to darken. The normal map's own tilt is
    the obvious candidate and it is the wrong one: on this sculpt almost nothing
    is flat, so darkening by tilt just darkens everything evenly. The plate
    mask's *boundary* is what reads as an edge - one plate ending and the next
    beginning - so the gradient of the mask is the line to draw on.
    """
    gy, gx = np.gradient(plate)
    return _blur(np.clip(np.hypot(gx, gy) * gain, 0.0, 1.0), blur)


def _relight(normal_map, tighten=18.0):
    """A fake light baked into the diffuse, from the mod's own normal map.

    Two terms out of one dot product: a broad one that makes a plate read as
    curved rather than flat, and a tight one for the glint. It is not lighting -
    the engine does that - it is the sheen of the material, so it is kept low
    enough that the real light still leads.
    """
    n = normal_map[..., :3] * 2.0 - 1.0
    light = np.array([-0.42, 0.46, 0.78])
    light = light / np.linalg.norm(light)
    ndl = np.clip((n * light).sum(axis=2), 0.0, 1.0)
    return 0.55 + 0.45 * ndl, ndl ** tighten


def convert_diffuse(diffuse_path, spec_path, contrast=1.15, blur=1.6,
                    grain=0.35, detail=0.25, normal_path=None,
                    kant=0.75, curve=1.0, gloss=0.45):
    dif = load(diffuse_path)
    size = (dif.shape[1], dif.shape[0])
    spec = load(spec_path, size) if spec_path else dif

    spec_l = spec[..., :3].mean(axis=2)
    dif_l = dif[..., :3].mean(axis=2)
    # Off each map's own percentiles, so a piece the artist painted darker does
    # not come out of this darker than the rest of the suit.
    s_n = _norm(spec_l, np.percentile(spec_l, 2), np.percentile(spec_l, 98))
    d_n = _norm(dif_l, np.percentile(dif_l, 2), np.percentile(dif_l, 98))

    plate = _blur(_smooth(_norm(s_n, 0.34, 0.66)), blur)

    tone = np.clip((1.0 - detail) * s_n + detail * d_n, 0.0, 1.0)
    form, fine = _split(tone, max(dif.shape[0], dif.shape[1]) / 90.0)
    tone = np.clip(form + fine * grain, 0.0, 1.0)
    tone = _smooth(np.clip((tone - 0.5) * contrast + 0.5, 0.0, 1.0))

    if normal_path and os.path.exists(normal_path):
        lit, hot = _relight(load(normal_path, size))
        tone = np.clip(tone * lit ** curve * (1.0 - kant * _kant(plate))
                       + gloss * hot * plate, 0.0, 1.0)

    ceramic = CERAMIC_DARK + (CERAMIC - CERAMIC_DARK) * tone[..., None]
    mech = MECH_DARK + (MECH - MECH_DARK) * tone[..., None]
    body = mech + (ceramic - mech) * plate[..., None]

    redness = dif[..., 0] - np.maximum(dif[..., 1], dif[..., 2])
    trim = _smooth(np.clip((redness - 0.05) / 0.13, 0.0, 1.0))
    # Gold belongs on metal. Red in the source marks the hot veins, but it also
    # marks dyed leather and cloth - the collar strap and the cuirass's fabric
    # panel are red end to end, and unqualified this turned both solid gold.
    # Weighting by the plate mask keeps the trim bright where it is inlaid into
    # armour and lets it fall back to a dull tint on everything soft.
    trim = trim * (0.22 + 0.78 * plate)
    gold = GOLD_DARK + (GOLD - GOLD_DARK) * np.clip(tone * 1.35 + 0.15, 0, 1)[..., None]

    rgb = body * (1.0 - trim[..., None]) + gold * trim[..., None]
    out = np.concatenate([np.clip(rgb, 0, 1), dif[..., 3:]], axis=2)
    return dif, out, plate


def convert_glow(glow_path):
    """Red emissive to amber, intensity untouched.

    The artist decided where the armour glows and how brightly. That judgement
    is kept exactly; only the colour of the light changes, because in our
    fiction it is machinery running rather than something burning.
    """
    g = load(glow_path)
    intensity = g[..., :3].max(axis=2)
    rgb = np.clip(intensity[..., None] * GOLD * 1.2, 0, 1)
    return g, np.concatenate([rgb, g[..., 3:]], axis=2)


def find_folder(cfg_path, skip):
    """The last data directory in the load order holding Textures/jy_daedric."""
    data, _ = parse_cfg(cfg_path)
    skip = {os.path.normcase(os.path.abspath(s)) for s in skip}
    hit = None
    for directory in data:
        if os.path.normcase(os.path.abspath(directory)) in skip:
            continue
        candidate = os.path.join(directory, "Textures", FOLDER)
        if os.path.isdir(candidate):
            hit = candidate
    return hit


def sheet(rows, path, width=430, height=215):
    from PIL import ImageDraw
    cols = max(len(r) - 1 for r in rows)
    img = Image.new("RGB", (cols * (width + 4) + 4,
                            len(rows) * (height + 26) + 4), (18, 18, 18))
    draw = ImageDraw.Draw(img)
    for r, row in enumerate(rows):
        stem, panels = row[0], row[1:]
        y = r * (height + 26) + 22
        for c, (label, arr) in enumerate(panels):
            tile = Image.fromarray((arr[..., :3] * 255).astype(np.uint8))
            img.paste(tile.resize((width, height)), (c * (width + 4) + 4, y))
            draw.text((c * (width + 4) + 8, y - 16), f"{stem}  {label}",
                      fill=(220, 220, 220))
    img.save(path)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", default="momw")
    ap.add_argument("--config", default=PLAY_CFG)
    ap.add_argument("--out", default=None)
    ap.add_argument("--preview-dir", default=os.path.join(root, "tools", "armour"))
    ap.add_argument("--contrast", type=float, default=1.15)
    ap.add_argument("--grain", type=float, default=0.35,
                    help="how much of the original fine veining survives")
    ap.add_argument("--detail", type=float, default=0.25,
                    help="diffuse weight in the tone; the rest is specular")
    ap.add_argument("--kant", type=float, default=0.75,
                    help="how dark the outline around each plate goes")
    ap.add_argument("--curve", type=float, default=1.0,
                    help="broad baked light, so a plate reads as curved")
    ap.add_argument("--gloss", type=float, default=0.45,
                    help="the tight highlight; the sheen")
    ap.add_argument("--blur", type=float, default=1.6)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    out_root = args.out or os.path.join(root, "tools", "build",
                                        f"armour-{args.profile}")
    out_dir = os.path.join(out_root, "Textures", FOLDER)
    src = find_folder(args.config, skip=[out_root])
    if not src:
        raise SystemExit(f"no Textures/{FOLDER} in the load order - is Daedric "
                         f"Lord Armor installed?")
    print(f"source: {src}")

    os.makedirs(args.preview_dir, exist_ok=True)
    if args.write:
        os.makedirs(out_dir, exist_ok=True)

    rows, written = [], 0
    for stem in PIECES:
        diffuse = os.path.join(src, stem + ".dds")
        if not os.path.exists(diffuse):
            print(f"  ! missing, skipped: {stem}")
            continue
        spec = os.path.join(src, stem + "_s.dds")
        before, after, plate = convert_diffuse(
            diffuse, spec if os.path.exists(spec) else None,
            args.contrast, args.blur, args.grain, args.detail,
            os.path.join(src, stem + "_n.dds"),
            args.kant, args.curve, args.gloss)
        panels = [("before", before), ("AFTER", after),
                  ("plate mask", np.dstack([plate] * 3))]
        note = ""
        glow = os.path.join(src, stem + "_g.dds")
        if os.path.exists(glow):
            g_before, g_after = convert_glow(glow)
            panels.append(("glow AFTER", g_after))
            note = " + glow"
        rows.append([stem] + panels)
        print(f"  {stem:16} {before.shape[1]}x{before.shape[0]}{note}")
        if args.write:
            # Opaque, and the originals are DXT1. Same format, same footprint.
            write_dxt(os.path.join(out_dir, stem + ".dds"),
                      after * 255.0, "dxt1")
            written += 1
            if os.path.exists(glow):
                write_dxt(os.path.join(out_dir, stem + "_g.dds"),
                          g_after * 255.0, "dxt1")
                written += 1

    sheet(rows, os.path.join(args.preview_dir, f"armour-{args.profile}.png"))
    print(f"\ncontact sheet: "
          f"{os.path.join(args.preview_dir, f'armour-{args.profile}.png')}")
    if args.write:
        print(f"{written} textures written to {out_dir}")
        print("Add one line to the profile's openmw.cfg:")
        print(f'    data="{out_root.replace(os.sep, "/")}"')
    else:
        print("Preview only. Nothing was written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
