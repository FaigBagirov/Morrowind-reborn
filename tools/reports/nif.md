# Can a script change a mesh? Measured, 2026-08-30

Faig asked why the project refuses to touch geometry, and whether that was
inability or policy. The honest answer needed a measurement, because the
justification in the documents had never been tested.

## What the documents claimed

*Canon* Part 9, under **Do not touch**:

> **NIF generation.** Binary format. The engine validates models on load and
> rejects machine-assembled files. Hand-edit in NifSkope or not at all.

`CLAUDE.md` carries the rule that follows from it: *Do not generate or edit NIF
files.* The rule was obeyed throughout, and the claim behind it was repeated to
Faig as fact. It had never been checked by anyone on this project.

## The instrument

OpenMW ships its own validator, `niftest.exe`, whose stated purpose is exactly
this question:

    Ensure that OpenMW can use the provided NIF, KF, BTO/BTR, RDT, PSA,
    BGEM/BGSM and BSA/BA2 files

So no game run is needed and no judgement is involved: the engine's own reader
either accepts the file or does not.

## Three runs

The subject is `meshes/a/a_ebony_helmet.nif`, extracted from `Morrowind.bsa` -
117 vertices, 230 triangles, 5,761 bytes. Everything below was written into the
scratch directory; **no game folder was touched**.

| | File | Result |
| --- | --- | --- |
| 1 | the original, as a control | accepted, exit 0 |
| 2 | every vertex scaled by 1.25, written by script | **accepted, exit 0** |
| 3 | a real deformation - a brow ridge raised at eye height, the crown tapered - 79 of 117 vertices moved, mean shift 0.46, max 1.82 | **accepted, exit 0** |

## What that settles, and what it does not

**Settled: the claim as written is false.** OpenMW's own validator accepts a NIF
whose geometry a script computed and wrote. It does not reject it, and it does
not care that no human touched it.

**Not settled, and not to be claimed:**

* A NIF *assembled from nothing* - new vertex and triangle counts, blocks built
  rather than patched - was not tested. Doing it needs the rest of the
  `NiTriShapeData` field layout decoded, and that decoding was stopped rather
  than guessed at: the bounding-sphere fields did not fall where any of three
  candidate layouts put them.
* Whether the reshaped helm *looks* right, or animates and collides correctly,
  was not tested. `niftest` reads a file; it does not wear it.

## So why still not do it

The rule stands, and its real justification is different from the one in the
documents:

1. **Good geometry is sculpting, not scripting.** A formula can move vertices;
   it cannot judge a silhouette. Nothing in this session's texture work would
   have gone better as geometry - the panel layout that got cut is exactly what
   procedural geometry produces, and worse.
2. **A bad mesh is not undoable the way a bad texture is.** Every texture here
   is removed by deleting one `data=` line. A mesh sits under animation and
   collision, and its failures show up as clipping, floating weapons and
   characters stuck in walls - far from the change that caused them.
3. **The two honest routes to a new shape are unchanged.** An existing mesh from
   another mod, with the plugin repointing `male_bodypart` so the record keeps
   its name and stats; or hand-modelling in Blender or NifSkope.

## The correction owed

*Canon* Part 9's sentence is now marked as measured-and-wrong rather than left
standing. The rule it justified is kept - on the grounds above, which are about
craft and blast radius rather than about the file format - and relaxing it is
Faig's call, not a decision to be taken quietly because a validator said yes.
