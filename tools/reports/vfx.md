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

### That reading of the table was wrong, and the game said so

The six shipped. Faig cast three spells and reported that only the summons had
changed - hexagons on `summon flame atronach`, a plain vanilla glow on the next
thing he tried.

He was right, and the same table says why if you read the other column: six
files are 85 of 141, so **56 effects were still vanilla**. The lopsided
distribution made a top-six look like most of the game; what it actually buys is
three fifths. And a conversion that covers three fifths of the schools does not
read as a style, it reads as a bug - the player sees his own casting change
denomination between one spell and the next.

The fix is not a bigger top-N. It is to stop picking: **the target list is now
read out of the masters**, every texture any magic effect names, and the six
hand-picked names are gone from the source. 35 textures, 141 of 141 effects.

The long tail is genuinely long and genuinely cheap - 20 of the 35 textures
serve a single effect each - but it is where the schools live. `vfx_myst_flare01`
is five Absorb effects, `vfx_map21` is five Drains, `vfx_ill_glow` is Open and
Lock. Any of them is the next spell a player casts.

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

## Corprus is torn

The distinction Part 9 wanted is back, and made of shape rather than density.
Half the Corprus plates lose one or two of their six sides, and what fill they
have is dimmed. Healthy casting never shows a broken plate. Same material,
damaged - which is what Canon Part 3a says Corprus is.

## Fifth pass: every school, not the top six

Confirmed on screen first - the sparse field reads as machinery in motion, which
is the judgement no still image could give. Then the coverage was fixed.

### The list comes from the masters

`effect_textures()` walks the three converted masters, takes each magic effect's
`texture` field with the last master winning, and returns texture to effects.
141 effects, 36 textures. Nothing is hand-picked and nothing can silently fall
out of the set: add a mod that introduces an effect and the generator picks up
its texture the next time it runs.

### The one texture that is not a magic texture

`tx_firealpha00a`, and the `tx_` prefix is the tell - Bethesda's prefix for
ordinary world surfaces, against `vfx_` for magic. Where it resolves confirms
it: not in Vurt's vfx pack but in **Morrowind Enhanced Textures**, a landscape
and architecture pack. It is the flame sheet, worn by every torch, brazier and
campfire in the game. One magic effect borrows it: **Light**.

Overriding it would put hexagons on every fire in Vvardenfell in order to
convert one spell. So it is excluded by name, with the reason in the code.

**Light is still converted, by a different route.** The generator writes a
private copy, `vfx_zen_light.dds`, colour sampled from the flame so the spell
keeps its warm light, and `mod/scripts/rewrite/apply.lua` points the effect
record at it - `rec.particle = 'vfx_zen_light.dds'`.

That write is **guarded and unproven**. `particle` is documented as a field of
`MagicEffect` and `content.magicEffects.records` as mutable, but it was not one
of the WO0 probes and no readback has established that this field has a setter
in 0.51. So the code reads the value, writes, reads back, and logs all three. If
the engine refuses, Light keeps the vanilla flame and nothing else is touched.
Grep the log for `[REWRITE] light:` to find out which happened.

### One field, thirty-six colours

The hexagon field does not depend on the source at all - same size, same seed,
same cell. So it is computed once for sparse and once for Corprus and reused,
which is why 36 textures take about the same time the six did.

That is not an optimisation dressed up as a principle. It is the fiction: one
technology has one structure, and what differs between schools is the light it
is lit by. The light is sampled, never chosen - fire comes back 255/89/8, frost
196/235/255, poison 224/255/16, mysticism 235/64/255.

**Proof the refactor changed nothing Faig approved:** the six textures he saw
regenerate byte for byte identical, checked pixel by pixel against the shipped
files.

### The BSA reader

`--profile vanilla` needs the vanilla originals to sample from, and the first
pass got them with `delta_plugin vfs-extract`, which is not in the repo.
`tools/scripts/bsa.py` reads the 2002 archive format directly - about forty
lines - and is **verified against `delta_plugin`**: the six files the first pass
extracted come back byte for byte identical. All 36 textures are present in the
three vanilla BSAs, so the vanilla build has no external dependency left.

