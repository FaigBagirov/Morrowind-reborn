# Work Order 0 -- Load Context Writability Spike

**Summary of record:** Architecture **Part 12** is the canonical write-up of
this result and is marked `SETTLED, MEASURED`. This file is the working detail
behind it: how the targets were chosen, the verification card, and the
provenance of each observation. Where the two differ, Part 12 wins.

**Status:** RUN and ANSWERED, in both layers and on screen.
Log run 2026-08-21 (`logs/wo0-spike.txt`, `logs/openmw.log`). On-screen check
reported by the user in a later session whose log was not kept -- see the
provenance note in section 4.
**Engine:** OpenMW 0.51.0 (`resources/version`: `0.51.0`, commit `f4bec414`).
**Profile:** clean vanilla dev profile, three masters only.

---

## 1. The answer

Static analysis first, then the run, then the screen. **All three agree.**

### What static analysis said

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
assumed. It covers **books, GMST strings, spells, ingredients, potions, magic
effects and the other twelve record types listed above**. It does not cover
item names, creature names, or dialogue -- which is most of the rewrite surface
in the table in Part 12. Probes 5-8 measure how much of the naming table
survives inside that narrower boundary.

### What the run added

The run agreed with all of it and sharpened three points.

**Probe 4 failed harder than predicted.** The prediction allowed either
`WRITE_THREW` or `NO_API_SURFACE`. It is `NO_API_SURFACE`: in the load context
`openmw.core.dialogue` is **nil**, and the attempt dies at
`attempt to index field 'dialogue' (a nil value)`. There is no read-only
dialogue surface to argue with -- in that context there is no dialogue surface
at all. (`core.dialogue` *is* present in a GLOBAL script: Layer 2 read the
target INFO record and reported its original text. The package exists; it is
simply not exposed to the load context.)

**Runtime enumeration matched the stubs exactly.** `pairs(content)` returned
16 keys: the 15 sub-packages listed above, each with `.records`, plus `RANGE`,
which has none. The shipped stub is not stale and the docs are not lying.

**The obvious workaround is closed.** Probes 9-10 were added after the first
run to test the one remaining hope: `types.Armor.records` and
`types.Creature.records` are live in a GLOBAL script, and the docs call them
read-only, but a documented restriction is not always an enforced one. It is
enforced. Both writes fail with `sol: cannot write to a readonly property`.

Together with `tools/reports/ui-hook.md` -- no display-time hook for names or
tooltips exists in 0.51, the UI is C++/MyGUI and never routes those strings
through Lua -- that exhausts the Lua-side options. Item names, creature names
and dialogue have to be changed at the record level, in a real plugin.

### The split this forces

Counting keyword hits from `tools/reports/wo1-keyword-occurrences.csv`, one
hit per record-field. **Read these as an upper bound, not a count of records.**
`aedra` is a substring of `daedra`, so nearly every `aedra` row double-counts a
`daedra` one -- *Shared World Canon* Part 10 puts the real Aedra total at about
twenty lines game-wide. The routing split below is still correct about *which
side of the line* each record type falls on, which is what it is for.

| Route | Hits | Contents |
| --- | --- | --- |
| Load context, Lua, `mod/` | 369 | BOOK text 336, SPELL name 12, BOOK name 10, INGREDIENT name 6, MISCITEM name 5 |
| Real plugin, `tes3conv` (Part 3 Option A) | 1005 | INFO text 960, WEAPON name 23, ARMOR name 14, CREATURE name 6, CLASS description 1, CLOTHING name 1 |
| Frozen by policy, never touched | 43 | DIAL id 37, CELL name 6 |

Tier A (equipment and species renaming) and all of Tier C (hand-written
dialogue) sit on the plugin side. The load context keeps the books and the
small records. Architecture Part 3 has been updated to record this.

**Note one unmeasured assumption in that table:** BOOK *name* is placed on the
load-context side because it lives in `content.books.records`, the same
sub-package as BOOK text. The spike probed BOOK `text` only. It has not been
demonstrated that BOOK `name` is writable, and the user's on-screen report is
consistent with either answer, because the spike never wrote it.

---

## 2. Writability table

Filled in from `logs/wo0-spike.txt`. `write_ok` is the Layer 1 result,
`readback_ok` is Layer 2, `on screen` is the user's report. `Predicted` is what
the static analysis said; a mismatch would have meant the analysis was wrong.
**Nothing mismatched.**

