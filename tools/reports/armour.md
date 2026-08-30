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

## Second pass: darker, with a kant and a sheen

Faig's notes after seeing it in game: silver rather than bone white, then a step
darker than the darkest of the four shown, an illusion of gloss, and darkening
along the edges and piping.

* **0.50 for the plate**, blue channel leading. Four options were rendered at
  0.95 / 0.83 / 0.72 / 0.60 first; this is under all of them.
* **The kant.** The obvious source is the normal map's own tilt, and it is the
  wrong one: on this sculpt almost nothing is flat, so darkening by tilt darkens
  everything evenly and reads as nothing. What reads as an edge is one plate
  ending and the next beginning, so the line comes from the **gradient of the
  plate mask**. That is what makes the abdominal ribs legible.
* **The sheen** is baked from the mod's normal map, which until now we had not
  used at all - one fixed light, two terms out of one dot product. A broad one
  so a plate reads as curved rather than flat, and a tight one for the glint.
  Kept low: the engine does the real lighting and this is only the material.

### Gold is now per piece

Faig on the Face of Terror: the colours are right, take the gold off. `NO_GOLD`
holds the pieces that go without it, and the trim does not simply vanish for
them - those lines are the design, and a helm with no piping reads as
unfinished. It goes to a brighter cool steel instead, and the glow follows the
same decision, since amber piping on a helm with no gold piping would
contradict itself.

## The marbling was the right answer, and it is settled

The open question was the dark mottling: the Daedric coral pattern, painted
low-specular, coming through as veining on a pale plate. It was flagged as a
look rather than a defect, and Faig's call went the other way from the guess -
he liked it on the helm and asked for the **cuirass to match**.

The cuirass had less of it because the grain was dialled to 0.35, back when the
plate was bone white and the veining read as cracked porcelain. At 0.50 it does
not: it reads as marble. Grain is now **1.0** across the suit, and the character
is consistent from helm to boot.

Worth keeping: the same number was wrong at one plate colour and right at
another. It was never a property of the veining.

## The closed helm

Faig chose the **Ebony Closed Helm** shape over the horned Daedric one, from a
catalogue built out of the game's own inventory icons - 47 helmets, real
pictures rather than mesh names. Reference for the material: the Pragmata
helmet, which is a pale shell with dark mechanism and yellow accents.

Its source is `tx_a_ebony_helmet`, replaced in this list by Morrowind Enhanced
Textures, and it needed three per-piece settings and one new step:

* **`plate_from: diffuse`.** Its specular map is a *highlight* map - near black
  with a few glints - not a hardness map. Used as the plate mask it calls the
  whole helm mechanism; used as tone it drags the piece to black.
* **`trim: warm`.** Its trim is gold, which is red *and* green against little
  blue, so the red detector barely registers it.
* **`spec: _spec`.** Different mod, different suffix.
* **A midtone gamma.** This is the general lesson. Ebony's median luminance is
  0.114; stretching the percentiles leaves it at 0.136, and the contrast curve
  then crushes that to **0.019** - a black helmet with gold on it, which is what
  two attempts produced before the number was measured rather than guessed. One
  gamma puts the object's median at mid grey, and any piece however dark its own
  paint now arrives where the palette expects it.

**Cost of overriding that texture, measured rather than assumed:** the ebony
closed helm exists in exactly **three places** in the game - the Urshilaku
burial and two Vivec vaults - plus a test crate and one scripted NPC. So the
five ebony helms in the world become Zenaric silver, and one of them is the
player's.

## The closed helm was tried and dropped

Faig picked the Ebony Closed Helm shape, asked for a Pragmata-like paint job on
it, and after four rounds called it off: **wind it down and put the ebony helm
back the way it was.** The helmet is the horned Face of Terror with its gold
removed, which he had already approved.

Our override of `tx_a_ebony_helmet` is gone, so every ebony closed helm in the
game is vanilla again. `paint_helm.py` is deleted with it.

What the rounds established, since the next painted piece will hit the same
walls:

* **A texture cannot say which way a helmet faces.** `uv_calibrate.py` answers
  it by measurement - eight named colour bands and three rules, worn and read
  off in one look. That worked first time and is kept.
* **This mesh's unwrap folds and overlaps.** Several parts of the shell share
  the same pixels, so anything drawn once can appear two or three times: two eye
  slits came out as four. A continuous band is immune; discrete marks are not.
* **`uvmap.py` gives an exact per-pixel map** - vertices, UVs and triangles out
  of the NIF, rasterised - but it cannot rescue an unwrap that overlaps: the
  azimuth map comes out a patchwork whichever surface you let win. It is kept
  because reading and rasterising a mesh is generally useful and it validates
  its own parse.
* **Contrast has to sit close to the plate.** Trim at 0.78 against a 0.50 plate
  read as black-and-white stripes on screen. That fix stayed in and helps the
  whole suit.
* **Matching a statistic is not matching a look.** Generated veining tuned to
  the cuirass's high-pass energy came out as even crackle glaze; the cuirass has
  clean stretches and veined ones. The number was a proxy, and it was not the
  point.

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

## The helmet built from a downloaded model

The one piece here whose geometry is not the game's own. `tools/build/` is
gitignored, so the command that produces it is recorded here or it is lost:

    python tools/scripts/glb.py <model.glb> --extract helmet --out helmet.obj
    python tools/scripts/nif_write.py helmet.obj         --donor meshes/a/a_ebony_helmet.nif         --out tools/build/armour-momw/Meshes/a/a_ebony_helmet.nif         --texture zenar_helm.dds --scale 1.55

and the texture through the ordinary converter, `plate_from="diffuse"`,
`trim="warm"`, gold off, grain 1.0, written to `Textures/zenar_helm.dds`.

**1.55** is where the size landed after two looks: a bounding-box fit is
conservative when a mesh carries spikes, so the first build was a third too
small and the second slightly so.

**No axis swap.** Morrowind bodyparts are Y-up with +Z forward, the same as
glTF - measured on the ebony helm, and confirmed on screen. Swapping is a
ninety-degree roll about the ear-to-ear axis and looks like a helmet nodding at
the floor.

The mesh sits at the ebony closed helm's own path inside our data directory, so
no record is touched and equipping that item shows it. The ebony helm exists in
three places in the game plus a test crate and one scripted NPC. Deleting two
files undoes all of it.

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
