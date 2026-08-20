# Work Order 0 -- Load Context Writability Spike

**Status:** built, not yet run. Claude Code does not launch the game.
**Engine:** OpenMW 0.51.0 (`resources/version`: `0.51.0`, commit `f4bec414`).
**Profile:** clean vanilla dev profile, three masters only.

---

## 1. The answer, from static analysis

Three of the four fields the project needs **have no API surface at all** in
0.51. This is not a guess and not a prediction about behaviour -- it is the
absence of the sub-package that would have to exist for the write to be
expressible.

`openmw.content` is the only package available in the load context. In 0.51 it
exposes exactly these sub-packages:

```
activators  books   doors    enchantments  gameSettings  globals
ingredients lights  magicEffects  miscs   potions  probes
sounds      spells  statics
```

There is **no `armors`, no `weapons`, no `clothing`, no `creatures`, no `npcs`,
and no `dialogue`.**

Evidence, three independent sources agreeing:

| Source | What it shows |
| --- | --- |
| `resources/lua_api/openmw/content.lua` (shipped with 0.51) | the 15 sub-packages listed above, nothing else |
| docs for `openmw-0.51.0`, `openmw_content.html` | same 15 |
| `strings openmw.exe` | `armors` **does not occur anywhere in the binary** |

The two near-misses in the binary were run down and are both false leads:

* `creatures` -- a field of `ESM3_CreatureLevelledList` (it sits beside
  `chanceNone` and `calculateFromAllLevels`), not a content sub-package.
* `dialogue` -- the string `openmw_core_dialogue`, i.e. `core.dialogue`, which
  the API docs describe as **read-only** record access.

The `latest` (0.52-dev) docs add `classes, factions, levelledCreatures,
levelledItems, lockpicks, races, repairs`. Still no armor, creature, or
dialogue. The gap is not a 0.51 oversight that the next release closes.

### Consequence for Part 3

**Part 12's stated trigger condition is met: INFO text is not writable from the
load context.** Per Part 12, "if INFO text turns out to be read-only, the
architecture changes completely."

The load context is not a dead end, but it is much narrower than Part 3
assumed. It covers **books and GMST strings**. It does not cover item names,
creature names, or dialogue -- which is most of the rewrite surface in the
table in Part 12.

Run the spike before acting on this. The point of the run is to confirm the
static reading and, more importantly, to catch the one failure mode static
analysis cannot see: a write that is accepted and then silently discarded.

---

## 2. Writability table

`write_ok` and `readback_ok` are filled by the run. `Predicted` is what the
static analysis above says you should see; a mismatch is the interesting
result and means the analysis was wrong somewhere.

| record_type | field | write_ok | readback_ok | Predicted | notes |
| --- | --- | --- | --- | --- | --- |
| ARMO | FNAM (`name`) | | | `NO_API_SURFACE` | no `content.armors`; `armors` absent from the binary entirely |
| CREA | FNAM (`name`) | | | `NO_API_SURFACE` | no `content.creatures`; the `creatures` string in the binary belongs to CreatureLevelledList |
| BOOK | `text` | | | `WRITE_OK` | `content.books.records` exists and is documented mutable |
| INFO | response `text` | | | `WRITE_THREW` or `NO_API_SURFACE` | no content sub-package; only `core.dialogue`, documented read-only |

Fill each row from `logs/wo0-spike.txt`, which `run-spike.bat` extracts for
you. Layer 1 lines give `write_ok=`, Layer 2 lines give `readback_ok=`.

Result codes the script emits:

| Code | Meaning |
| --- | --- |
| `NO_API_SURFACE` | no sub-package to write through -- the field is unreachable, not merely protected |
| `RECORD_NOT_FOUND` | sub-package exists, record id did not resolve -- a targeting bug, tell me |
| `WRITE_THREW` | the engine actively rejected the write (loud failure -- the good kind) |
| `WRITE_OK` | write accepted and reads back correctly inside the load context |
| `WRITE_SILENTLY_REVERTED` | **the dangerous one.** Accepted, then discarded |