Probes 1-4 are the fields the project needs and expected to fail. Probes 5-8
are sub-packages that **do** exist and appear in the naming table, so the same
run reports both what is broken and what survives. Probes 9-10 were added
after the first run and write from a GLOBAL script rather than the load
context.

| # | record_type | field | write_ok | readback_ok | on screen | Predicted | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ARMO | FNAM (`name`) | **false** | **false** | unchanged | `NO_API_SURFACE` | as predicted. No `content.armors`; `armors` absent from the binary entirely |
| 2 | CREA | FNAM (`name`) | **false** | **false** | unchanged | `NO_API_SURFACE` | as predicted. No `content.creatures`; the `creatures` string in the binary belongs to CreatureLevelledList |
| 3 | BOOK | `text` | **true** | **true** | **changed, but blank** | `WRITE_OK` | writable, and the change does reach the screen -- the vanilla text is gone. The page renders empty instead of showing the sentinel; see section 7 |
| 4 | INFO | response `text` | **false** | **false** | not checked | `WRITE_THREW` or `NO_API_SURFACE` | `NO_API_SURFACE`, the harder of the two. `core.dialogue` is nil in the load context, so there is nothing to write to |
| 5 | GMST | the value itself | **true** | **true** | changed | `WRITE_OK` | as predicted. Readback via `core.getGMST`, which load scripts cannot call -- the strongest of the eight |
| 6 | SPEL | `name` | **true** | **true** | **renamed** | `WRITE_OK` | as predicted, and confirmed on screen |
| 7 | INGR | `name` | **true** | **true** | **renamed** | `WRITE_OK` | as predicted, and confirmed on screen |
| 8 | MGEF | `name` | **true** | **true** | changed | `WRITE_OK` | as predicted. The `esmfallbacks.lua` ordering hazard did not bite in the log |
| 9 | ARMO | `name`, written from a GLOBAL script | **false** | n/a | n/a | (added after run 1) | `WRITE_THREW`: `sol: cannot write to a readonly property` |
| 10 | CREA | `name`, written from a GLOBAL script | **false** | n/a | n/a | (added after run 1) | `WRITE_THREW`: same message. `types.*.records` is enforced read-only |

Five of the eight fields are writable from the load context. The three the
project most needed -- ARMO name, CREA name, INFO text -- are not reachable at
all, and probes 9-10 confirm there is no way round via GLOBAL either. Every
field the user looked at on screen agreed with both log layers.

Result codes the script emits:

| Code | Meaning |
| --- | --- |
| `NO_API_SURFACE` | no sub-package to write through -- the field is unreachable, not merely protected |
| `RECORD_NOT_FOUND` | sub-package exists, record id did not resolve -- a targeting bug, tell me |
| `WRITE_THREW` | the engine actively rejected the write (loud failure -- the good kind) |
| `WRITE_OK` | write accepted and reads back correctly inside the load context |
| `WRITE_SILENTLY_REVERTED` | **the dangerous one.** Accepted, then discarded |

---

## 3. Why these eight targets

All eight exist in vanilla and all eight are in Seyda Neen.

| # | Type | Record ID | Vanilla value | Why this one |
| --- | --- | --- | --- | --- |
| 1 | ARMO | `newtscale_cuirass` | `Imperial Newtscale Cuirass` | physically placed in Seyda Neen, Arrille's Tradehouse -- confirmed by reading the CELL record |
| 2 | CREA | `mudcrab` | `Mudcrab` | the **only** creature in the Seyda Neen exterior cell -- confirmed by cross-referencing every ref id in that cell against every CREA id |
| 3 | BOOK | `bk_BriefHistoryEmpire1` | `Brief History of the Empire v 1` | sits in Seyda Neen, Census and Excise Office -- the room the game starts in |
| 4 | INFO | `1248319992938512979` | Arrille's "little advice" reply | `filterActorId = arrille`, **no select rule at all**, and it precedes the other Arrille entry in the topic, so it always fires |
| 5 | GMST | `sMagicEffects` | `Magic Effects` | the header of the tooltip that also shows probes 6 and 8 |
| 6 | SPEL | `absorb fatigue` | `Absorb Fatigue` | sold by Arrille in Seyda Neen; its single effect is probe 8 |
| 7 | INGR | `food_kwama_egg_02` | `Large Kwama Egg` | sits in Seyda Neen, Census and Excise Office, beside the book |
| 8 | MGEF | `absorbfatigue` | `Absorb Fatigue` | the only effect on probe 6, so both appear in one tooltip |

