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
from paint_helm import paint as paint_helm  # noqa: E402
from uvmap import rasterise, read_mesh  # noqa: E402
from effective import parse_cfg  # noqa: E402

PLAY_CFG = r"D:/Backups/OneDrive/All/Documents/My Games/OpenMW/play/openmw.cfg"
FOLDER = "jy_daedric"

# Every piece names its own maps, because they do not agree across mods. The
# defaults are Daedric Lord Armor's; anything else states what it differs in.
#
#   folder      subdirectory under Textures/, "" for the root
#   spec        suffix of the specular map
#   plate_from  "spec" or "diffuse" - which map decides plate against mechanism
#   trim        "red" or "warm" - what the gold is looking for in the original
#   gold        False keeps the trim but makes it steel
#   paint       "pragmata" draws a panel layout on top; see paint_helm.py
DEFAULTS = {"folder": "", "spec": "_s", "normal": "_n", "glow": "_g",
            "plate_from": "spec", "trim": "red", "gold": True,
            "paint": None, "mesh": None}

PIECES = (
    {"stem": "daecuir", "folder": "jy_daedric"},
    {"stem": "daeboots", "folder": "jy_daedric"},
    {"stem": "daegaunt", "folder": "jy_daedric"},
    {"stem": "daegreaves", "folder": "jy_daedric"},
    {"stem": "daefacei", "folder": "jy_daedric"},
    # Faig on the Face of Terror: the colours are right, take the gold off.
    {"stem": "daefacet", "folder": "jy_daedric", "gold": False},
    {"stem": "daeneck", "folder": "jy_daedric"},
    {"stem": "daedrickatana", "folder": "jy_daedric"},
    # The closed helm Faig chose over the horned one, so that the silhouette is
    # a sealed dome rather than a face. Three things differ. Its specular map is
    # a highlight map rather than a hardness map - almost black, with a few
    # glints - so the plate mask has to come from the diffuse instead, or the
    # whole helm would be called mechanism and come out black. Its trim is gold
    # rather than red, which the red detector barely sees. And the map is named
    # `_spec`.
    # Gold off here too. Faig on the Pragmata reference: the orange was the one
    # element he did not like, so the band and the studs go to steel.
    {"stem": "tx_a_ebony_helmet", "spec": "_spec",
     "plate_from": "diffuse", "trim": "warm", "gold": False,
     # A few bold features, drawn on top. The mesh is named so its coverage can
     # be rasterised: that is what keeps the drawing on the helmet rather than
     # across the empty margins of the sheet.
     "paint": "helm", "mesh": "meshes/a/a_ebony_helmet.nif"},
)

# The palette. Four colours and two ramps: a plate lit and a plate in shadow, a
# mechanism lit and in shadow. Gold sits on top of whichever it lands on.
# Silver-grey, cool, and a step under the darkest of the four shown. The first
# pass was bone white; Faig's correction was the grey of his reference render,
# "a bit more silvery", then "a touch darker than the darkest one you offered" -
# which was 0.60. The blue channel leads, and that is what separates silver from
# grey paint.
CERAMIC = np.array([0.50, 0.525, 0.565], np.float32)   # plate, lit
CERAMIC_DARK = np.array([0.12, 0.13, 0.155], np.float32)
# Lifted off black. In game the deep recesses read as holes punched in the
# helmet rather than as a mechanism sitting behind the plates.
MECH = np.array([0.22, 0.228, 0.250], np.float32)   # what shows between plates
MECH_DARK = np.array([0.065, 0.068, 0.080], np.float32)
GOLD = np.array([1.00, 0.74, 0.32], np.float32)
GOLD_DARK = np.array([0.30, 0.20, 0.07], np.float32)

# Faig on the Face of Terror: the colours came out well, take the gold off. The
# trim does not simply disappear when it does - those lines are the design, and
# a helm with no piping reads as unfinished. It goes to a brighter, cooler metal
# instead, so the piping still separates itself from the plate it sits on.
NO_GOLD = {"daefacet"}
# Close to the plate rather than far above it. At 0.78 against a 0.50 plate the
# trim came out as blown white sashes and the helm read as black-and-white
# stripes on screen - Faig's word, twice. Trim should say "a different metal",
# not "a different object".
STEEL = np.array([0.60, 0.618, 0.655], np.float32)
STEEL_DARK = np.array([0.155, 0.163, 0.185], np.float32)


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


