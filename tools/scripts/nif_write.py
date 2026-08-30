#!/usr/bin/env python3
"""Write a Morrowind NIF carrying geometry from somewhere else.

    python tools/scripts/nif_write.py helmet.obj --donor meshes/a/a_ebony_helmet.nif --out new.nif

The project rule against generating NIFs rested on a sentence in Canon Part 9 -
"the engine validates models on load and rejects machine-assembled files" -
which had never been tested by anyone here. It is false, measured twice: OpenMW's
own `niftest` accepts a mesh a script reshaped, and accepts this, a file carrying
3,269 vertices of downloaded geometry where the donor had 117.

## How it is done, and why it is safe to do this way

Not from nothing. A **donor** file supplies everything except the geometry - the
node, the material, the texture reference, the trailing bytes - and only its
`NiTriShapeData` block is replaced. In this format blocks refer to each other by
index rather than by offset and carry no length field, so a block that changes
size breaks nothing after it.

The layout of that block was not guessed. It was established by parsing a real
file and rebuilding it from its own arrays until all 5,761 bytes came back
identical:

    ushort numVertices        uint32 flag      float3 * n vertices
    uint32 flag               float3 * n normals
    float3 centre             float radius
    uint32 hasVertexColours   ushort numUVSets    uint32 flag
    float2 * n texture coordinates
    ushort numTriangles       uint32 numTrianglePoints
    ushort3 * m triangles

The three `flag` words are copied from the donor rather than invented. They read
as neither 0 nor 1 in the file examined, so what they mean is **not known**;
passing them through is honest and works, and writing a guess would not be.

## What it does not do

* **Rigging.** Morrowind dresses a body from separate rigid parts, so a helmet
  needs none. Anything spanning a joint would.
* **Judging the result.** `niftest` reads a file; it does not wear one. Whether
  the piece sits on the head, faces forward and does not clip is a question for
  the game.
* **Collision.** The donor's own is carried through unexamined.
"""

import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from obj import read as read_obj  # noqa: E402
from uvmap import read_mesh  # noqa: E402

MARKER = b"NiTriShapeData"


def donor_parts(blob):
    """Everything of the donor that is kept, plus its three unexplained words."""
    start = blob.find(MARKER)
    if start < 0:
        raise ValueError("donor has no NiTriShapeData block")
    body = start + len(MARKER)
    count, = struct.unpack_from("<H", blob, body)
    flag_a, = struct.unpack_from("<I", blob, body + 2)
    verts_end = body + 6 + 12 * count
    flag_b, = struct.unpack_from("<I", blob, verts_end)
    sphere = verts_end + 4 + 12 * count
    flag_c, = struct.unpack_from("<I", blob, sphere + 22)
    uv_off = sphere + 26
    tri_off = uv_off + 8 * count
    ntri, = struct.unpack_from("<H", blob, tri_off)
    tail = blob[tri_off + 6 + 6 * ntri:]
    return blob[:body], (flag_a, flag_b, flag_c), tail


def retexture(blob, name):
    """Point the donor's texture reference somewhere else.

    Without this a mesh built on the ebony helm wears the ebony helm's texture,
    because that filename is baked into the donor's NiSourceTexture block. The
    string is length-prefixed and nothing in this format stores block offsets,
    so a replacement of any length is safe.
    """
    for ext in (b".bmp", b".dds", b".tga", b".png"):
        at = blob.lower().find(ext)
        while at > 0:
            # walk back to a plausible length prefix and check it matches
            for back in range(4, 80):
                start = at + 4 - back
                if start < 4:
                    break
                length, = struct.unpack_from("<I", blob, start - 4)
                if length == back and _printable(blob[start:start + back]):
                    old = blob[start:start + back].decode("ascii")
                    new = name.encode("ascii")
                    return (blob[:start - 4] + struct.pack("<I", len(new))
                            + new + blob[start + back:]), old
            at = blob.lower().find(ext, at + 1)
    raise ValueError("no texture filename found in the donor")


def _printable(chunk):
    return all(32 <= c < 127 for c in chunk)


def normals(verts, tris):
    """Area-weighted per-vertex normals, which is what the format stores."""
    out = np.zeros_like(verts)
    corner = verts[tris]
    face = np.cross(corner[:, 1] - corner[:, 0], corner[:, 2] - corner[:, 0])
    for k in range(3):
        np.add.at(out, tris[:, k], face)
    length = np.linalg.norm(out, axis=1, keepdims=True)
    return np.where(length > 1e-12, out / np.maximum(length, 1e-12),
                    np.array([0.0, 0.0, 1.0]))


