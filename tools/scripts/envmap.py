#!/usr/bin/env python3
import struct
from skeleton import blocks


def _footer_offset(blob):
    """Return the offset where the footer starts."""
    for end in range(len(blob) - 8, len(blob) - 4 - 4 * 64, -4):
        roots, = struct.unpack_from("<I", blob, end)
        if end + 4 + 4 * roots == len(blob):
            return end
    raise AssertionError("no footer")


def root_ref(blob):
    """Return the root reference (int32) from the file."""
    f = _footer_offset(blob)
    return struct.unpack_from("<i", blob, f + 4)[0]


def node_walk(blob, i):
    """Return the absolute positions of num_children (C) and num_effects (E)."""
    kind, at = blocks(blob)[i]
    if kind != "NiNode":
        raise AssertionError
    p = at
    name_len, = struct.unpack_from("<I", blob, p)
    p += 4 + name_len
    p += 8  # extra_data_ref + controller_ref
    p += 2  # flags
    p += 12  # translation
    p += 36  # rotation
    p += 4   # scale
    p += 12  # velocity
    num_prop, = struct.unpack_from("<I", blob, p)
    p += 4 + 4 * num_prop
    has_box, = struct.unpack_from("<I", blob, p)
    p += 4 + (64 if has_box else 0)
    C = p
    num_children, = struct.unpack_from("<I", blob, p)
    p += 4 + 4 * num_children
    E = p
    num_effects, = struct.unpack_from("<I", blob, p)
    return C, E


def node_children(blob, i):
    """Return the child references of a NiNode block."""
    C, _ = node_walk(blob, i)
    num_children, = struct.unpack_from("<I", blob, C)
    return list(struct.unpack_from(f"<{num_children}i", blob, C + 4)) if num_children else []


def node_effects(blob, i):
    """Return the effect references of a NiNode block."""
    _, E = node_walk(blob, i)
    num_effects, = struct.unpack_from("<I", blob, E)
    return list(struct.unpack_from(f"<{num_effects}i", blob, E + 4)) if num_effects else []


def add_env_map(blob, donor):
    """Return a new .nif file with the environment map added."""
    # donor blocks
    dblocks = blocks(donor)
    e = next(idx for idx, (name, _) in enumerate(dblocks) if name == "NiTextureEffect")
    s = e + 1

    def block_bytes(bs, idx):
        at = bs[idx][1]
        start = at - len(bs[idx][0]) - 4
        end = bs[idx + 1][1] - len(bs[idx + 1][0]) - 4 if idx + 1 < len(bs) else _footer_offset(donor)
        return donor[start:end]

    effect_bytes = bytearray(block_bytes(dblocks, e))
    source_bytes = block_bytes(dblocks, s)

    # overwrite int32 at len(effect_bytes)-27
    effect_bytes[len(effect_bytes) - 27:len(effect_bytes) - 23] = struct.pack("<i", len(blocks(blob)) + 1)

    n = len(blocks(blob))
    r = root_ref(blob)
    old_count = struct.unpack_from("<I", blob, blob.index(b"\n") + 5)[0]
    case_a = blocks(blob)[r][0] == "NiNode"

    # header
    H = blob.index(b"\n") + 5
    start_block0 = blocks(blob)[0][1] - len(blocks(blob)[0][0]) - 4
    new_header = blob[:H] + struct.pack("<I", old_count + (2 if case_a else 3)) + blob[H + 4:start_block0]

    # build block list
    out_blocks = []
    bblks = blocks(blob)
    footer = blob[_footer_offset(blob):]
    for idx, (kind, at) in enumerate(bblks):
        start = at - len(kind) - 4
        end = bblks[idx + 1][1] - len(bblks[idx + 1][0]) - 4 if idx + 1 < len(bblks) else _footer_offset(blob)
        block_data = blob[start:end]
        if case_a and idx == r:
            # replace effect list
            C, E = node_walk(blob, r)
            old_num = struct.unpack_from("<I", blob, E)[0]
            pref = block_data[:E - start]
            old_refs = block_data[E - start + 4:E - start + 4 + 4 * old_num]
            rest = block_data[E - start + 4 + 4 * old_num:]
            new_block = pref + struct.pack("<I", old_num + 1) + old_refs + struct.pack("<i", n) + rest
            block_data = new_block
        out_blocks.append(block_data)

    # add new blocks
    out_blocks.extend([bytes(effect_bytes), source_bytes])
    if not case_a:
        # new NiNode
        node_hdr = struct.pack("<I", 6) + b"NiNode"
        name = struct.pack("<I", 7) + b"EnvRoot"
        extra = struct.pack("<i", -1)
        ctrl = struct.pack("<i", -1)
        flags = struct.pack("<H", 0)
        trans = struct.pack("<3f", 0.0, 0.0, 0.0)
        rot = struct.pack("<9f",
                          1.0, 0.0, 0.0,
                          0.0, 1.0, 0.0,
                          0.0, 0.0, 1.0)
        scale = struct.pack("<f", 1.0)
        vel = struct.pack("<3f", 0.0, 0.0, 0.0)
        props = struct.pack("<I", 0)
        bbox = struct.pack("<I", 0)
        child = struct.pack("<I", 1) + struct.pack("<i", r)
        effect = struct.pack("<I", 1) + struct.pack("<i", n)
        new_node = (node_hdr + name + extra + ctrl + flags + trans + rot +
                    scale + vel + props + bbox + child + effect)
        out_blocks.append(new_node)
        # modify footer root reference
        foff = _footer_offset(blob)
        new_footer = footer[:4] + struct.pack("<i", n + 2) + footer[8:]
        footer = new_footer

    # assemble output
    body = b''.join(out_blocks)
    return new_header + body + footer
