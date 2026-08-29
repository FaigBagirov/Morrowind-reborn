#!/usr/bin/env python3
"""Read Bethesda's BSA archives - enough of them to pull a texture out.

The vanilla particle textures live in `Morrowind.bsa` and its two expansions,
and `--profile vanilla` has to sample its colour from them. `delta_plugin
vfs-extract` did this in the first pass; this replaces it so the build has no
dependency the repo does not carry.

The format is the 2002 one and it is small: a header, a table of sizes and
offsets, a table of name offsets, the names, a hash table, then the data.

**Verified against `delta_plugin`**: the six textures the first pass extracted
come back byte for byte identical.
"""

import os
import struct


class Bsa:
    def __init__(self, path):
        self.path = path
        self._f = open(path, "rb")
        version, hash_offset, count = struct.unpack("<III", self._f.read(12))
        if version != 0x100:
            raise ValueError(f"{path}: not a Morrowind BSA (version {version:#x})")
        sizes = struct.unpack(f"<{count * 2}I", self._f.read(count * 8))
        name_offsets = struct.unpack(f"<{count}I", self._f.read(count * 4))
        names = self._f.read(hash_offset - count * 12)
        data_start = 12 + hash_offset + count * 8
        self.index = {}
        for i in range(count):
            start = name_offsets[i]
            name = names[start:names.index(b"\0", start)].decode("cp1252")
            self.index[name.lower().replace("\\", "/")] = (
                sizes[i * 2], data_start + sizes[i * 2 + 1])

    def __contains__(self, name):
        return name.lower().replace("\\", "/") in self.index

    def read(self, name):
        size, offset = self.index[name.lower().replace("\\", "/")]
        self._f.seek(offset)
        return self._f.read(size)

    def close(self):
        self._f.close()


def open_archives(paths):
    """Archives in load order. Later ones win, as the engine has them."""
    return [Bsa(p) for p in paths if os.path.exists(p)]


def find(archives, name):
    """(archive, name) for the last archive holding `name`, or None."""
    hit = None
    for a in archives:
        if name in a:
            hit = (a, name)
    return hit
