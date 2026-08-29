# Particle textures — measured, prototyped, not shipped

*Canon* Part 9 settled the design in August; this is the measurement and the
implementation. Nothing has been written into `mod/` yet.

## Where the leverage is

The particle texture is named in the magic effect record's `texture` field, not
in the NIF. 141 effects reference 36 different textures, and the distribution is
lopsided enough to make the plan obvious:

| Texture | Effects | |
| --- | --- | --- |
| `vfx_conj_flare02` | **31** | conjuration flares, the summons |
| `vfx_bluecloud` | **28** | |
| `vfx_redglowalpha` | 13 | |
| `vfx_particle064` | 9 | |
| `vfx_summon` | 2 | |
| `vfx_corprus` | 1 | the dense variant Part 9 reserves |

Two files cover 59 effects of 141. Four cover 81. That is what Part 9 means by
"replacing one DDS changes every cast in the game".

## What is installed there now

All six resolve, through `delta_plugin vfs-find`, to the same place:

    ...\TexturePacks\VurtsMorrowindVisualResurgence\vfx\Data Files\Textures\

**Vurt's Morrowind Visual Resurgence.** Not the vanilla BSA. So this is not
replacing Bethesda's work, it is overriding a visual overhaul the player chose
and installed, and that is a decision for him rather than a technical detail.
All six are 512x512 DXT5.

## The generator

`tools/scripts/make_vfx.py`, following Part 9 to the letter:

* **Alpha carries the shape**, with a smoothstep falloff on every hexagon,
  because a hard edge under additive blending reads as a rendering fault.
* **A sparse grid**, not one hexagon. The dense variant is the same generator
  with the cell size and softness changed, and it is used for `vfx_corprus` and
  nothing else.
* **The colour is taken from the file already installed**, sampled from its own
  brightest pixels. Fire stays warm, frost stays cold, and only the structure
  becomes theirs. The alternative - inventing a colour - would have made every
  school look identical, which is a bigger change than the one being asked for.
* A faint core and a radial vignette: without the core the grid falls below a
  pixel at distance and flickers out, and without the vignette the particle
  shows its own square quad against the sky.
* **No geometry, no NIF, no animation.** A particle is a camera-facing billboard
  a few dozen pixels across for a fraction of a second.

Output is uncompressed 32-bit BGRA DDS - no DXT compressor needed and the engine
reads it. Six files at 1 MB each against 256 KB, which is not worth a
compressor for six textures.

## Still open

Whether to ship at all, given that it overrides Vurt's. And the grain shader,
which Part 9 puts in post-processing rather than in particles - not started.