Probes 5, 6 and 8 were chosen to converge on a single screen. Open the Magic
menu and hover **Absorb Fatigue**: the tooltip's section header is probe 5, the
spell name is probe 6, and the effect line is probe 8. One tooltip, three
answers.

Every id above was read out of `tools/input/Morrowind.esm` with `esmtool`, not
recalled from memory. `tools/input/` was opened read-only and not modified.

A note on target 4: the topic is reachable without any quest setup because
Arrille's own greeting contains the words "little advice", which hyperlinks the
topic the moment you first speak to him.

---

## 4. VERIFICATION CARD -- and its result

### Result, reported by the user

Five of the eight checks were done and reported. **Every one agrees with the
two log layers.** The card itself is kept below, unchanged, because the spike
is still in `mod/` and the three unreported checks can still be done.

| Check | What the logs said | What the user saw | Agrees |
| --- | --- | --- | --- |
| 1 ARMO name | write never happened | cuirass **not** renamed | yes |
| 2 CREA name | write never happened | mudcrab **not** renamed | yes |
| 3 BOOK text | written, sentinel read back | page **not** the vanilla text -- it came up **blank** | yes, with a caveat -- section 7 |
| 4 INFO text | write never happened | not checked | -- |
| 5 GMST string | written, sentinel read back | changed -- see the tooltip note | yes |
| 6 SPEL name | written, sentinel read back | spell **renamed** | yes |
| 7 INGR name | written, sentinel read back | egg **renamed** | yes |
| 8 MGEF name | written, sentinel read back | changed -- see the tooltip note | yes |

**On "the book was not renamed":** the user also reported that the book's name
in the inventory was unchanged. That is correct and expected -- **probe 3
wrote the `text` field, never `name`.** No sentinel was ever placed in the
book's name, so an unchanged name is the only possible outcome and is not a
failure. BOOK `name` remains unprobed; see the note at the end of section 1.

**Provenance, and it differs in strength between rows.**

Checks 1, 2, 3, 6 and 7 were reported by the user from what they saw: the
cuirass and the mudcrab unchanged, the spell and the egg renamed, the book
blank.

Checks 5 and 8 rest on a **recollection, not a read-out.** Asked about them
later, the user recalled that on the one spell they looked at, *every* line of
the tooltip had changed, but did not recall the exact strings. The tooltip for
`absorb fatigue` is exactly those three lines -- spell title (6), the section
header above the effects (5), the effect line under it (8) -- so "all of them
changed" means none of the three still read its vanilla value. That is
evidence against the failure mode that matters here, which would show as
*unchanged* text on screen despite a successful write. It is not the same as
having read `SPIKE_GMST_OK` off the screen.

Note that the `confirmed` markers previously in Architecture Part 12 for these
two rows were **not** written by the user. They were written by an earlier
Claude session and inherited into the document unchallenged.

The run that produced these observations is **not** in `logs/`.
`run-spike.bat` overwrites `logs/openmw.log` on each run and that copy was
never taken, so the archived log is still the 93-second run of 2026-08-21 that
produced the two log layers. If the checks are ever repeated, copy the log
before anything else.

### The card

Follow this blind. Run `run-spike.bat`, then do these eight checks in one
sitting. The console opens with the `~` key.

Checks 1-4 are the ones predicted to fail. Checks 5-8 are the positive half:
they say what the load context *can* still do. Checks 5, 6 and 8 all land in a
single tooltip, so the eight checks take about five screens, not eight.

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

This is the only one of checks 1-4 predicted to succeed. If exactly one of the
first four shows its sentinel, it should be this one.

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

### Checks 5, 6 and 8 -- one tooltip, three answers

Do this one first if you only have time for one thing. It is the positive
half of the answer.

Setup, in the console:

```
player->AddSpell "absorb fatigue"
```

(You can also buy this spell from Arrille, who is standing right there --
the console is just faster.)

Now open the **Magic** menu and hover the spell **Absorb Fatigue**. One
tooltip contains all three:

| Check | What it is in the tooltip | If the write worked | Expected instead |
| --- | --- | --- | --- |
| 6 -- SPEL name | the spell's title, at the top | `SPIKE_SPEL_OK` | `Absorb Fatigue` |
| 5 -- GMST string | the section header above the effect list | `SPIKE_GMST_OK` | `Magic Effects` |
| 8 -- MGEF name | the effect line under that header | `SPIKE_MGEF_OK` | `Absorb Fatigue` |

If check 8 shows `Absorb Fatigue` while the log says `write_ok=true` for probe
8, that is the `esmfallbacks.lua` ordering hazard, not a writability failure --
say so and I will look at it. The other two are unaffected by that.

---

### Check 7 -- INGR name

* **Record ID:** `food_kwama_egg_02`
* **Where:** Seyda Neen, Census and Excise Office -- the room the game starts
  in, same room as the book in check 3. Pick up the large egg.
* **Or by console:**
  ```
  player->AddItem "food_kwama_egg_02" 1
  ```
  then open Inventory and hover it.
* **If the write worked, the item is called:** `SPIKE_INGR_OK`
* **Expected instead:** `Large Kwama Egg`

---

### After the eight checks

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
reach the game data. It reads the same eight values through completely
different paths (`openmw.types`, `openmw.core.dialogue`, `openmw.core.magic`
and `core.getGMST`) from a GLOBAL script, which has no relationship to the load
context. Agreement between the layers is the only evidence that a write
actually landed.

The GMST readback is the strongest of the eight: `core.getGMST` is documented
as "Not available in load scripts", so it physically cannot be answered by
whatever the load context left behind in its own map.

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

All four of the new probes (5-8) are length-compliant -- each vanilla value is
at least as long as its 13-character sentinel, which is part of why these
specific records were chosen over shorter alternatives:

| Probe | Vanilla value | Length | Sentinel | Fits |
| --- | --- | --- | --- | --- |
| 5 GMST | `Magic Effects` | 13 | `SPIKE_GMST_OK` (13) | yes, exactly |
| 6 SPEL | `Absorb Fatigue` | 14 | `SPIKE_SPEL_OK` (13) | yes |
| 7 INGR | `Large Kwama Egg` | 15 | `SPIKE_INGR_OK` (13) | yes |
| 8 MGEF | `Absorb Fatigue` | 14 | `SPIKE_MGEF_OK` (13) | yes |

For probe 7 this ruled out `ingred_crab_meat_01` (`Crab Meat`, 9) and
`ingred_comberry_01` (`Comberry`, 8), which are in the same room.

---

## 7. What is settled, and the one thing that is not

The question this section used to hold -- whether a write the load context
accepts actually reaches game data -- is **answered, all the way to the
screen.** Every successful write read back from an unrelated GLOBAL context
through a different API path, and the three the user looked at on screen
matched. Nothing was silently reverted. The feared combination for BOOK,
`write_ok=true` with `readback_ok=false`, did not occur.

### The one anomaly: a written book renders blank

Probe 3 replaced the whole 5403-character `text` field of
`bk_BriefHistoryEmpire1` with the bare string `SPIKE_BOOK_OK`. The card
predicted the page would show that string. The user opened the book and the
page was **empty**.

What this does and does not mean:

* **It is not a writability failure.** The vanilla text is gone from the page.
  The write reached the render layer; only the vanilla text disappearing could
  produce that. BOOK text is writable end to end.
* **The cause of the blank is not established.** Vanilla book text opens with
  pseudo-HTML -- `<DIV ALIGN="CENTER"><FONT COLOR="000000" SIZE="3" FACE="Magic
  Cards">` -- and the sentinel carried none of it. Whether OpenMW's book text
  parser drops untagged content, or renders it in a colour invisible against
  the page, or something else, **I do not know and cannot determine from the
  web environment** -- it needs the engine source or a test on the Windows
  side. Do not guess it in the rules table.

**The consequence for the project is real regardless, and it is a rule:**
book text must be rewritten by **substituting inside the existing field**,
never by replacing the field wholesale. The markup is load-bearing. The WO2
transform does substring substitution by design, so it preserves the markup by
construction -- but this is now an explicit rule and the first test case for
the book emitter: rewrite one book, open it in game, confirm it still renders.

### Still outstanding

* Whether BOOK `name` is writable. Assumed yes, never probed -- the spike wrote
  `text` only. 10 keyword hits ride on it, and Part 12 now carries the same
  caveat.
* The blank-page cause above, if it is ever worth chasing. It is not a gate:
  the transform never replaces a whole text field.
