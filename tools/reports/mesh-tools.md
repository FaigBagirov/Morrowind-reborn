# Making meshes for Morrowind: what the community says

Web research by the first fork on 2026-08-30, when Faig asked whether
instructions exist for adapting 3D models to Morrowind. It lived only in that
session's conversation; this is it written down. **None of it is measured
here** - it is what the sources say, and each point should be checked the way
everything else in this project is before it is relied on.

## Two tool stacks, and the versions matter

**Current.** The [Morrowind Blender Plugin](https://blender-morrowind.readthedocs.io/)
(Greatness7, [`io_scene_mw`](https://github.com/Greatness7/io_scene_mw)),
Blender 3.1 or newer, `File > Export > Morrowind (.nif)`. Beta, maintained.
Not installed here.

**Legacy**, still what [UESP](https://en.uesp.net/wiki/Morrowind_Mod:Creating_Morrowind_Meshes_Using_New_Versions_of_Blender)
describes: Blender 2.49b with NifScripts, Python 2.6.6 and PyFFI 2.1.11, and a
second, modern Blender beside it, meshes moved between the two by append.

**NifSkope version trap** - the same thing this project measured on its own
(`.nif` is a family, not a format). Recent NifSkope opens a Morrowind file with
"Unsupported 'Startup Version' 4.0.0.2, reverting to 20.0.0.5", and a mesh it
saves shows in game as an error marker. Use 1.0.9 or 1.1.3. Recent versions
also do not display skinned meshes.

## The donor + OBJ route is ours

[UESP gives it as the main route](https://en.uesp.net/wiki/Morrowind_Mod:Converting_models_from_Oblivion_mods_using_Nifskope)
for bringing models over from other games: export to `.obj`, open the simplest
Morrowind `.nif`, import the `.obj` into it, delete the branches you do not
need. That is what `tools/scripts/nif_write.py` does by script. Their tool is
NifSkope 1.1.0-rc6; newer versions break OBJ import.

One warning worth a check in `nif_info.py`: after import, `NiTriShapeData`
sometimes drops its **`Has UV`** flag to "no" on its own.

## Skinning

From [Pherim's notes](https://www.nexusmods.com/morrowind/mods/57478) to his
skinning skeleton:

- The rig is the `NiNode` branch that starts at `Bip01`. The Morrowind humanoid
  is simple: no toe bones, two fingers and a thumb on each hand.
- **At most 4 weights per vertex, and he keeps to 3**: with four he saw gaps
  between parts even on a welded mesh.
- **Vertex group names must equal the rig's bone names.** Extra groups - an
  importer's `leaf bones`, say - are likely to cause errors.
- Only groups that carry weights reach `NiSkinInstance`. Weights are
  normalised on export, so only their proportions matter.
- A crooked rest pose breaks import; it twisted his bracers.

**Weight transfer.** With a correctly skinned body at hand, weights can be
poured onto new armour with Blender's **Data Transfer** modifier (Vertex Data >
Vertex Groups, mapping `Nearest Face Interpolated`), then **applied by hand** -
left unapplied, his mesh bound to a single bone. This is the named cure for the
chest problem recorded in `CLAUDE.md`: every cuirass in the game is skinned, and
a script cannot produce the weights.

**And the relief.** A part that does not deform - a metal pauldron, a helmet -
may simply be parented to one bone with no skinning at all. That is an accepted
technique, not a workaround, and it is what the donor route already does for
rigid pieces.

## What follows for this project

1. Helmet, pauldrons, bracers: the scripted donor route is the right one.
2. The cuirass and anything else that bends is Blender work - weight transfer
   from a skinned vanilla body.
3. Before a file reaches the game: at most 3 weights per vertex, group names
   equal to bone names, `Has UV` set. `nif_info.py` checks none of these yet.

Daniel Bui has a tutorial series on converting Morrowind armour and on how the
engine assembles separate parts, but it is on
[Patreon](https://www.patreon.com/posts/morrowind-armor-19312853) and returned
403. Also: [Tamriel Rebuilt modelling resources](https://www.tamriel-rebuilt.org/content/modelling-resources).
