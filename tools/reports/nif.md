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

## Then the harder one: a file built rather than patched

The first three runs left assembly untested, and the report said so. Faig said
try, so it was tried, and it works.

**The layout was not guessed.** It was established by parsing the ebony helm's
`NiTriShapeData` block into arrays and rebuilding the file from them until all
**5,761 bytes came back identical**. Only then was the geometry changed.

    ushort numVertices        uint32 flag      float3 * n vertices
    uint32 flag               float3 * n normals
    float3 centre             float radius
    uint32 hasVertexColours   ushort numUVSets    uint32 flag
    float2 * n texture coordinates
    ushort numTriangles       uint32 numTrianglePoints
    ushort3 * m triangles

Three words in there read as neither 0 nor 1 and their meaning is **not known**.
They are copied from the donor rather than invented, which is honest and works.

| | File | Result |
| --- | --- | --- |
| 4 | the helm rebuilt from its own parsed arrays | **5,761 of 5,761 bytes identical** |
| 5 | a Sketchfab helmet, 3,269 vertices and 5,292 triangles, in a 117-vertex donor - 136,997 bytes against 5,761 | **accepted, exit 0** |

Blocks in this format refer to each other by index and carry no length field, so
a block that changes size breaks nothing after it. That is why a donor works and
why nothing had to be written from absolute zero.

`tools/scripts/nif_write.py` does it: OBJ in, donor named, NIF out, with the
axis swap and a uniform fit into the donor's own bounding box.

## A bug of mine that this uncovered

The four extra bytes before the vertex array are why `uvmap.py` had been reading
every mesh **four bytes short**. A float array read at the wrong offset is still
a float array, so nothing complained; the vertices simply came back shifted
against their own UVs.

That is what made this helm's azimuth map look like a patchwork, and I concluded
from it that the unwrap overlapped so badly it could not be painted on. With the
parse corrected the height map is a clean gradient and the azimuth map is smooth
almost everywhere. **Some overlap is real** - a few rectangular islands remain -
but the mess was mostly mine.

The parser now verifies itself against something no wrong offset can satisfy:
the file states its own bounding sphere, and the stated radius has to equal the
distance to the furthest vertex from the stated centre. On the ebony helm both
are 13.0252.

## What that settles, and what it does not

**Settled: the claim as written is false.** OpenMW's own validator accepts a NIF
whose geometry a script computed and wrote. It does not reject it, and it does
not care that no human touched it.

**Not settled, and not to be claimed:**

* Whether the built helm *looks* right, sits on the head, faces forward or
  clips was not tested. `niftest` reads a file; it does not wear one.
* Rigging. Morrowind dresses a body from separate rigid parts, so a helmet needs
  none - anything spanning a joint would, and that is untried.
* Collision. The donor's is carried through unexamined.
* A file built with **no donor at all** is still untested. Nothing needs it: the
  donor supplies the node, the material and the texture reference, all of which
  a new piece wants anyway.

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
