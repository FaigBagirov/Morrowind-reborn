#!/usr/bin/env python3
"""Ship the model's own colours, not a drained copy of them.

    python tools/scripts/model_textures.py model.glb --out <armour dir>

The imported suit went into the game grey, and the black patches Faig kept
reporting were not holes and not the geometry: they were the **navy panels of
the original, crushed to nothing** by a recolouring built for the Daedric atlas.
Measured against the author's own sheet, mean luminance had fallen from 141 to
70 and saturation from 0.146 to 0.102.

The author painted white plate, gold on the horns and the emblem and the belt,
and a dark navy tabard. That is what the reference images show and it is what
this writes: the base-colour texture of each primitive we actually use, straight
out of the GLB, as DDS with mipmaps.

Recolouring to the conversion's palette is a separate question and a later one.
It must start from this rather than from a grey sheet, and it must keep the
tonal range - the mistake the first pass made was to treat a dark colour as
something to remove.
"""

import argparse
import io
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dds import write_dxt  # noqa: E402
from glb import Gltf  # noqa: E402


def images(model):
    """Every embedded image, decoded."""
    out = []
    for entry in model.json.get("images", []):
        view = model.json["bufferViews"][entry["bufferView"]]
        start = view.get("byteOffset", 0)
        out.append(Image.open(io.BytesIO(
            model.bin[start:start + view["byteLength"]])).convert("RGB"))
    return out


def base_colour(model, prim):
    """Which image index a primitive's material paints with."""
    material = model.json["materials"][prim["material"]]
    texture = material.get("pbrMetallicRoughness", {}).get("baseColorTexture")
    if not texture:
        return None
    return model.json["textures"][texture["index"]]["source"]


def wanted(model):
    """The primitives the cut actually uses, in the same order it takes them.

    Recognised by geometry rather than by accessor index, because this model
    lists the body and the helmet three times each with a different material -
    and only the first of each is read.
    """
    out, seen = [], set()
    for mesh in model.json.get("meshes", []):
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            if "JOINTS_0" not in attrs or "POSITION" not in attrs:
                continue
            verts = model.accessor(attrs["POSITION"])
            mark = (len(verts), tuple(np.round(verts[0], 5)),
                    tuple(np.round(verts[-1], 5)))
            if mark in seen:
                continue
            seen.add(mark)
            out.append((prim, len(verts)))
    return out


# The palette the Zenaric armour already wears, from make_armour.py: cool
# silver-grey plate, a dark near-black for the kant, and a lighter steel for
# the pieces that used to be a different metal.
CERAMIC = np.array([0.50, 0.525, 0.565])
STEEL = np.array([0.60, 0.615, 0.645])


def zenar(sheet):
    """The author's sheet in the conversion's colours, sculpt intact.

    **Hue goes, tone stays.** The first attempt at this drained the sheet and
    took the dark navy panels down to black with it, which is what Faig had
    been reporting as black patches since the very first screenshot. Luminance
    is remapped into a band instead of being crushed, so a dark panel comes out
    dark grey and still reads as a panel.

    Gold is not kept - Faig asked for it gone - but it is not flattened into the
    plate either: it becomes the lighter steel, so the engraving is still legible
    as a different metal.
    """
    rgb = np.asarray(sheet, np.float64) / 255.0
    high = rgb.max(2)
    low = rgb.min(2)
    sat = (high - low) / np.maximum(high, 1e-6)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])

    # Gold is the warm, saturated part: red leads and blue trails.
    gold = (sat > 0.22) & (rgb[..., 0] >= rgb[..., 1]) & (rgb[..., 1] > rgb[..., 2])

    # Into a band rather than to zero. Black lands at 0.10, white at 0.66, so
    # the navy panels sit near 0.24 - dark, present, not a hole.
    tone = 0.10 + 0.56 * lum
    out = tone[..., None] * CERAMIC / CERAMIC.mean()
    lifted = np.clip(tone + 0.13, 0, 1)[..., None] * STEEL / STEEL.mean()
    out = np.where(gold[..., None], lifted, out)
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model")
    ap.add_argument("--out", default=os.path.join("tools", "build",
                                                  "armour-momw", "Textures"))
    ap.add_argument("--zenar", action="store_true",
                    help="recolour to the conversion's palette instead of "
                         "shipping the author's")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    model = Gltf(args.model)
    sheets = images(model)
    parts = wanted(model)
    # The larger primitive is the body, the smaller the helmet. Said out loud
    # rather than assumed by position, because the order is the file's, not ours.
    parts.sort(key=lambda p: -p[1])
    names = ["zenar_body.dds", "zenar_helm.dds"]

    os.makedirs(args.out, exist_ok=True)
    for (prim, count), name in zip(parts, names):
        index = base_colour(model, prim)
        if index is None:
            print(f"{name}: that primitive names no base colour")
            continue
        sheet = sheets[index]
        pixels = np.array(sheet).astype(float)
        bright = pixels.mean()
        colour = float(np.mean((pixels.max(2) - pixels.min(2))
                               / np.maximum(pixels.max(2), 1)))
        print(f"{name:<16} from image {index}, {sheet.size[0]}x{sheet.size[1]}, "
              f"{count} vertices, luminance {bright:.0f}, saturation {colour:.3f}")
        if not args.write:
            continue
        if args.zenar:
            sheet = zenar(sheet)
            pixels = np.array(sheet).astype(float)
            print(f"                 recoloured: luminance {pixels.mean():.0f}, "
                  f"saturation {np.mean((pixels.max(2) - pixels.min(2)) / np.maximum(pixels.max(2), 1)):.3f}")
        rgba = np.dstack([np.array(sheet.convert("RGB")),
                          np.full(sheet.size[::-1], 255, np.uint8)])
        path = os.path.join(args.out, name)
        write_dxt(path, rgba, "dxt1")
        print(f"                 wrote {path}, {os.path.getsize(path):,} bytes")
    if not args.write:
        print("Dry run. Pass --write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