---

## 3. Why these four targets

All four exist in vanilla and all four are in Seyda Neen.

| # | Type | Record ID | Vanilla value | Why this one |
| --- | --- | --- | --- | --- |
| 1 | ARMO | `newtscale_cuirass` | `Imperial Newtscale Cuirass` | physically placed in Seyda Neen, Arrille's Tradehouse -- confirmed by reading the CELL record |
| 2 | CREA | `mudcrab` | `Mudcrab` | the **only** creature in the Seyda Neen exterior cell -- confirmed by cross-referencing every ref id in that cell against every CREA id |
| 3 | BOOK | `bk_BriefHistoryEmpire1` | `Brief History of the Empire v 1` | sits in Seyda Neen, Census and Excise Office -- the room the game starts in |
| 4 | INFO | `1248319992938512979` | Arrille's "little advice" reply | `filterActorId = arrille`, **no select rule at all**, and it precedes the other Arrille entry in the topic, so it always fires |

Every id above was read out of `tools/input/Morrowind.esm` with `esmtool`, not
recalled from memory. `tools/input/` was opened read-only and not modified.

A note on target 4: the topic is reachable without any quest setup because
Arrille's own greeting contains the words "little advice", which hyperlinks the
topic the moment you first speak to him.

---

## 4. VERIFICATION CARD

Follow this blind. Run `run-spike.bat`, then do these four checks in one
sitting. The console opens with the `~` key.

Two possible outcomes per check, and **both are results** -- write down which
one you see.

---

### Check 1 -- ARMO name

* **Record ID:** `newtscale_cuirass`
* **Where:** Seyda Neen, Arrille's Tradehouse -- it is placed in the shop.
* **Or by console:**
  ```
  player->AddItem "newtscale_cuirass" 1
  ```
  then open your Inventory and look at the cuirass.
* **If the write worked, the item is called:** `SPIKE_ARMO_OK`
* **Expected instead:** `Imperial Newtscale Cuirass`

---

### Check 2 -- CREA name

* **Record ID:** `mudcrab`
* **Where:** the shoreline in Seyda Neen, outdoors. Mudcrabs are the only
  creature in that cell, so any creature you see on the shore is one.
  Put your crosshair on it -- the name appears above the health bar.
* **Or by console:** `player->PlaceAtMe "mudcrab" 1 128 1`
  (spawns one next to you; if this syntax is rejected, just walk to the shore --
  the shoreline route is the reliable one)
* **If the write worked, the crosshair reads:** `SPIKE_CREA_OK`
* **Expected instead:** `Mudcrab`

---

### Check 3 -- BOOK text

* **Record ID:** `bk_BriefHistoryEmpire1`
* **Where:** Seyda Neen, Census and Excise Office -- the building you start the
  game in. The book is on a shelf there.
* **Or by console:**
  ```
  player->AddItem "bk_BriefHistoryEmpire1" 1
  ```
  then open Inventory and read it.
* **If the write worked, the open page shows only:** `SPIKE_BOOK_OK`
* **Expected instead:** the page begins
  `A Brief History of the Empire / Part One / by Stronach k'Thojj III`

This is the one predicted to succeed. If exactly one of the four checks shows
its sentinel, it should be this one.

---

### Check 4 -- INFO response text

* **Record ID:** `1248319992938512979` (topic `little advice`, actor `arrille`)
* **Where:** Seyda Neen, Arrille's Tradehouse. Talk to **Arrille**, the
  publican behind the counter. In his greeting the words **little advice**
  are a hyperlink -- click it. (It is also in the topic list on the right.)
* **If the write worked, his whole reply is:** `SPIKE_INFO_OK`
* **Expected instead:** `If you want to live to a ripe old age, buy a weapon
  and as much armor as you can wear and still run from trouble...`

---

### After the four checks

Quit the game. **Do not save** -- the spike needs nothing saved, and not saving
keeps save files clean of the temporary global script.