## Sixth pass: half the plate, same file

Faig's note on seeing the full coverage: smaller hexagons.

**The limit is the rim, not the cell.** Rendered a strip at 20 / 26 / 32 / 40
plates across at 512. At 32 the plates are rings; at 40 they are grit. The
falloff is a fixed 1.4 px, so shrinking the plate does not shrink its outline,
and a plate needs about four pixels of radius before six straight sides survive.
Turning the cell size down alone cannot deliver what he asked for.

**The way under the floor is resolution.** At 1024 a plate with the same pixel
crispness covers half as much of the texture, so 36 across is finer than 20 was
and still hexagonal. The obvious objection is memory, and this is where the
earlier refusal to compress gets reversed.

### DXT5, measured this time rather than assumed

The first write-up rejected DXT5 on the reasoning that it quantises alpha in 4x4
blocks while this texture is nothing but thin rims and one-pixel filaments in
alpha - so the artifacts would land exactly where the design lives. Plausible,
and wrong. Measured on the 1024 field:

* mean alpha error **1.5 of 255**;
* 1.6% of pixels off by more than 20, every one of them on a rim gradient;
* side by side at 3x magnification there is nothing to see.

And the arithmetic is the whole argument: **1024 DXT5 is 1,398,256 bytes against
1,398,228 for the 512 uncompressed it replaces.** Twice the resolution, 28 bytes.
The rejection cost nothing to make and would have cost the whole improvement to
keep.

`--format rgba` still builds the uncompressed form at any size, which is what
any future artifact should be compared against.

### Mips are no longer a separate command

`add_mips.py` is gone. Its whole purpose was a second step run after the
generator, and forgetting it once nearly shipped 36 mipless textures - the
defect was the separateness. The chain is now built inside the writer, and the
writer itself moved to `tools/scripts/dds.py` so that `make_vfx.py` and
`make_armour.py` do not each carry a hand-written DDS header. Verified across
that move: all 36 particle textures regenerate byte for byte identical.

### The generator stopped painting the whole canvas

Every plate, thread and mote used to be evaluated over the full array. At 512
that was slow; at 1024 it was over ten minutes a profile, which is too slow to
iterate on a look. Each now writes into its own bounding box - a plate reaches
`(radius + edge) / 0.866`, since hexagon distance is never below 0.866 of the
euclidean one and so cannot clip a contributing pixel.

**Thirty seconds a profile, down from ten minutes.** Checked against the old code
at 512 sparse and dense: the float fields agree to 1e-7, and after quantisation
**one colour byte in 1,048,576 lands a level apart, none of them in alpha.**

## Written

Both builds are on disk:

    tools/build/vfx-vanilla/Textures/*.dds     36 files, 1.4 MB each
    tools/build/vfx-momw/Textures/*.dds        36 files

1024x1024 DXT5 with a full 11-level mipmap chain, 49 MB a profile. Add one
`data=` line for the matching profile; remove the line to remove the change.
Nothing was written into `mod/`, which stays shared.

## Confirmed in the real profile

2026-08-29, `play` profile, Vivec exterior. Light, `self dispel` and `hearth
heal` cast in turn: each a hexagon swarm in its own colour, plates at the finer
size. `hearth heal` is the one that matters most - `vfx_bluecloud` is 28 effects,
the largest group after the summons, and it was vanilla until this pass.

**The Light redirect took.** From the log:

    [REWRITE] light: particle tx_firealpha00A.tga -> vfx_zen_light.dds

So `MagicEffect.particle` is writable from the load context in 0.51, which
nothing documented and no probe had established. Verified the two ways the
working method asks for: the readback in the context that wrote it, and the
engine's own use of the field on screen.

Zero errors in the log touching our textures, and no complaint about the DXT5
files - the hand-written header and mip chain are read as the engine expects.

## Still open

The grain shader, which Part 9 puts in post-processing rather than in particles.
Not started. It is the only part of Part 9 that is not in the game.