def _order(extent):
    """The axes longest first, and how decisively the longest leads."""
    rank = np.argsort(extent)[::-1]
    lead = extent[rank[0]] / max(extent[rank[1]], 1e-9)
    return rank, lead


def axes(spec):
    """Parse "-z,y,x" into the rotation it names. Rejects anything else.

    Each token says where one of the piece's axes lands, X then Y then Z. The
    result has to be a rotation: a bare axis swap mirrors the mesh, which turns
    every triangle inside out, so a determinant of -1 is an error and not
    something to paper over.
    """
    look = {"x": 0, "y": 1, "z": 2}
    out = np.zeros((3, 3))
    tokens = [t.strip().lower() for t in spec.split(",")]
    if len(tokens) != 3:
        raise SystemExit("--axes wants three comma-separated tokens")
    for src, token in enumerate(tokens):
        sign = -1.0 if token.startswith("-") else 1.0
        out[look[token.lstrip("+-")], src] = sign
    if abs(np.linalg.det(out) - 1.0) > 1e-9:
        raise SystemExit(f"--axes {spec} is a reflection, not a rotation")
    return out


def trim(ref, spec):
    """Keep the half of a reference that corresponds to the piece.

    The game offers exactly one single-shape chest donor and it wears a long
    skirt: 62 units along its up axis where the body is 26. Fitting a torso to
    that box puts the shoulders at the waist and half the cuirass where the
    skirt should be - which is what it did.

    So cut the reference at its own narrowest cross-section, which on a cuirass
    is the waist, and keep the named side. `spec` is an axis and a sign, "z-"
    for the negative side of Z.
    """
    axis = "xyz".index(spec[0].lower())
    lo, hi = ref[:, axis].min(), ref[:, axis].max()
    slices = np.linspace(lo, hi, 12)
    width = []
    for a, b in zip(slices, slices[1:]):
        got = ref[(ref[:, axis] >= a) & (ref[:, axis] < b)]
        other = [k for k in range(3) if k != axis]
        # The widest of the two remaining axes, not their product. Area is
        # fooled by a thin ring at the hem: on the adamantium cuirass the
        # narrowest slice by area is the second one, 33.3 by 7.5, and cutting
        # there keeps the skirt and the whole thing with it. By width the
        # profile reads 32, 33, 31, 31, 27, 20.8, 22, 24, 25, 28, 28 - one
        # clear minimum, in the middle, which is the waist.
        width.append(np.max(got[:, other].max(0) - got[:, other].min(0))
                     if len(got) > 2 else np.inf)
    # Ignore the two end slices: a cuirass tapers at the shoulders and the hem,
    # and the waist is what is wanted, not an end.
    waist = slices[1 + int(np.argmin(width[1:-1]))]
    keep = ref[:, axis] < waist if spec[1] == "-" else ref[:, axis] > waist
    return ref[keep] if keep.sum() > 8 else ref


