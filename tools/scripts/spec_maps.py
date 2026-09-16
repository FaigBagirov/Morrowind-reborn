#!/usr/bin/env python3
"""Shine for an imported suit: `_spec` maps from the model's own PBR maps.

    python tools/scripts/spec_maps.py model.glb --out tools/build/armour-vanilla/Textures [--gain 1.6]

Faig found the Zenaric import matte, "as if plastic". OpenMW (0.51, with
`auto use object specular maps`, on in both profiles) loads `<texture>_spec.dds`
beside a diffuse. Read from `resources/shaders/compatibility/objects.frag`:
rgb is the specular colour, alpha * 255 the shininess exponent.

The model carries glTF metallic-roughness maps (green = roughness, blue =
metallic). Metal reflects in its own colour, anything else in a dim grey; a
smooth surface gets a tight, high exponent and a rough one a broad, low one.
`--gain` lifts the whole highlight, since the engine has no environment
reflection to carry metal the way a PBR viewer does.

The sheets and their names are the same ones `model_textures.py` writes.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dds import write_dxt  # noqa: E402
from glb import Gltf  # noqa: E402
from model_textures import base_colour, images, wanted  # noqa: E402


def spec_map(base, mr, gain):
    base = np.asarray(base.convert("RGB")).astype(np.float64) / 255.0
    mr = np.asarray(mr.convert("RGB").resize(base.shape[1::-1])).astype(np.float64) / 255.0
    rough, metal = mr[..., 1:2], mr[..., 2:3]
    # Measured too weak on screen at 0.08 grey and exponents near 125: the
    # highlight was a pinpoint nobody could see. Every surface now reflects
    # in its own colour, and the exponent stays broad.
    # Faig, 2026-09-16: that read as a lighter colour, not as shine - a broad
    # highlight is just brighter paint. Steel is a tight, bright highlight: a
    # neutral grey on non-metal, the surface's own colour on metal, exponent
    # 30..128.
    colour = (0.45 * (1.0 - metal) + base * metal) * gain
    shine = 30.0 + (1.0 - rough[..., 0]) * 98.0             # exponent 30..128
    out = np.empty(base.shape[:2] + (4,), np.uint8)
    out[..., :3] = np.clip(colour * 255, 0, 255)
    out[..., 3] = np.clip(shine, 0, 255)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gain", type=float, default=2.0)
    args = ap.parse_args()

    model = Gltf(args.model)
    sheets = images(model)
    parts = sorted(wanted(model), key=lambda p: -p[1])
    for (prim, _count), name in zip(parts, ["zenar_body", "zenar_helm"]):
        mat = model.json["materials"][prim["material"]]
        tex = mat.get("pbrMetallicRoughness", {}).get("metallicRoughnessTexture")
        base = base_colour(model, prim)
        if tex is None or base is None:
            print(f"{name}: no metallic-roughness map, left matte")
            continue
        mr = sheets[model.json["textures"][tex["index"]]["source"]]
        rgba = spec_map(sheets[base], mr, args.gain)
        path = os.path.join(args.out, name + "_spec.dds")
        write_dxt(path, rgba, "dxt5")
        print(f"{path}: mean exponent {rgba[..., 3].mean():.0f}, "
              f"mean colour {rgba[..., :3].mean():.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
