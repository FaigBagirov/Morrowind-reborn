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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model")
    ap.add_argument("--out", default=os.path.join("tools", "build",
                                                  "armour-momw", "Textures"))
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
