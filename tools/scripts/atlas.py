#!/usr/bin/env python3
"""Pack a model's textures and flat colours onto one sheet.

A Morrowind bodypart file carries one shape and one texture, but a downloaded
suit paints one plate with several materials - a plate sheet, a detail sheet,
a flat colour with no image at all. So every material goes onto one atlas and
each vertex's texture coordinate is moved into its material's tile.

Images take a square grid, the last cell is cut into swatches for the flat
colours, and every tile is edge-padded with its own border pixels so the
smaller mipmaps do not bleed a neighbour into the seam.
"""

import math

import numpy as np
from PIL import Image


def build_atlas(items, size=2048, pad=8):
    """items: PIL images or (r, g, b[, a]) colours. Returns (atlas, rects).

    rect = (u0, v0, du, dv): (u, v) of the item lands at (u0 + u*du, v0 + v*dv),
    v measured down from the top, as glTF and DDS both do.
    """
    images = [i for i, it in enumerate(items) if isinstance(it, Image.Image)]
    colours = [i for i, it in enumerate(items) if not isinstance(it, Image.Image)]
    grid = math.ceil(math.sqrt(len(images) + (1 if colours else 0))) or 1
    cell = size // grid
    canvas = np.zeros((size, size, 4), np.uint8)
    rects = [None] * len(items)

    inner = cell - 2 * pad
    for slot, i in enumerate(images):
        cx, cy = slot % grid, slot // grid
        tile = np.asarray(items[i].convert("RGBA").resize((inner, inner),
                                                          Image.LANCZOS))
        padded = np.pad(tile, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
        canvas[cy * cell:cy * cell + cell, cx * cell:cx * cell + cell] = padded
        rects[i] = ((cx * cell + pad) / size, (cy * cell + pad) / size,
                    inner / size, inner / size)

    if colours:
        last = grid * grid - 1
        x0, y0 = (last % grid) * cell, (last // grid) * cell
        k = math.ceil(math.sqrt(len(colours)))
        sub = cell // k
        for n, i in enumerate(colours):
            rgba = tuple(items[i]) + ((255,) if len(items[i]) == 3 else ())
            sx, sy = x0 + (n % k) * sub, y0 + (n // k) * sub
            canvas[sy:sy + sub, sx:sx + sub] = rgba
            rects[i] = ((sx + sub * 0.25) / size, (sy + sub * 0.25) / size,
                        sub * 0.5 / size, sub * 0.5 / size)
    return Image.fromarray(canvas, "RGBA"), rects


def remap_uv(uv, rect):
    u0, v0, du, dv = rect
    uv = np.clip(np.asarray(uv, np.float64), 0.0, 1.0)
    return np.c_[u0 + uv[:, 0] * du, v0 + uv[:, 1] * dv]


if __name__ == "__main__":
    red = Image.new("RGB", (64, 64), (255, 0, 0))
    green = Image.new("RGB", (64, 64), (0, 255, 0))
    green.paste((0, 0, 255), (0, 0, 32, 32))
    atlas, rects = build_atlas([red, green, (255, 255, 0), (10, 20, 30)], 512, 4)

    def at(item, u, v):
        (x, y), = remap_uv([[u, v]], rects[item]) * 512
        return atlas.getpixel((min(int(x), 511), min(int(y), 511)))
    assert at(0, 0.5, 0.5)[:2] == (255, 0)
    assert at(1, 0.25, 0.25)[2] > 200 and at(1, 0.75, 0.75)[1] > 200
    for item, want in ((2, (255, 255, 0)), (3, (10, 20, 30))):
        for u, v in ((0.0, 1.0), (1.0, 0.0), (0.5, 0.5)):
            assert at(item, u, v)[:3] == want
    x0 = int(rects[0][0] * 512)
    assert atlas.getpixel((x0 - 2, int((rects[0][1] + rects[0][3] / 2) * 512)))[0] == 255
    print("OK")
