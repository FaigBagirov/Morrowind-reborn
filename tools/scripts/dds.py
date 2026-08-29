#!/usr/bin/env python3
"""Write DDS textures the engine reads: BGRA, DXT1 or DXT5, always mipmapped.

Shared by `make_vfx.py` and `make_armour.py`. It exists because a binary header
written from memory in two places is a header that drifts in one of them, and
the failure is silent - the engine either refuses the file or samples garbage.

Pillow does the block encoding but writes a single level, so the mip chain and
the header are assembled here.
"""

import io
import os
import struct

import numpy as np
from PIL import Image

FOURCC = {"dxt1": b"DXT1", "dxt5": b"DXT5"}
BLOCK_BYTES = {"dxt1": 8, "dxt5": 16}


def mip_levels(rgba):
    """The full chain, level 0 first, halving until 1x1.

    Without mips the GPU samples a full-size texture for a few pixels of screen:
    it thrashes the cache and shimmers as the object moves. Everything in the
    game has them.
    """
    levels = [np.asarray(rgba).astype(np.uint8)]
    cur = Image.fromarray(levels[0], "RGBA")
    while min(cur.size) > 1:
        cur = cur.resize((max(cur.width // 2, 1), max(cur.height // 2, 1)),
                         Image.LANCZOS)
        levels.append(np.array(cur))
    return levels


def _header(w, h, mips, linear_size, fourcc=None):
    head = bytearray(128)
    head[0:4] = b"DDS "
    struct.pack_into("<I", head, 4, 124)
    if fourcc:
        # caps | height | width | pixelformat | linearsize | mipmapcount
        flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000 | 0x20000
    else:
        # caps | height | width | pitch | pixelformat | mipmapcount
        flags = 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x20000
    struct.pack_into("<I", head, 8, flags)
    struct.pack_into("<I", head, 12, h)
    struct.pack_into("<I", head, 16, w)
    struct.pack_into("<I", head, 20, linear_size)
    struct.pack_into("<I", head, 28, mips)
    struct.pack_into("<I", head, 76, 32)               # pixelformat size
    if fourcc:
        struct.pack_into("<I", head, 80, 0x4)          # DDPF_FOURCC
        head[84:88] = fourcc
    else:
        struct.pack_into("<I", head, 80, 0x1 | 0x40)   # alphapixels | rgb
        struct.pack_into("<I", head, 88, 32)           # bit count
        struct.pack_into("<I", head, 92, 0x00FF0000)   # R
        struct.pack_into("<I", head, 96, 0x0000FF00)   # G
        struct.pack_into("<I", head, 100, 0x000000FF)  # B
        struct.pack_into("<I", head, 104, 0xFF000000)  # A
    struct.pack_into("<I", head, 108, 0x1000 | 0x400000 | 0x8)  # texture|mipmap|complex
    return head


def write_dxt(path, rgba, fmt="dxt5"):
    """Block-compressed, mipmapped.

    `dxt1` for opaque textures - it is what the originals in the game use and
    half the size of dxt5. `dxt5` where alpha matters, or where alpha carries
    shape: it quantises alpha in 4x4 blocks, which was measured harmless on the
    particle textures but is worth knowing before choosing it.
    """
    levels = mip_levels(rgba)
    payload = []
    for level in levels:
        buf = io.BytesIO()
        Image.fromarray(level, "RGBA").save(buf, format="DDS",
                                            pixel_format=fmt.upper())
        payload.append(buf.getvalue()[128:])   # strip Pillow's own header
    h, w = levels[0].shape[:2]
    with open(path, "wb") as f:
        f.write(_header(w, h, len(levels), len(payload[0]), FOURCC[fmt]))
        for block in payload:
            f.write(block)


def write_bgra(path, rgba):
    """Uncompressed 32-bit BGRA, mipmapped. Four times the size, no encoder."""
    levels = mip_levels(rgba)
    h, w = levels[0].shape[:2]
    with open(path, "wb") as f:
        f.write(_header(w, h, len(levels), w * 4))
        for level in levels:
            f.write(level[..., [2, 1, 0, 3]].tobytes())


def read_bgra(path):
    """Level 0 of an uncompressed BGRA file, as RGBA."""
    with open(path, "rb") as f:
        head = f.read(128)
        h, w = struct.unpack_from("<II", head, 12)
        if head[80:84] != b"\x41\x00\x00\x00" and head[84:88] in FOURCC.values():
            raise ValueError(f"{os.path.basename(path)} is block-compressed")
        data = f.read(w * h * 4)
    bgra = np.frombuffer(data, np.uint8).reshape(h, w, 4)
    return bgra[..., [2, 1, 0, 3]].copy()