def _f32(a):
    """Keep arrays in float32.

    Multiplying a float32 image by a plain Python float promotes the result to
    float64 and doubles the memory for every intermediate. On a 1024x1024 sheet
    that is 8 MB a time, and this machine runs close to its commit limit - the
    generator failed on an 8 MB allocation with 2 GB of RAM free.
    """
    return np.asarray(a, dtype=np.float32)


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
                    kant=0.75, curve=1.0, gloss=0.45, gold_on=True,
                    plate_from="spec", trim_mode="red"):
    dif = load(diffuse_path)
    size = (dif.shape[1], dif.shape[0])
    spec = load(spec_path, size) if spec_path else dif

    spec_l = spec[..., :3].mean(axis=2)
    dif_l = dif[..., :3].mean(axis=2)
    # Off each map's own percentiles, so a piece the artist painted darker does
    # not come out of this darker than the rest of the suit.
    s_n = _norm(spec_l, np.percentile(spec_l, 2), np.percentile(spec_l, 98))
    d_n = _norm(dif_l, np.percentile(dif_l, 2), np.percentile(dif_l, 98))

    if plate_from == "diffuse":
        # For a piece whose specular is a highlight map, the diffuse is the only
        # thing that says where the object is at all: the unused parts of the
        # sheet are black and the shell is not.
        #
        # And the percentiles have to be taken over the object rather than the
        # sheet. Half of this helm's page is empty black, which drags the low
        # end down and leaves an already-dark ebony shell normalising to almost
        # nothing - the first attempt came out a black helmet with gold on it.
        body = dif_l > 0.02
        if body.sum() > 64:
            d_n = _norm(dif_l, np.percentile(dif_l[body], 3),
                        np.percentile(dif_l[body], 97))
            # Then put the object's midtone at mid grey. Stretching the ends is
            # not enough for a source this dark: ebony's median luminance is
            # 0.114, which survives the stretch at 0.136 and the contrast curve
            # then crushes it to 0.019 - a black helmet with gold on it, which
            # is what the first two attempts produced. One gamma fixes it, and
            # it generalises: any piece, however dark its own paint, arrives at
            # the palette in the middle of the range the palette expects.
            median = float(np.median(d_n[body]))
            if 0.02 < median < 0.98:
                d_n = d_n ** (np.log(0.5) / np.log(median))
        plate = _blur(_smooth(_norm(d_n, 0.10, 0.35)), blur)
    else:
        plate = _blur(_smooth(_norm(s_n, 0.34, 0.66)), blur)

    # A specular map that is really a highlight map is no good for tone either -
    # it is black almost everywhere, and mixing it in drags the whole piece down
    # to black. The same per-piece decision covers both.
    if plate_from == "diffuse":
        detail = 1.0
    tone = np.clip((1.0 - detail) * s_n + detail * d_n, 0.0, 1.0)
    form, fine = _split(tone, max(dif.shape[0], dif.shape[1]) / 90.0)
    tone = _f32(np.clip(form + fine * np.float32(grain), 0.0, 1.0))
    tone = _f32(_smooth(np.clip((tone - 0.5) * np.float32(contrast) + 0.5, 0.0, 1.0)))

    if normal_path and os.path.exists(normal_path):
        lit, hot = _relight(load(normal_path, size))
        tone = _f32(np.clip(
            tone * lit ** np.float32(curve)
            * (1.0 - np.float32(kant) * _kant(plate))
            + np.float32(gloss) * hot * plate, 0.0, 1.0))

    ceramic = CERAMIC_DARK + (CERAMIC - CERAMIC_DARK) * tone[..., None]
    mech = MECH_DARK + (MECH - MECH_DARK) * tone[..., None]
    body = mech + (ceramic - mech) * plate[..., None]

    if trim_mode == "warm":
        # Gold is red *and* green against little blue, so the red detector
        # barely registers it. This one finds any warm hue.
        signal = np.minimum(dif[..., 0], dif[..., 1]) - dif[..., 2]
    else:
        signal = dif[..., 0] - np.maximum(dif[..., 1], dif[..., 2])
    trim = _smooth(np.clip((signal - 0.05) / 0.13, 0.0, 1.0))
    # Gold belongs on metal. Red in the source marks the hot veins, but it also
    # marks dyed leather and cloth - the collar strap and the cuirass's fabric
    # panel are red end to end, and unqualified this turned both solid gold.
    # Weighting by the plate mask keeps the trim bright where it is inlaid into
    # armour and lets it fall back to a dull tint on everything soft.
    trim = trim * (0.22 + 0.78 * plate)
    hi, lo = (GOLD, GOLD_DARK) if gold_on else (STEEL, STEEL_DARK)
    gold = lo + (hi - lo) * np.clip(tone * 1.35 + 0.15, 0, 1)[..., None]

    rgb = body * (1.0 - trim[..., None]) + gold * trim[..., None]
    out = np.concatenate([np.clip(rgb, 0, 1), dif[..., 3:]], axis=2)
    return dif, out, plate


