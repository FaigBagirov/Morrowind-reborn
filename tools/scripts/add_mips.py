#!/usr/bin/env python3
"""Add a mipmap chain to the generated particle DDS files.

Without mips the GPU samples a full 512x512 texture for a particle a few pixels
across: it thrashes the texture cache and shimmers as the particle moves. Every
texture in the game has them; ours should too.
"""
import os
import struct
import sys

import numpy as np
from PIL import Image


def read_dds(path):
    with open(path, "rb") as f:
        head = f.read(128)
        h, w = struct.unpack_from("<II", head, 12)
        data = f.read(w * h * 4)
    bgra = np.frombuffer(data, np.uint8).reshape(h, w, 4)
    return bgra[..., [2, 1, 0, 3]].copy()


def write_dds(path, levels):
    h, w = levels[0].shape[:2]
    header = bytearray(128)
    header[0:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)
    # caps | height | width | pitch | pixelformat | mipmapcount
    struct.pack_into("<I", header, 8, 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x20000)
    struct.pack_into("<I", header, 12, h)
    struct.pack_into("<I", header, 16, w)
    struct.pack_into("<I", header, 20, w * 4)
    struct.pack_into("<I", header, 28, len(levels))
    struct.pack_into("<I", header, 76, 32)
    struct.pack_into("<I", header, 80, 0x1 | 0x40)
    struct.pack_into("<I", header, 88, 32)
    struct.pack_into("<I", header, 92, 0x00FF0000)
    struct.pack_into("<I", header, 96, 0x0000FF00)
    struct.pack_into("<I", header, 100, 0x000000FF)
    struct.pack_into("<I", header, 104, 0xFF000000)
    struct.pack_into("<I", header, 108, 0x1000 | 0x400000 | 0x8)  # texture|mipmap|complex
    with open(path, "wb") as f:
        f.write(header)
        for lvl in levels:
            f.write(lvl[..., [2, 1, 0, 3]].astype(np.uint8).tobytes())


def mip_directory(directory, label="", quiet=False):
    """Give every DDS in one directory a full mipmap chain, in place.

    Idempotent: `read_dds` takes level 0 only, so running it twice is a no-op
    beyond the rewrite. `make_vfx.py --write` calls this itself - forgetting the
    second command once was enough to ship 36 mipless textures.
    """
    count = 0
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".dds"):
            continue
        path = os.path.join(directory, name)
        rgba = read_dds(path)
        levels, cur = [rgba], Image.fromarray(rgba, "RGBA")
        while min(cur.size) > 1:
            cur = cur.resize((max(cur.width // 2, 1), max(cur.height // 2, 1)),
                             Image.LANCZOS)
            levels.append(np.array(cur))
        write_dds(path, levels)
        count += 1
        if not quiet:
            print(f"  {label}{name}: {len(levels)} levels, "
                  f"{os.path.getsize(path) // 1024} KB")
    return count


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    total = 0
    for profile in ("vanilla", "momw"):
        d = os.path.join(root, "tools", "build", f"vfx-{profile}", "Textures")
        if os.path.isdir(d):
            total += mip_directory(d, f"{profile}/")
    print(f"{total} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
