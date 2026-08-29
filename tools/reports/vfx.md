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

## Two builds, as with the plugin

`--profile momw` samples colour from Vurt's; `--profile vanilla` samples it from
the textures extracted out of `Morrowind.bsa` with `delta_plugin vfs-extract`,
which are 64x64 DXT3 against Vurt's 512x512 DXT5. Both are generated at 512:
the hexagons need the resolution, and a sharper particle is the signature.

Output goes to `tools/build/vfx-<profile>/Textures/`, a data directory the user
adds - one line, and removing the line removes the change. Nothing is written
into `mod/`, which stays shared between both profiles.

## The second pass on the shape

The first draft drew soft filled hexagons, and Faig's read of it was right: they
were blobs, and a blob does not look manufactured. Rebuilt around three ideas:

* **Plates rather than blobs.** A bright rim with a dim interior, the falloff
  only a couple of pixels wide. A filled soft hexagon smudges at particle size;
  an outlined one keeps its six sides, which is the only thing that says
  somebody made it. Each plate is rotated a little, because a lattice reads as a
  texture bug.
* **Filaments.** Short tapering threads to one or two neighbours - never all of
  them, since a fully connected mesh reads as a net rather than as a swarm.
  This is what makes the cloud look like it is holding itself together.
* **Motes.** Sub-pixel specks in the gaps at low alpha, so the empty space does
  not look deliberate.

## Third pass: scale

The plates were five across the texture, which at particle size is a handful of
slabs. Faig's word was megaliths and it was accurate. Now twenty across for
casting and thirty for Corprus, with the size drawn from three buckets - 45% of
plates small, 35% medium, 20% large - because a field of one-size plates reads
as a print and a swarm has to look like a population.

The rim is down to a pixel of falloff, the central core is nearly gone, and
there are twice as many motes.

**This narrows a distinction Part 9 makes deliberately.** Canon separates the
Zenaric cast from Corprus by density: sparse structure for casting, dense swarm
reserved for Corprus. With casting now fine-grained, the two differ by density
alone - 20 across against 30 - and both read as a swarm.

If Corprus needs to stay unmistakable, the cheapest way is **broken plates**:
half its hexagons missing a side or two, which healthy casting never shows. Same
material, damaged. Not implemented; it is one branch in the generator.

## Fourth pass: the threads read

Filaments a touch stronger, on Faig's note and nothing else touched: width up a
fifth, brightness 0.30 to 0.44, and their contribution to the combined alpha
0.85 to 0.95. The plates are unchanged.

They matter more than their size suggests. The plates alone are a scatter; the
threads are what makes it one thing moving together, which is the difference
between dust and a swarm.

**Approved for the first iteration** at this point - shape settled, both builds
generating, nothing shipped yet.

## Still open

Whether to ship at all, given that it overrides Vurt's. And the grain shader,
which Part 9 puts in post-processing rather than in particles - not started.
