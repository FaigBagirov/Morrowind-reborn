#!/usr/bin/env python3
"""Paint a Pragmata-style panel layout onto the closed helm.

Drawn on top of the converted texture, never instead of it, so the plate colour,
the marbling, the kant and the baked sheen all come through and the helm belongs
to the same set as the cuirass. Faig asked for that in as many words: it has to
feel like a suit, not a hat from another game.

## Everything is placed on the helmet, not on the sheet

The first version drew in sheet coordinates and assumed the horizontal axis ran
evenly around the head. It does not. This helm's unwrap is closer to a side
projection: a straight-line fit of u against azimuth leaves 0.10 turns of
residual - 36 degrees - and the drawing landed across the empty margins as well
as the helmet.

So the layout is specified where it belongs, in **height and azimuth on the
actual helmet**, and `uvmap.py` rasterises the mesh's own triangles to tell each
pixel which point of the helmet it is. No fit, no residual.

Two numbers anchor it, and only one of them could not be computed:

    FRONT_AZ = +0.0873   which way the helmet faces
    EYE_H    = -0.30     the height of the eyes

Geometry cannot say which way a helmet faces, so that was measured on screen:
`uv_calibrate.py` painted eight named colour bands and three rules, Faig wore it
and looked, and reported violet at the front and the bottom rule on his eyes.
Those two readings became these two numbers.

Height landmarks on this helm, read off the rasterised map: crown +8.6, the wide
band +4.0, the stud row +1.5, eyes -0.3, the neck flare below -1.7.

## Why the relief is faint

No geometry is generated - the rules forbid it - so depth is faked with a dark
groove and a lit lip. It stays subtle on purpose: the shading is baked from one
fixed direction while the engine lights the helm from wherever the sun is, and a
strong bake contradicts the real light the moment the player turns round. Soft
edges survive that. Dramatic chiaroscuro does not.
"""

import numpy as np

FRONT_AZ = 0.0873       # measured on screen, 2026-08-30
EYE_H = -0.30

VISOR_TOP = 1.15        # heights, in the mesh's own units
VISOR_BOTTOM = -1.55
BROW_H = 2.35
CROWN_SEAM_H = 5.25
FLARE_H = -1.95

DARK = np.array([0.055, 0.060, 0.072], np.float32)    # a groove
VISOR = np.array([0.048, 0.053, 0.066], np.float32)   # the face plate
LIP = np.array([0.74, 0.77, 0.83], np.float32)        # the lit edge of a panel
OPTIC = np.array([0.60, 0.78, 0.88], np.float32)      # the slit itself


def _turns(a):
    """Wrap a difference in turns to -0.5 .. 0.5."""
    return (a + 0.5) % 1.0 - 0.5


def _span(x, lo, hi, soft):
    """1 inside [lo, hi], falling to 0 over `soft` either side."""
    return (np.clip((x - lo) / soft + 1.0, 0.0, 1.0)
            * np.clip((hi - x) / soft + 1.0, 0.0, 1.0))


def _line(x, at, half, soft):
    return _span(np.abs(x - at), -1.0, half, soft)


def paint(rgba, height, azimuth, cover, strength=1.0):
    """Return the texture with the panel layout drawn on it.

    `height`, `azimuth` and `cover` come from `uvmap.rasterise` and
    `uvmap.polar` - per pixel, where on the helmet this pixel lands and whether
    it lands on it at all. Nothing is drawn off the helmet.
    """
    out = rgba.copy()
    body = np.asarray(cover, np.float32)
    da = _turns(azimuth - FRONT_AZ)      # 0 dead ahead
    ahead = np.abs(da)

    def lay(mask, colour, amount=1.0):
        m = np.clip(mask * body * strength * amount, 0.0, 1.0)[..., None]
        out[..., :3] = out[..., :3] * (1.0 - m) + colour * m

    def groove(mask, depth=1.0, lip=0.5):
        """A dark line with a lit edge above it: the only depth cue available."""
        lay(mask, DARK, depth)
        lifted = np.roll(mask, -2, axis=0)
        lay(np.clip(lifted - mask, 0.0, 1.0), LIP, lip)

    # --- the crown --------------------------------------------------------
    # Panel seams running up the dome were tried and cut. Lines of constant
    # azimuth converge at the pole, and a helmet with six lines meeting on the
    # crown reads as a cracked eggshell rather than as panelling. Doing it
    # properly means seams that stop short of the top and vary in width, which
    # is art direction and wants its own round.
    groove(_line(height, CROWN_SEAM_H, 0.10, 0.10), 0.55, 0.4)

    # --- the brow ----------------------------------------------------------
    groove(_line(height, BROW_H, 0.10, 0.09), 1.0, 0.65)

    # --- the visor ---------------------------------------------------------
    # A face plate, not a belt: it stops at the temples.
    front = _span(ahead, -1.0, 0.150, 0.045)
    face = _span(height, VISOR_BOTTOM, VISOR_TOP, 0.18) * front
    lay(face, VISOR, 0.90)
    groove(_line(height, VISOR_BOTTOM, 0.09, 0.09) * front, 1.0, 0.55)

    # --- the eye slits -----------------------------------------------------
    # Opaque, as asked: a dark recess with a bright inner line, which is what
    # reads as a lens at this size rather than as a hole.
    for side in (1.0, -1.0):
        centre = side * 0.052
        slit = (_span(np.abs(da - centre), -1.0, 0.034, 0.006)
                * _span(height, EYE_H - 0.62, EYE_H + 0.62, 0.10))
        lay(slit, DARK, 1.0)
        inner = (_span(np.abs(da - centre), -1.0, 0.028, 0.005)
                 * _span(height, EYE_H - 0.30, EYE_H + 0.30, 0.07))
        lay(inner, OPTIC, 0.85)

    # --- the neck flare ----------------------------------------------------
    groove(_line(height, FLARE_H, 0.09, 0.09), 1.0, 0.5)
    for ring in (-3.55, -5.05):
        groove(_line(height, ring, 0.07, 0.07), 0.45, 0.3)

    return np.clip(out, 0.0, 1.0)
