# Zenaric armour — retexture, first iteration `BUILT, NOT YET SEEN ON SCREEN`

Generator `tools/scripts/make_armour.py`. Output
`tools/build/armour-momw/Textures/jy_daedric/`, 15 files, added to the profile
with one `data=` line and removed by deleting it.

## The brief and the one hard limit

Faig's reference is a white-and-gold ceramic mech suit; his instruction was
"something like this but with notes of the original Daedric armour".

**No geometry.** The project rules and Canon Part 9 both forbid generating NIFs:
the engine validates models on load and rejects machine-assembled ones. So the
silhouette does not change — the spikes, the horned helm, the sculpted muscle
plates all stay.

That is not a compromise here, it is the answer to the second half of the brief.
The notes of the original *are* the mesh and its normal map, and they cost
nothing.

## What the source gives us

Daedric Lord Armor ships four channels a piece: diffuse, `_g` glow, `_n` normal,
`_s` specular. Only one directory in the whole 772-entry load order provides
`Textures/jy_daedric`, so there is nothing to collide with.

**We write the diffuse and the glow, and nothing else.** Our data directory only
overrides the files it contains, so the mod's own normal and specular maps keep
being used. The sculpt and the gloss stay the original artist's work, which is
the best part of that mod.

## Where the structure comes from, and why not the diffuse

The diffuse is nearly useless as a source of tone. Measured on `daecuir`: median
luminance 0.094, p90 0.191. The entire sculpt lives in a narrow dark band, and
stretching that band alone turns DXT compression noise into visible dirt.

The **specular map** has the range — mean 0.244, p25 0.110, p75 0.353 — and
carries the same sculpt. More than that, it carries a judgement we would
otherwise have to guess at: the artist painted hard armour bright and cloth,
leather and mail dark. So it separates plate from underlayer better than
anything we could infer, and `plate` is built from it.

| Signal | Comes from | Decides |
| --- | --- | --- |
| `plate` | specular, thresholded and blurred | ceramic or dark mechanism |
| `tone` | specular for range, diffuse for grain | how lit that pixel is |
| `trim` | red-dominance in the diffuse | where the gold goes |

Nothing is placed by hand. The gold lands exactly on the veins and seams the
artist already picked out in red.

## Three corrections the previews forced

1. **Everything was white.** The first pass had no plate mask, so plates,
   cloth and mail all came out ceramic and the piece read as one bright slab.
   The reference has hard black separation between plates; the mask is what
   produces it.
2. **The collar and the cuirass's fabric panel turned solid gold.** Red in the
   source marks the hot veins, but it also marks dyed leather and cloth, and
   both of those are red end to end. Weighting `trim` by the plate mask keeps
   gold bright where it is inlaid into armour and dull on anything soft.
3. **Cracked porcelain.** Fine veining that barely shows on charcoal became a
   black web on a white plate. The tone is now split into large-scale form and
   fine grain, and the grain is dialled to 0.35.

## The open question, and it is not mine to answer

The large dark mottling on the helm and cuirass survives all of that, and it is
not noise: it is the Daedric coral pattern, which the artist painted with **low
specular**, so the mask correctly calls it not-plate and it comes out near
black.

So the plates are white with dark organic veining rather than the clean panels
of the reference. That reads as a deliberate material to me and it is a strong
note of the original — but it is a look, not a bug, and looks are Faig's call.
If he wants the plates cleaner, the lever is the `plate` threshold in
`_norm(s_n, 0.34, 0.66)`: widening the low end pulls the coral back into
ceramic.

## Scope, deliberately narrow for this iteration

Done: the worn set and the mod's blade — `daecuir`, `daeboots`, `daegaunt`,
`daegreaves`, `daefacei`, `daefacet`, `daeneck`, `daedrickatana`.

Left alone on purpose:

* **Dremora skin** (`DremoraNeck`, `DremoraEars`, `daefacehair`). A creature's
  body, not equipment. What the Zenar themselves look like is a separate
  decision and a bigger one.
* **Vanilla Daedric weapons and shields**, ~40 `tx_w_*_daedric*` and
  `tx_a_shield_daedric*` textures. The same generator would run on them, but
  they have **no specular map** in this load order — the only `_n`/`_spec` files
  the modpack adds under "04 Daedric" are for the *ruins* architecture. So they
  need the structure derived from the diffuse alone, which is a different tuning
  problem. Worth doing: a white cuirass beside a black dai-katana will show.
* **Daedric ruins and shrines** (`tx_a_daedric_fountain_*`, `_god_*`). Those are
  Zetic, the cult's architecture, not Zenaric manufacture. Different word,
  different look, and they are everywhere in the world. Not in scope by meaning,
  not by effort.

## Format

DXT1 with a full mip chain, written through `tools/scripts/dds.py`. The
originals are DXT1 and every one of these textures is fully opaque — checked,
only `daefacehair` carries alpha and that is Dremora hair, which we do not
touch. File sizes come out within 8 bytes of the originals.

## Canon

*Canon* Part 9 describes the particle visuals and says nothing about what
Zenaric equipment is made of. This is the first answer to that, and it came from
Faig's reference rather than from the documents. If the look is kept it belongs
in Part 9 as a settled decision.
