#!/usr/bin/env python3
"""Draw each built piece beside the vanilla part it has to fill.

A screenshot of a character in a dim room cannot say whether one bodypart is
malformed, inside out, or merely small. This can: same scale, same three
orthographic views, ours in white over the vanilla part in grey.

Reading a NIF only. Nothing here writes one.
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_armour_set import SLOTS                      # noqa: E402
from uvmap import parse_trishape, read_mesh             # noqa: E402

CELL, PAD = 150, 6
VIEWS = ((0, 2, "front  X-Z"), (1, 2, "side  Y-Z"), (0, 1, "top  X-Y"))


def draw(box, verts, tris, a, b, span, centre, colour, width=1):
    lo = centre - span / 2.0
    def to_px(p):
        x = (p[:, a] - lo[a]) / span * (CELL - 2 * PAD) + PAD
        y = (CELL - PAD) - (p[:, b] - lo[b]) / span * (CELL - 2 * PAD)
        return np.c_[x, y]
    px = to_px(verts)
    for t in tris:
        pts = [tuple(px[i]) for i in t]
        box.polygon(pts + [pts[0]], outline=colour)


def main():
    root = os.path.join("tools", "build", "armour-momw", "Meshes", "zenar")
    rows = [s for s in SLOTS if os.path.exists(os.path.join(root, s + ".nif"))]
    img = Image.new("RGB", (CELL * 3 + 90, CELL * len(rows)), (18, 18, 20))
    pen = ImageDraw.Draw(img)
    for r, slot in enumerate(rows):
        donor, ref, _turn, cut = SLOTS[slot]
        with open(os.path.join(root, slot + ".nif"), "rb") as f:
            ours, _u, our_tris = parse_trishape(f.read())
        theirs, _v, their_tris = read_mesh(ref or donor)
        if cut:
            from nif_write import trim
            keep = trim(theirs, cut)
            mask = np.isin(np.arange(len(theirs)),
                           np.where((theirs[:, None] == keep[None]).all(2)
                                    .any(1))[0])
            their_tris = their_tris[mask[their_tris].all(1)]
        both = np.vstack([ours, theirs])
        centre = (both.max(0) + both.min(0)) / 2.0
        span = float((both.max(0) - both.min(0)).max()) * 1.05
        pen.text((6, r * CELL + 8), slot, fill=(200, 200, 210))
        pen.text((6, r * CELL + 24), "%d v" % len(ours), fill=(120, 120, 130))
        for c, (a, b, label) in enumerate(VIEWS):
            box = Image.new("RGB", (CELL, CELL), (18, 18, 20))
            cell = ImageDraw.Draw(box)
            draw(cell, theirs, their_tris, a, b, span, centre, (90, 90, 100))
            draw(cell, ours, our_tris, a, b, span, centre, (235, 235, 245))
            if r == 0:
                cell.text((PAD, PAD), label, fill=(150, 150, 160))
            img.paste(box, (90 + c * CELL, r * CELL))
    out = os.path.join("tools", "reports", "armour-pieces.png")
    img.save(out)
    print("white is ours, grey is the vanilla part it must fill")
    print(out)


if __name__ == "__main__":
    sys.exit(main())
