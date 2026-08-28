# MOMW `graphics-overhaul` compatibility — the mechanical answer

Run: `python tools/scripts/momw_compat.py`, 2026-08-28, against
`D:\Games\OpenMWMods\graphics-overhaul` version **8.5.0** — 694 plugin files,
~2 GB. Per-record detail in `momw-compat.csv`.

Method: intersect the record IDs our mod would edit with the record IDs every
plugin in the list edits. Plugins are read straight out of the binary, because
converting 2 GB through `tes3conv` is not practical; the reader is validated
against `tes3conv` on Morrowind.esm and matches on every record type, and
`--selfcheck` re-runs that comparison.

## The short answer

**The Lua half is clear. The plugin half collides with exactly two mods that
matter, and the list already ships the tool that resolves it.**

| Route | Records we touch | Colliding plugins | Verdict |
| --- | --- | --- | --- |
| Lua load context | 251 | 4 (all BOOK) | **no conflict, by construction** |
| Plugin via `tes3conv` | 497 (325 after our own dialogue policy) | 10, two of them real | **conflict, resolvable** |

## Why the Lua half cannot conflict

Load-context edits run after every content file has loaded, mutate one field of
a record and leave the rest alone, and read the value they are substituting
into. Four plugins touch books we also touch —
`book-jackets.esp` (82), `delta-merged.omwaddon` (74),
`Beautiful cities of Morrowind.ESP` (1), `RPNR_Library.ESP` (1) — and every one
of those is changing a book's *icon and mesh*, not its text. Our rule lands on
top of whatever text is in memory at that point, so if a mod had changed a
book's text, we would substitute into the modded text rather than over it.

There is also nothing to collide *with*: **not one Lua file in the entire list
writes `openmw.content`.** The list is 24 `.omwscripts` files and none of them
is in the record-editing business.

## Where it does collide

Two mods account for 95 of the 100 colliding records.

**`PatchesFixesandConsistency/PatchforPurists/Patch for Purists.esm` — 83
records: 80 INFO, 3 CREA.** Under our own dialogue policy — only
uniquely-filtered INFO, never greetings, never journals — that drops to **27**.
The three creatures are `daedroth`, `daedroth_az`, `daedroth_baladas`. PfP is a
core, always-active mod in every MOMW list, and it exists to fix typos in
exactly the dialogue we are rewriting.

**`Armor/DaedricLordArmorMorrowindEdition/DaedricArmor.esp` — 12 records: 11
ARMO, 1 WEAP.** All of them in the strict set, and they are precisely the
records Tier A renames: `daedric_cuirass`, `daedric_boots`,
`daedric_gauntlet_left/right`, `daedric_greaves`, `daedric_pauldron_left/right`,
`daedric_fountain_helm`, `daedric_terrifying_helm`, the two `_htab` variants,
and `daedric dai-katana`. This mod's whole purpose is to change how that armour
looks.

The remaining eight are single records: `daedric_special` in
`FM - Unique Items` and its PfP patch, one CREA in `Morrowind Anti-Cheese`,
and four INFO records in BCOM patches (`MasterIndexRedux` twice,
`Illuminated Order Improved`, `KS_Julan_Ashlander Companion` — the last falls
outside our dialogue policy anyway). Several sit under `Patches/` and
`Optional/` folders, so whether they are active depends on the list's install
config, which is not in this directory.

## Why a collision is not a warning but a silent loss

A Morrowind plugin overrides a record **whole**, not field by field. If our
plugin renames `daedric_cuirass` and `DaedricArmor.esp` gives it a new mesh,
whichever loads later wins the entire record. Load ours after and the armour
reverts to vanilla-looking. Load ours before and the rename disappears. Nothing
reports this; the game just shows one of the two.

The same is true of the 27 INFO records: our plugin generated from the bare
masters would carry the masters' text, which means it would quietly undo Patch
for Purists' corrections in those records.

## The resolution, and it is already installed

`Tools/MOMWToolsPack/delta-merged.omwaddon` is in the list — 510 records, and
**no INFO records at all**. That is the output of Delta Plugin, which merges
plugin overrides field-wise instead of wholesale, and the list already depends
on it for its own conflicts.

So the plan for the plugin half is the one Architecture Part 12 route 2
describes, with the tooling requirement already satisfied:

1. **Generate our plugin from the effective record set, not from the bare
   masters** — masters plus the active plugins as the game sees them. This is
   what keeps Patch for Purists' fixes and lets our substitution apply on top
   of the corrected text.
2. **Add our plugin to the Delta Plugin merge and regenerate
   `delta-merged.omwaddon`.** Field-wise merge means the armour keeps its new
   mesh and its new name.
3. **Regenerate after any change to the mod list.** This is the standing cost
   of the hybrid route, and it is the reason Part 12 records it as a cost.

Twelve armour records and twenty-seven dialogue records are a small enough
surface that step 1 could also be done by hand if the pipeline is not ready —
but it must be done deliberately, because the failure mode is silent.

## What this does not answer

- **Which plugins are actually in the load order.** There is no `openmw.cfg`
  or list manifest in this directory, so every `.esp` present was analysed,
  including `Optional/` and `Patches/` variants that may not be installed. The
  numbers are an upper bound on the active set.
- **Landmass mods.** Tamriel Rebuilt and friends add records rather than
  override vanilla ones, and none of them appears in the collision list. If a
  landmass adds its own daedric equipment or its own dialogue about daedra,
  that is new content our rules have never seen — a scope question for later,
  not a conflict.