def align(verts, ref, clearance=1.0, fallback=None, gate=1.4, turn=None):
    """Put a bone-local piece into the frame of the vanilla part it replaces.

    **Rotation was the missing half, and it is most of what broke the suit.**
    Cutting now happens in each bone's own frame, so the two sides are already
    comparable; what is left is that Morrowind's bones and the rig's do not
    always agree on which axis runs along the limb. Measured against the vanilla
    body, they agree for the arm, the thigh, the foot and the hips, and disagree
    for the calf by one ninety-degree turn - the piece runs along X where the
    game wants Z.

    So the axes are matched by length: the longest of the piece to the longest
    of the vanilla part, and so on down. **Only when both are decisively
    ordered**, which is the `gate`. A hip is nearly cubic, its axis lengths are
    within a fifth of each other, and ranking them measures noise; a calf leads
    by 2.3 against 2.45 and ranking it measures the limb. Below the gate the
    axes are left alone, which is the answer the clearly-ordered pieces all give.

    Two earlier rules were tried and measured worse:

    * Fitting each piece to its **armour donor's** bounding box. The donor boxes
      do not correspond to the body - the one single-shape chest donor the game
      offers is 62 units deep because of its skirt - so every piece got its own
      unrelated scale and the suit came apart.
    * Aligning **principal axes** and choosing among the four flips by volume
      overlap. The margins came out between 0.002 and 0.009 on scores of 0.06 to
      0.18, so the choice was noise, and the scales it produced ranged from 5.0
      to 11.9 across the set.

    Size comes from the vanilla part along the matched axis, which is the one
    measurement that means the same thing on both bodies: how long the limb is.
    Uniform, so the piece keeps its own proportions, and `clearance` lets armour
    sit over a body rather than inside it. `fallback` covers the chest and the
    clavicle, which have no vanilla twin - Morrowind draws a naked torso from the
    skeleton, and its Chest bodypart is a skin decal seven units across.
    """
    extent = verts.max(0) - verts.min(0)
    target = ref.max(0) - ref.min(0)
    mine, lead = _order(extent)
    theirs, their_lead = _order(target)

    ranked = lead >= gate and their_lead >= gate
    if turn is None and ranked:
        turn = np.zeros((3, 3))
        for a, b in zip(mine, theirs):
            turn[b, a] = 1.0
        if np.linalg.det(turn) < 0:
            # A bare swap can mirror the piece, which turns every triangle
            # inside out. Undo it on the shortest axis, where a cross-section is
            # closest to symmetric and the flip shows least.
            turn[theirs[2]] *= -1.0
    elif turn is None:
        turn = np.eye(3)

    if fallback:
        # Uniform, for a slot with no vanilla twin to fill. Its own box would
        # be the wrong thing to fill anyway: the one chest donor the game
        # offers is 62 units deep because of its skirt.
        scale = np.array([float(fallback)] * 3)
    else:
        # **Per axis, and it has to be.** Morrowind's body is not a modern
        # character's: its Forearm bodypart spans 8.1 units where its Ankle
        # spans 24.3, because the game splits an arm into upper arm, forearm,
        # wrist and hand while this rig has no wrist at all. Scaling uniformly
        # off one axis then either leaves the calf short or blows the forearm
        # out - measured, the per-slot factors ranged from 41 to 132. Armour
        # has to fill the space the body part occupies or it gapes, so each
        # axis is fitted to the box it must fill.
        turned = (verts @ turn.T)
        scale = target / np.maximum(turned.max(0) - turned.min(0), 1e-9)
    scale = scale * clearance

    out = (verts @ turn.T) * scale
    centre = (out.max(0) + out.min(0)) / 2.0
    return out - centre + (ref.max(0) + ref.min(0)) / 2.0, scale, turn


def fit(verts, donor_verts, swap=True, extra=1.0, lift=0.0, fixed=None):
    """Put an incoming mesh where the donor's is, at the donor's size.

    **Morrowind bodyparts are Y-up too, and +Z is forward.** That was measured
    rather than assumed, on the ebony helm: the texture sheet's vertical axis
    runs along -Y with a correlation of 0.998, and the point Faig identified as
    the front of the helm during the colour-band calibration sits at +Z. glTF
    uses the same pair, so **no swap is wanted** - `swap` exists because the
    first attempt applied one, and a swap here is a 90-degree roll about the
    ear-to-ear axis. On screen that is a helmet nodding at the floor, which is
    exactly what it did.

    The base scale fits the incoming bounding box inside the donor's, uniformly
    and off the tightest axis so proportions survive. `extra` multiplies that,
    because a box fit is conservative when a mesh has spikes: the first build
    came out about a third too small.

    **`fixed` overrides that, and for a suit it must.** Fitting each piece to
    its own donor's box gives each piece its own scale, and the donor boxes are
    not proportional to each other - measured, the upper arm's differed from the
    piece's by 3.06 on one axis and 1.00 on another, and the chest's by 3.28.
    Every piece then landed at a different size and the suit came apart. One
    scale for the whole model is the only thing that keeps the pieces in
    proportion with each other; the donor is still used to place the piece, just
    not to size it.
    """
    if swap:
        verts = np.column_stack([verts[:, 0], -verts[:, 2], verts[:, 1]])
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    lo0, hi0 = donor_verts.min(axis=0), donor_verts.max(axis=0)
    scale = (float(fixed) if fixed
             else float(np.min((hi0 - lo0) / np.maximum(hi - lo, 1e-9))) * extra)
    if fixed:
        # Place by centroid, not by box centre. The donor boxes carry outliers -
        # the adamantium cuirass measures 62 units deep where its body is 26 -
        # and a box centre inherits that displacement. The mean of the vertices
        # does not.
        out = (verts - verts.mean(axis=0)) * scale + donor_verts.mean(axis=0)
    else:
        out = (verts - (lo + hi) / 2.0) * scale + (lo0 + hi0) / 2.0
    # Up is local +Y here: the node transform maps it to world +Z, and the
    # bodypart's own origin is the attachment point, so a bounding-box fit can
    # centre a piece correctly and still hang it too low on the body.
    out[:, 1] += lift
    return out, scale