def convert_glow(glow_path, gold_on=True):
    """Red emissive to amber, intensity untouched.

    The artist decided where the armour glows and how brightly. That judgement
    is kept exactly; only the colour of the light changes, because in our
    fiction it is machinery running rather than something burning.
    """
    g = load(glow_path)
    intensity = g[..., :3].max(axis=2)
    tint = GOLD if gold_on else np.array([0.72, 0.84, 1.00])
    rgb = np.clip(intensity[..., None] * tint * 1.2, 0, 1)
    return g, np.concatenate([rgb, g[..., 3:]], axis=2)


def data_dirs(cfg_path, skip):
    """The load order's data directories, ours removed."""
    data, _ = parse_cfg(cfg_path)
    skip = {os.path.normcase(os.path.abspath(s)) for s in skip}
    return [d for d in data
            if os.path.normcase(os.path.abspath(d)) not in skip]


def find_texture(dirs, folder, name):
    """The file the engine would use: the last directory that has it wins."""
    hit = None
    for directory in dirs:
        for ext in (".dds", ".tga"):
            path = os.path.join(directory, "Textures", folder, name + ext)
            if os.path.exists(path):
                hit = path
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
    ap.add_argument("--grain", type=float, default=1.0,
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
    dirs = data_dirs(args.config, skip=[out_root])
    os.makedirs(args.preview_dir, exist_ok=True)

    rows, written = [], 0
    for spec_row in PIECES:
        p = dict(DEFAULTS, **spec_row)
        stem, folder = p["stem"], p["folder"]
        diffuse = find_texture(dirs, folder, stem)
        if not diffuse:
            print(f"  ! not in the load order, skipped: {folder}/{stem}")
            continue
        out_dir = os.path.join(out_root, "Textures", folder)
        if args.write:
            os.makedirs(out_dir, exist_ok=True)
        specular = find_texture(dirs, folder, stem + p["spec"])
        normal = find_texture(dirs, folder, stem + p["normal"])
        glow = find_texture(dirs, folder, stem + p["glow"]) if p["glow"] else None

        before, after, plate = convert_diffuse(
            diffuse, specular, args.contrast, args.blur, args.grain,
            args.detail, normal, args.kant, args.curve, args.gloss,
            p["gold"], p["plate_from"], p["trim"])
        if p["paint"] == "helm":
            _pos, cover = rasterise(*read_mesh(p["mesh"], args.config),
                                    after.shape[0])
            after = paint_helm(after, _blur(cover, 1.0))
        panels = [("before", before), ("AFTER", after),
                  ("plate mask", np.dstack([plate] * 3))]
        note = ""
        if glow:
            g_before, g_after = convert_glow(glow, p["gold"])
            panels.append(("glow AFTER", g_after))
            note = " + glow"
        rows.append([stem] + panels)
        print(f"  {stem:22} {before.shape[1]}x{before.shape[0]}"
              f"{'' if specular else '  (no specular)'}{note}")
        if args.write:
            # Opaque, and the originals are DXT1. Same format, same footprint.
            write_dxt(os.path.join(out_dir, stem + ".dds"), after * 255.0, "dxt1")
            written += 1
            if glow:
                write_dxt(os.path.join(out_dir, stem + p["glow"] + ".dds"),
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
