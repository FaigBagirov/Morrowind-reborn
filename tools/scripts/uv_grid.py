#!/usr/bin/env python3
"""A diagnostic UV sheet: every cell a different colour, every cell an F.

    python tools/scripts/uv_grid.py --out grid.png [--cells 8] [--size 1024]
    python tools/scripts/uv_grid.py --out grid.dds --dds        # for the game

Why it exists (CLAUDE.md, "Testing a mesh in game", methods 2 and 3): a model
in its own texture hides its own faults. Painted with this sheet, any patch on
screen names its place on the UV sheet, and therefore on the model:

- **hue by column, lightness by row** - a patch's colour says where on the
  sheet it came from, so a seam, a wrapped island or a piece unwrapped twice
  is visible as a colour that does not belong;
- **an F in every cell** - the letter is asymmetric, so it reads backwards on
  a mirrored piece and upside down on a rotated one. Colour alone cannot say
  that: a mirrored piece shows the same colours in reverse order, which is
  easy to miss, while a backwards F is not;
- **cells are square and all the same size** - stretched texture shows as
  stretched cells, and a piece unwrapped at a different scale from its
  neighbour shows as cells of a different size across the seam.

Blender has `Image > New > Generated Type: Color Grid`, which is the same
idea with numbers instead of letters; this one is here so the sheet in the
modelling program and the sheet in the game are the same picture.
"""

import argparse
import colorsys
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def grid(size=1024, cells=8):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    pen = ImageDraw.Draw(img)
    step = size // cells
    for cx in range(cells):
        hue = cx / cells
        for cy in range(cells):
            light = 0.30 + 0.55 * (cy / max(cells - 1, 1))
            r, g, b = colorsys.hls_to_rgb(hue, light, 0.85)
            x0, y0 = cx * step, cy * step
            pen.rectangle([x0, y0, x0 + step - 1, y0 + step - 1],
                          fill=(int(r * 255), int(g * 255), int(b * 255), 255))
            # the F: a stem and two arms, drawn from the cell's own corner so
            # it flips with the cell
            ink = (0, 0, 0, 255) if light > 0.5 else (255, 255, 255, 255)
            x, y = x0 + step // 4, y0 + step // 6
            w, h = step // 2, step * 2 // 3
            pen.rectangle([x, y, x + w // 4, y + h], fill=ink)        # stem
            pen.rectangle([x, y, x + w, y + h // 5], fill=ink)        # top arm
            pen.rectangle([x, y + h // 2, x + int(w * 0.7),
                           y + h // 2 + h // 6], fill=ink)            # middle
            pen.rectangle([x0, y0, x0 + step - 1, y0 + step - 1],
                          outline=(0, 0, 0, 255), width=max(1, step // 64))
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--cells", type=int, default=8)
    ap.add_argument("--dds", action="store_true",
                    help="write a mipmapped BGRA .dds the game can read")
    args = ap.parse_args()
    img = grid(args.size, args.cells)
    if args.dds:
        import numpy as np
        from dds import write_bgra
        write_bgra(args.out, np.asarray(img))
    else:
        img.save(args.out)
    print(f"{args.out}: {args.size}x{args.size}, {args.cells}x{args.cells} cells")
    return 0


if __name__ == "__main__":
    sys.exit(main())