def build(donor_blob, verts, uv, tris):
    head, (flag_a, flag_b, flag_c), tail = donor_parts(donor_blob)
    if len(verts) > 65535:
        raise SystemExit(f"{len(verts)} vertices - the index type is 16-bit")
    nrm = normals(verts, tris)
    centre = (verts.min(axis=0) + verts.max(axis=0)) / 2.0
    radius = float(np.linalg.norm(verts - centre, axis=1).max())

    out = bytearray()
    out += struct.pack("<H", len(verts)) + struct.pack("<I", flag_a)
    out += np.asarray(verts, np.float32).tobytes()
    out += struct.pack("<I", flag_b)
    out += np.asarray(nrm, np.float32).tobytes()
    out += struct.pack("<3f", *centre) + struct.pack("<f", radius)
    out += struct.pack("<I", 0) + struct.pack("<H", 1) + struct.pack("<I", flag_c)
    out += np.asarray(uv, np.float32).tobytes()
    out += struct.pack("<H", len(tris)) + struct.pack("<I", 3 * len(tris))
    out += np.asarray(tris, np.uint16).tobytes()
    return head + bytes(out) + tail


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", help="an .obj carrying the new geometry")
    ap.add_argument("--donor", required=True,
                    help="a game mesh to borrow everything else from")
    ap.add_argument("--out", required=True)
    ap.add_argument("--swap", action="store_true",
                    help="rotate the source into a different up axis - not "
                         "wanted for glTF, which shares Morrowind's")
    ap.add_argument("--fixed-scale", type=float, default=None,
                    help="one scale for every piece of a suit, instead of "
                         "fitting each to its own donor's box")
    ap.add_argument("--lift", type=float, default=0.0,
                    help="raise the piece along the bone, in donor units")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="multiply the fitted scale; a box fit is conservative "
                         "when the mesh has spikes")
    ap.add_argument("--no-fit", action="store_true",
                    help="leave the source at its own scale and position")
    ap.add_argument("--reference", metavar="NIF",
                    help="the vanilla bodypart to align to - same slot, same "
                         "anatomy. Supplies rotation as well as size, which a "
                         "donor's bounding box cannot. Defaults to the donor.")
    ap.add_argument("--axes", metavar="SPEC",
                    help="force the turn, e.g. -z,y,x - where the piece's X, "
                         "Y and Z each land. For a slot whose vanilla part is "
                         "too cubic to rank by length, so the rig has to say.")
    ap.add_argument("--core", metavar="OBJ",
                    help="measure the fit from this mesh but write the source. "
                         "The source carries the overlap that hides a seam, and "
                         "the overlap must not be squeezed into the vanilla "
                         "part's box or the limb inside it comes out short.")
    ap.add_argument("--bone", metavar="NODE",
                    help="fit in world space against the reference hung on "
                         "this skeleton node, then write back into the "
                         "bodypart's own frame. The honest way round: up means "
                         "up for both sides, and no axis has to be guessed.")
    ap.add_argument("--shape", metavar="TEXT",
                    help="use only the reference's shapes whose name contains "
                         "this - `b_n_..._skins.nif` is the Chest bodypart and "
                         "both Hand bodyparts in one file")
    ap.add_argument("--trim", metavar="AXIS",
                    help="keep only one side of the reference, cut at its own "
                         "narrowest cross-section, e.g. z- - for a donor that "
                         "carries a skirt the piece does not")
    ap.add_argument("--clearance", type=float, default=1.0,
                    help="how much bigger than the reference, so armour sits "
                         "over a body rather than inside it")
    ap.add_argument("--texture", metavar="NAME",
                    help="repoint the donor's texture reference, e.g. "
                         "zenar_helm.dds - without this the new mesh wears "
                         "the donor's own texture")
    args = ap.parse_args()

    verts, uv, tris = read_obj(args.source)
    donor_verts, _duv, _dtris = read_mesh(args.donor)
    print(f"incoming {len(verts)} vertices, {len(tris)} triangles")
    print(f"donor    {len(donor_verts)} vertices")

    if args.bone:
        from skeleton import SKELETON, all_shapes, place, shape, unplace
        from skeleton import world as skeleton_frames
        with open(_resolve(SKELETON), "rb") as f:
            frame = skeleton_frames(f.read())[args.bone]
        with open(_resolve(args.reference), "rb") as f:
            parts = all_shapes(f.read(), only=args.shape)
        if not parts:
            raise SystemExit(f"no shape named {args.shape} in {args.reference}")
        ref = np.vstack([place(v, frame) for v, _t, _n in parts])
        turn = axes(args.axes) if args.axes else np.eye(3)
        ours = verts @ turn.T
        core = ours
        if args.core and os.path.exists(args.core):
            core_v, _cuv, _ct = read_obj(args.core)
            core = core_v @ turn.T
        target = ref.max(0) - ref.min(0)
        scale = (target / np.maximum(core.max(0) - core.min(0), 1e-9)
                 * args.clearance)
        shift = ((ref.max(0) + ref.min(0)) / 2.0
                 - (core.max(0) + core.min(0)) / 2.0 * scale)
        ours = ours * scale + shift
        # **Two transforms sit between world space and what gets written**, and
        # only one of them is the bone. The donor's own NiTriShape carries a
        # transform too - the vanilla upper leg's swaps X and Z and shifts ten
        # units - and the engine will apply it to whatever geometry is put in
        # that file. Undoing only the bone left the thigh 13 units tall where
        # its own reference is 38.5.
        with open(_resolve(args.donor), "rb") as f:
            own = shape(f.read())
        verts = unplace(unplace(ours, frame), own)
        print(f"aligned  on {args.bone}, {len(parts)} reference shape(s), "
              f"scale {np.mean(scale):.2f}, world height "
              f"{ref[:, 2].min():.1f} to {ref[:, 2].max():.1f}")
    elif args.reference:
        ref, _ruv, _rt = read_mesh(args.reference)
        if args.trim:
            whole = len(ref)
            ref = trim(ref, args.trim)
            print(f"trimmed  reference {whole} -> {len(ref)} vertices, "
                  f"cut at its own waist")
        verts, scale, turn = align(ref=ref, verts=verts,
                                   clearance=args.clearance,
                                   fallback=args.fixed_scale,
                                   turn=axes(args.axes) if args.axes else None)
        turned = "axes matched by length" if abs(np.trace(turn) - 3) > 1e-6             else "axes as they came"
        print(f"aligned  to {os.path.basename(args.reference)}, "
              f"{len(ref)} vertices, scale {np.mean(scale):.2f}, {turned}")
    elif not args.no_fit:
        verts, scale = fit(verts, donor_verts, swap=args.swap,
                           extra=args.scale, lift=args.lift,
                           fixed=args.fixed_scale)
        print(f"fitted   scale {scale:.3f}"
              f"{', axes swapped' if args.swap else ', axes as they came'}")
    print("bounds   X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f"
          % (verts[:, 0].min(), verts[:, 0].max(), verts[:, 1].min(),
             verts[:, 1].max(), verts[:, 2].min(), verts[:, 2].max()))

    with open(_resolve(args.donor), "rb") as f:
        blob = f.read()
    if args.texture:
        blob, was = retexture(blob, args.texture)
        print(f"texture  {was} -> {args.texture}")
    written = build(blob, verts, uv, tris)
    with open(args.out, "wb") as f:
        f.write(written)
    print(f"written  {args.out}, {len(written):,} bytes "
          f"(donor was {len(blob):,})")
    print("Now ask the engine:  niftest.exe " + args.out)
    return 0


def _resolve(rel):
    """The donor as a real file, extracted from a BSA if it only lives there."""
    if os.path.exists(rel):
        return rel
    from bsa import find, open_archives
    from uvmap import BSA_DIR, MASTER_BSAS
    archives = open_archives([os.path.join(BSA_DIR, n) for n in MASTER_BSAS])
    hit = find(archives, rel.replace("\\", "/").lower())
    if not hit:
        raise SystemExit(f"donor not found: {rel}")
    scratch = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "build", "donor-" + os.path.basename(rel))
    scratch = os.path.abspath(scratch)
    os.makedirs(os.path.dirname(scratch), exist_ok=True)
    with open(scratch, "wb") as f:
        f.write(hit[0].read(hit[1]))
    return scratch


if __name__ == "__main__":
    sys.exit(main())
