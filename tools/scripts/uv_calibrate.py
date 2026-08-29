#!/usr/bin/env python3
"""Paint a UV ruler onto a texture, so one screenshot says where the front is.

    python tools/scripts/uv_calibrate.py tx_a_ebony_helmet --write

Why this exists. To put a feature on a piece of armour - eye slits on a helmet -
you have to know which part of the texture sheet lands on the front of the head.
Nothing in the texture says so. The mesh does, in principle: its vertices carry
both a position and a UV. But the shape sits under a node transform, and reading
the sign conventions out of a 2002 binary format is exactly the kind of
inference that is right until it is silently wrong, and wrong here means eye
slits on the back of the skull.

So: measure instead. This paints eight labelled colour bands around the sheet's
horizontal axis and three horizontal rules across it. Wear the piece, look at it
from the front, and the colour in the middle of the face names the U, while the
rule crossing the eyes names the V. One screenshot, no inference.

The bands are laid over the real texture rather than replacing it, so the piece
is still recognisable and it is obvious which way up it is.

Delete the data directory line when done.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dds import write_dxt  # noqa: E402
from make_armour import data_dirs, find_texture, load  # noqa: E402

PLAY_CFG = r"D:/Backups/OneDrive/All/Documents/My Games/OpenMW/play/openmw.cfg"

# Eight, because eight colours can be told apart at a glance on a small object
# in a dark room, and 45 degrees around the head is close enough to place a
# visor and then refine. Named so the answer can be spoken rather than measured.
BANDS = [("red", (1.00, 0.15, 0.10)),
         ("orange", (1.00, 0.55, 0.05)),
         ("yellow", (1.00, 0.95, 0.10)),
         ("green", (0.15, 0.85, 0.20)),
         ("cyan", (0.10, 0.90, 0.95)),
         ("blue", (0.15, 0.35, 1.00)),
         ("violet", (0.60, 0.20, 0.95)),
         ("white", (1.00, 1.00, 1.00))]

# Three heights across the likely eye line, so the same screenshot pins V too.
RULES = [("top", 0.44), ("middle", 0.50), ("bottom", 0.56)]

MIX = 0.55          # how much of the ruler shows over the real texture
RULE_PX = 5


def paint(rgba):
    h, w = rgba.shape[:2]
    out = rgba.copy()
    for i, (_name, colour) in enumerate(BANDS):
        x0 = int(w * i / len(BANDS))
        x1 = int(w * (i + 1) / len(BANDS))
        band = np.array(colour, np.float32)
        out[:, x0:x1, :3] = (out[:, x0:x1, :3] * (1.0 - MIX) + band * MIX)
    for _name, v in RULES:
        y = int(h * v)
        out[max(y - RULE_PX, 0):y + RULE_PX, :, :3] = 0.02
    return np.clip(out, 0.0, 1.0)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stem", help="texture name, without extension")
    ap.add_argument("--folder", default="")
    ap.add_argument("--config", default=PLAY_CFG)
    ap.add_argument("--out", default=os.path.join(root, "tools", "build",
                                                  "armour-calib"))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    dirs = data_dirs(args.config, skip=[args.out])
    src = find_texture(dirs, args.folder, args.stem)
    if not src:
        raise SystemExit(f"{args.stem} is not in the load order")
    print(f"source: {src}")

    ruler = paint(load(src))
    preview = os.path.join(root, "tools", "armour", f"calib-{args.stem}.png")
    os.makedirs(os.path.dirname(preview), exist_ok=True)
    Image.fromarray((ruler[..., :3] * 255).astype(np.uint8)).save(preview)
    print(f"preview: {preview}")

    if args.write:
        out_dir = os.path.join(args.out, "Textures", args.folder)
        os.makedirs(out_dir, exist_ok=True)
        write_dxt(os.path.join(out_dir, args.stem + ".dds"),
                  ruler * 255.0, "dxt1")
        print(f"written: {os.path.join(out_dir, args.stem + '.dds')}")
        print("Add this line AFTER the armour one, and delete it afterwards:")
        print(f'    data="{args.out.replace(os.sep, "/")}"')
    else:
        print("Preview only. Nothing was written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
