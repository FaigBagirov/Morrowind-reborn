#!/usr/bin/env python3
"""Paint a few bold panel features onto the closed helm.

Drawn on top of the converted texture, never instead of it, so the plate colour,
the marbling, the kant and the baked sheen come through and the helm belongs to
the same set as the cuirass. Faig asked for that in as many words.

## Similar, not identical

His steer, and it is the right one: make it *like* the reference, not a copy of
it. The helmet is about a hundred pixels tall on screen, so anything finer than
a few texture pixels is mush at the only distance that matters. Few shapes, big,
legible. A greeble field would be work spent on something nobody can see.

## How placement works, and what it costs

Two coordinate systems were tried.

Rasterising the mesh gives an exact per-pixel map - `uvmap.py` still does, and
its **coverage mask is used here**, which is what keeps the drawing on the
helmet instead of across the empty margins. But this mesh's UV islands overlap
heavily: different parts of the shell share the same pixels, and resolving that
by "the surface furthest out wins" turns the azimuth map into a patchwork. The
mesh simply does not carry a clean unwrap to paint on.

What it does carry is enough for the *visible* surface, and the calibration
screenshot proves it: the eight colour bands came out in order across the front
of the helm. So placement is done in sheet coordinates, anchored on the two
readings Faig took, and refined against screenshots rather than derived.

    FRONT_U = 0.8125   the violet band, measured on screen
    EYE_V   = 0.56     the bottom rule, measured on screen

That is worth perhaps ten or twenty degrees of imprecision, which is why every
feature here is wide enough not to care.

## Why the relief is faint

No geometry is generated - the rules forbid it - so depth is faked with a dark
groove and a lit lip above it. It stays subtle on purpose: the shading is baked
from one direction while the engine lights the helm from wherever the sun is, so
a strong bake contradicts the real light the moment the player turns round.
"""

import numpy as np

FRONT_U = 0.8125        # measured on screen, 2026-08-30
EYE_V = 0.56

CROWN_SEAM_V = 0.300
BROW_V = 0.487
VISOR_TOP = 0.505
VISOR_BOTTOM = 0.605
FLARE_V = 0.638

# All four sit close together on purpose. The first pass in game came out as
# black-and-white stripes because every one of these was far from the plate it
# was drawn on.
DARK = np.array([0.105, 0.110, 0.125], np.float32)    # a groove
VISOR = np.array([0.135, 0.142, 0.160], np.float32)   # the face plate
LIP = np.array([0.62, 0.638, 0.672], np.float32)      # the lit edge of a panel
OPTIC = np.array([0.52, 0.70, 0.80], np.float32)      # the slit itself


def _turns(a):
    return (a + 0.5) % 1.0 - 0.5


def _span(x, lo, hi, soft):
    """1 inside [lo, hi], falling to 0 over `soft` either side."""
    return (np.clip((x - lo) / soft + 1.0, 0.0, 1.0)
            * np.clip((hi - x) / soft + 1.0, 0.0, 1.0))


def _rule(x, at, half, soft):
    return _span(np.abs(x - at), -1.0, half, soft)


def paint(rgba, cover=None, strength=1.0):
    """Return the texture with the panel features drawn on it."""
    h, w = rgba.shape[:2]
    rows, cols = np.mgrid[0:h, 0:w].astype(np.float32)
    v = rows / (h - 1)
    u = cols / (w - 1)
    du = _turns(u - FRONT_U)
    out = rgba.copy()
    body = (np.ones((h, w), np.float32) if cover is None
            else np.asarray(cover, np.float32))

    def lay(mask, colour, amount=1.0):
        m = np.clip(mask * body * strength * amount, 0.0, 1.0)[..., None]
        out[..., :3] = out[..., :3] * (1.0 - m) + colour * m

    def groove(mask, depth=1.0, lip=0.5):
        lay(mask, DARK, depth)
        lifted = np.roll(mask, -max(int(h * 0.003), 1), axis=0)
        lay(np.clip(lifted - mask, 0.0, 1.0), LIP, lip)

    # Two seams down the crown, stopping well short of the top. Lines of
    # constant azimuth all the way to the pole converge there and read as a
    # cracked eggshell, which is what the first attempt looked like.
    crown = _span(v, 0.115, BROW_V - 0.01, 0.045)
    for side in (1.0, -1.0):
        groove(_rule(du, side * 0.132, 0.0022, 0.0022) * crown, 0.75, 0.45)
    groove(_rule(v, CROWN_SEAM_V, 0.0025, 0.0025), 0.5, 0.35)

    # The brow, and the face plate under it. The visor stops at the temples: it
    # is a plate, not a belt.
    groove(_rule(v, BROW_V, 0.0035, 0.003), 0.95, 0.6)
    front = _span(np.abs(du), -1.0, 0.105, 0.028)
    lay(_span(v, VISOR_TOP, VISOR_BOTTOM, 0.008) * front, VISOR, 0.88)
    groove(_rule(v, VISOR_BOTTOM, 0.003, 0.003) * front, 0.9, 0.5)

    # One continuous slit, not two eyes. Two came out as four on screen: this
    # unwrap maps several parts of the shell onto the same pixels, so anything
    # drawn once appears more than once. A single band across the front is
    # immune to that - duplication merely extends it - and a continuous visor
    # line is closer to the reference anyway.
    recess = (_span(np.abs(du), -1.0, 0.088, 0.010)
              * _span(v, EYE_V - 0.016, EYE_V + 0.016, 0.004))
    lay(recess, DARK, 1.0)
    lens = (_span(np.abs(du), -1.0, 0.082, 0.008)
            * _span(v, EYE_V - 0.007, EYE_V + 0.007, 0.003))
    lay(lens, OPTIC, 0.9)

    # Where the shell ends and the neck flare begins.
    groove(_rule(v, FLARE_V, 0.0035, 0.003), 0.9, 0.45)
    return np.clip(out, 0.0, 1.0)