`run-spike.bat` then writes:

* `logs/openmw.log` -- the full log
* `logs/wo0-spike.txt` -- just the `[WO0]` lines

Bring me `logs/wo0-spike.txt`. If it is empty, the script did not load: check
`logs/openmw.log` for a line reading
`Loading content file wo0-spike.omwscripts`.

---

## 5. What was built

```
mod/wo0-spike.omwscripts        registers both scripts
mod/scripts/wo0/load.lua        Layer 1 - writes, from the LOAD context
mod/scripts/wo0/readback.lua    Layer 2 - reads back, from a GLOBAL context
run-spike.bat                   launch, wait, collect the log
tools/reports/wo0.md            this file
```

Layer 2 exists because a write can be accepted by the load context and never
reach the game data. It reads the same four values through a completely
different path (`openmw.types` and `openmw.core.dialogue`) from a GLOBAL
script, which has no relationship to the load context. Agreement between the
layers is the only evidence that a write actually landed.

The script never calls an API without probing for it first. Each write target
is looked up against a list of candidate sub-package names, and every access is
wrapped in `pcall`, so a missing surface is *reported* rather than throwing and
aborting the remaining tests. Record ids are tried in both their literal and
lowercased forms, since the ESM and the engine store differ in case.

### Verification performed before handing this over

* Both Lua files were parsed by **OpenMW's own `lua51.dll`** (LuaJIT 2.1) --
  syntax valid.
* Both were then **executed** against mocked 0.51 API surfaces, exercising
  every branch: `NO_API_SURFACE`, `RECORD_NOT_FOUND`, `WRITE_THREW`,
  `WRITE_OK`, the case-fallback lookup, and both Layer 2 outcomes. No handler
  threw.
* The dev profile was confirmed to already run a LOAD-context script:
  `logs`-side evidence is `#23 LOAD : scripts/omw/esmfallbacks.lua` in the
  existing `dev/openmw.log`, so the context is live in this exact profile.
* `D:\Work\Morrowind reborn\mod` is already a registered data directory in the
  dev profile -- confirmed in `dev/openmw.cfg` and in the existing log.

---

## 6. Reversibility and rule compliance

* **Delete the contents of `mod/` and the spike is gone.** Nothing else
  references it.
* **No file outside the project was modified.** The spike is registered with
  `--content` on the command line, not by editing `dev/openmw.cfg`. The OpenMW
  docs state that for multi-value settings, command line values are appended
  after config file values, so the three masters still load first.
* `tools/input/` was read only, never written. Masters untouched.
* No record IDs, RefIds, script bodies, or script variable names are touched.
* No NIF files generated or edited.
* All files are plain ASCII.
* Nothing is written to save games. The GLOBAL readback script implements no
  `onSave` handler and stores no data.

### Two knowing deviations, both spike-only

1. **`SPIKE_CREA_OK` (13 chars) is longer than `Mudcrab` (7 chars)**, against
   the "replacement must not be longer" rule. That rule exists for byte-level
   in-place ESM patching; the Lua context has no such constraint, and this
   spike exists precisely to decide whether that architecture is used at all.
   Mudcrab was chosen anyway because it is the only creature in Seyda Neen, and
   reachability was the stated priority. The other three replacements are all
   shorter than what they replace.
2. **The INFO sentinel drops the topic keyword**, against the
   keyword-preservation rule. A sentinel that contained real topic words would
   defeat the "obviously fake, never plausible-looking" requirement.

Both are reverted by deleting `mod/` contents and neither reaches any
permanent file.

---

## 7. Open question I could not settle without running

Whether a write the load context accepts actually reaches game data. Static
analysis cannot see `WRITE_SILENTLY_REVERTED`; only Layer 2 plus your eyes can.
For BOOK specifically, watch for Layer 1 saying `write_ok=true` while Layer 2
says `readback_ok=false` -- that combination would mean the load context is
unusable even for the one record type it appears to support.
