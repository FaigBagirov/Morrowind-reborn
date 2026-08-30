#!/usr/bin/env python3
"""Cut a suit of armour in one OBJ into the pieces Morrowind wears.

    python tools/scripts/obj_split.py suit.obj out/

Faig's question: if he finds a whole set as one file, can it be cut up. Yes, and
this is the half of the job a script does *better* than a person - unlike
sculpting, which it does worse. Two ways, tried in order:

**By label.** OBJ carries `o`, `g` and `usemtl` lines, and anything exported
from a modelling package almost always has them. Then the cut is reading, not
guessing, and it is exact.

**By connected component.** With no labels, pieces are separated by which
triangles share vertices: a helmet is not welded to a cuirass, so they fall
apart on their own. Union-find over the shared vertices, which is standard and
reliable.

There is a third way and it is bad: cutting by a plane through a single welded
shell. That leaves open holes needing new geometry along the cut, which is
sculpting again. It is not implemented, and a set that needs it is the wrong set
to start from.

## What the pieces then have to fit

Morrowind dresses a body from separate rigid parts - head, chest, groin, hands,
forearms, upper arms, clavicles, knees, ankles, feet - so no skinning is needed,
which is the good news. The bad news is the budget. Measured on the vanilla
Daedric set, one shape runs **50 to 620 vertices**, most of them between 50 and
180. A modern game's cuirass is tens of thousands.

And a piece still has to land in Morrowind's own coordinates at Morrowind's own
scale. `--fit` reports what transform each piece would need to sit inside a
named vanilla part's bounding box; it does not apply it, because a bounding box
is a crude thing to trust with a silhouette.
"""

import argparse
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from obj import read, write  # noqa: E402
from uvmap import read_mesh  # noqa: E402


def by_label(tris, labels):
    groups = defaultdict(list)
    for i, name in enumerate(labels):
        groups[name].append(i)
    return {k: np.array(v, np.int32) for k, v in groups.items()}


def by_component(tris, count):
    """Union-find over vertices shared by triangles."""
    parent = list(range(count))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b, c in tris:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[rc] = ra

    groups = defaultdict(list)
    for i, (a, _b, _c) in enumerate(tris):
        groups[find(a)].append(i)
    ordered = sorted(groups.values(), key=len, reverse=True)
    return {f"part{n + 1:02d}": np.array(v, np.int32)
            for n, v in enumerate(ordered)}


def extract(verts, uv, tris, face_ids):
    """A standalone mesh from a subset of faces, reindexed from zero."""
    used = np.unique(tris[face_ids])
    remap = {old: new for new, old in enumerate(used)}
    sub = np.array([[remap[i] for i in tri] for tri in tris[face_ids]], np.int32)
    return verts[used], uv[used], sub


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", help="the OBJ to cut")
    ap.add_argument("out", nargs="?", help="directory for the pieces")
    ap.add_argument("--by", choices=["auto", "label", "component"],
                    default="auto")
    ap.add_argument("--fit", metavar="NIF",
                    help="report the transform each piece needs to sit inside "
                         "this vanilla mesh's bounds")
    args = ap.parse_args()

    verts, uv, tris, labels = read(args.source, want_groups=True)
    distinct = len(set(labels))
    mode = args.by
    if mode == "auto":
        mode = "label" if distinct > 1 else "component"
    print(f"{len(verts)} vertices, {len(tris)} triangles, "
          f"{distinct} label(s) -> cutting by {mode}")

    pieces = (by_label(tris, labels) if mode == "label"
              else by_component(tris, len(verts)))

    target = None
    if args.fit:
        tv, _tuv, _tt = read_mesh(args.fit)
        target = (tv.min(axis=0), tv.max(axis=0))
        print(f"fitting against {os.path.basename(args.fit)}: "
              f"{len(tv)} vertices, size {np.round(target[1] - target[0], 2)}")

    if args.out:
        os.makedirs(args.out, exist_ok=True)
    print(f"\n{'PIECE':<20}{'VERTS':>7}{'TRIS':>7}  SIZE")
    for name, face_ids in pieces.items():
        pv, puv, pt = extract(verts, uv, tris, face_ids)
        size = pv.max(axis=0) - pv.min(axis=0)
        note = ""
        if len(pv) > 620:
            note = "  OVER BUDGET - vanilla shapes are 50 to 620 vertices"
        print(f"{name:<20}{len(pv):>7}{len(pt):>7}  {np.round(size, 2)}{note}")
        if target is not None:
            want = target[1] - target[0]
            scale = np.divide(want, size, out=np.ones(3),
                              where=size > 1e-6)
            print(f"{'':20}would need scale {np.round(scale, 3)}, "
                  f"offset {np.round(target[0] - pv.min(axis=0) * scale, 2)}")
        if args.out:
            write(os.path.join(args.out, f"{name}.obj"), pv, puv, pt, name)
    if args.out:
        print(f"\nwritten to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
