# Morrowind Sci-Fi Conversion

Rewrite Morrowind's lore, magic system and casting visuals into a nanite /
alien-technology setting without breaking the game.

Docs, three files, all of them authoritative over anything written here:

- `docs/Morrowind_SciFi_Conversion_Architecture.md` - method. **Part 12 is the
  measured writability result and everything else is subordinate to it.**
- `docs/Morrowind_SciFi_Conversion_Canon.md` - Vvardenfell only.
- `docs/Shared_World_Canon.md` - everything true of the world regardless of
  game: premise, the Schism, the Rename Test, the naming table. **Shared with
  the Skyrim project. It is edited here and re-uploaded there - never the
  other way round.**

**Read "State of play" below first**, then the docs, before proposing changes.

Game: OpenMW 0.51.0, pinned (`resources/version` commit `f4bec414`).
Clean vanilla dev profile, three masters only.
Mod files go in `mod/`. Scripts and reports go in `tools/`.

---

# State of play

This is the handover note. Read it instead of asking the user where we
stopped. **Every change set ends by updating this section.**

## Work orders

| # | What | Status |
| --- | --- | --- |
| WO0 | Load context writability (Architecture Part 12) | **DONE, `SETTLED, MEASURED`.** Ten probes, two log layers, confirmed on screen. Canonical write-up is Architecture Part 12; working detail in `tools/reports/wo0.md` |
| WO1 | Dialogue survey (Architecture Part 13) | **DONE, `SETTLED, CROSS-CHECKED`.** Re-run 2026-08-28 with all five defects fixed and checked against `esmtool`. Canonical write-up is Canon Part 7; working detail in `tools/reports/wo1.md` |
| WO2 | Rules table + transform script | **DONE, `SETTLED, MEASURED`.** All three gates pass, confirmed on screen 2026-08-28. Canonical write-up is Architecture Part 14; `run-mod.bat` re-runs the game check |

## WO0 - the answer, and why it is the constraint on everything

Log run 2026-08-21, 93 seconds; raw output `logs/wo0-spike.txt`, full log
`logs/openmw.log`. Layer 1 = writes attempted from the LOAD context. Layer 2 =
independent readback from a GLOBAL script, which cannot see a local copy the
load context left behind. The user did the on-screen checks in a later
session. **All three agree.**

The on-screen run's log is **not** in `logs/` - `run-spike.bat` overwrites
`logs/openmw.log` each run and that copy was never taken, so the archived log
is still the 2026-08-21 one. The screen results below came from the user in
conversation. If the checks are ever repeated, copy the log first.

At runtime `openmw.content` exposes 16 keys: `RANGE`, which has no records,
and 15 sub-packages that do -

    activators  books   doors    enchantments  gameSettings  globals
    ingredients lights  magicEffects  miscs   potions  probes
    sounds      spells  statics

| # | Record | Field | Layer 1 | Layer 2 | Verdict |
| --- | --- | --- | --- | --- | --- |
| 3 | BOOK | text | WRITE_OK | sentinel present | **writable** (see the book caveat below) |
| 5 | GMST | the value | WRITE_OK | sentinel present | **writable** |
| 6 | SPEL | name | WRITE_OK | sentinel present | **writable** |
| 7 | INGR | name | WRITE_OK | sentinel present | **writable** |
| 8 | MGEF | name | WRITE_OK | sentinel present | **writable** |
| 1 | ARMO | name | NO_API_SURFACE | original value | **unreachable** |
| 2 | CREA | name | NO_API_SURFACE | original value | **unreachable** |
| 4 | INFO | response text | NO_API_SURFACE | original value | **unreachable** |

On screen the user saw the spell and the egg **renamed**, the cuirass and the
mudcrab **not** renamed, and the book blank. GMST and MGEF rest on a weaker
footing: the user recalls that every line of the one spell tooltip they looked
at had changed, but not the exact strings. Those lines are the spell name, the
GMST header and the effect name, so nothing there still read its vanilla value
- enough to rule out the failure mode, short of a read-out. The `confirmed`
that stood in Architecture Part 12 for those two rows was written by a Claude
session, not observed; it has been corrected.

### The book caveat - a rule falls out of it

The user opened the book whose `text` the spike overwrote and the page came up
**blank**, not showing the sentinel.

This is **not** a writability failure: the vanilla 5403-character text is gone
from the page, so the write reached the render layer. What went with it was
the vanilla pseudo-HTML markup - `<DIV ALIGN="CENTER"><FONT COLOR="000000"
SIZE="3" FACE="Magic Cards">` - which the bare sentinel did not carry. Why that
renders as nothing rather than as unstyled text is **not established**, and it
cannot be determined from the web environment. Do not guess it.

**The rule that follows is in the Rules section: substitute inside a book's
text field, never replace the field.** The WO2 transform does substring
substitution by design, so it satisfies this by construction - but the first
book it rewrites must be opened in game to confirm the page still renders.

The user also reported the book's *name* unchanged. That is expected, not a
failure: **probe 3 wrote `text`, never `name`.** BOOK `name` remains unprobed,
which matters because the routing table below assumes it is writable.

Three findings that close the obvious workarounds:

- There is no `content.armors`, `content.creatures` or `content.dialogue`.
  `armors` does not occur anywhere in the 0.51 binary, and the 0.52-dev docs
  do not add it. In the load context `openmw.core.dialogue` is **nil** - the
  error is `attempt to index field 'dialogue' (a nil value)`, so this is not a
  rejected write, there is nothing to write to. (`core.dialogue` does exist in
  a GLOBAL script; Layer 2 read the target INFO record through it.)
- Probes 9-10 write to `types.Armor.records` / `types.Creature.records` from a
  GLOBAL script, where the docs call them read-only. It is enforced:
  `sol: cannot write to a readonly property`.
- There is no display-time hook for names or tooltips in 0.51. The UI is
  C++/MyGUI and never routes those strings through Lua, so the string cannot
  be intercepted at render time either. See `tools/reports/ui-hook.md`.

**Consequence.** Architecture Part 12 said: "if INFO text turns out to be
read-only, the architecture changes completely." That condition has fired.
Part 3's "pick the second one" no longer holds - the load context cannot carry
the rewrite, and a `tes3conv` plugin (Option A) is now mandatory, with every
load-order and save-contamination consequence Option A lists.

Where the line falls, counting **records** that carry a keyword, from the
corrected `tools/reports/wo1-keyword-occurrences.csv`. One row per
record-field, so a book with a keyword in both title and text is in two rows:

| Route | Records | Contents |
| --- | --- | --- |
| Load context, Lua, `mod/` | 253 | BOOK text 227, SPELL name 12, MISCITEM name 5, BOOK name 4, INGREDIENT name 3, GMST value 2 |
| Plugin via `tes3conv` | 496 | INFO text 455, WEAPON name 21, ARMOR name 14, CREATURE name 4, CLASS description 1, CLOTHING name 1 |
| Frozen by policy | 57 | SCRIPT text 32, DIAL id 19, CELL name 6 |

These are records, not the inflated occurrence counts the first pass reported -
the old table said 369 / 1005 / 43 and those numbers double-counted, mostly
through the phantom `aedra`. The shape of the conclusion is unchanged.

So Tier A (equipment and species renaming) and all of Tier C (hand-written
dialogue) are on the plugin side. The load context keeps the books and the
small records. One unmeasured assumption in that table: BOOK *name* sits on
the load-context side because it shares a sub-package with BOOK text. It was
never probed. 4 records ride on it.

### Outstanding on WO0 - one item left, not blocking

- **BOOK `name`: closed 2026-08-28, writable, confirmed on screen.** Probed by
  `mod/wo1-bookname.omwscripts`: written from the load context, read back from
  a GLOBAL script and from a PLAYER script in a live session, and seen renamed
  in the inventory. Nothing in Architecture Part 12's available column is an
  assumption any more.
- **Substring substitution in book text: closed the same run.** The probe
  rewrote the page-one heading in place, same length, markup untouched, and
  the page rendered normally - centered heading, Magic Cards face, pagination
  unchanged, rest of the text intact. The transform's method is measured on a
  real book.
- Why a book whose whole text field is replaced with unmarked-up text renders
  blank is still unexplained. Not a gate - the transform never replaces a
  whole field, and the substitution path is now known to work.

`mod/` can be emptied whenever you like; deleting its contents removes the
spike entirely.

## WO1 - the number, `SETTLED, CROSS-CHECKED`

`tools/scripts/wo1_survey.py`, re-run 2026-08-28. It is reproducible now: no
arguments, converts `tools/input/*.esm` into `tools/cache/` with `tes3conv` and
surveys the JSON, about twenty seconds end to end. `tools/cache/` is gitignored.

Canonical write-up is Canon Part 7; working detail, every cross-check and the
reconciliation with the first pass is `tools/reports/wo1.md`.

**The number Part 13 asks for, in three selections:**

| Selection | Actors | INFO | Words |
| --- | --- | --- | --- |
| Every actor-filtered line in the game | 1,111 | 16,225 | 473,221 |
| **Every line of an actor who says a keyword at least once** | **80** | **3,099** | **113,613** |
| Lines that actually carry a keyword | 80 | 208 | 10,645 |

Plan against the middle row: it is the reading load, and Tier C is "who knows",
not "who says daedra". The bottom row is the writing load. The old 11,502 was
the bottom row measured with two bugs in it, and it was called the answer.

Plus 64 name-field records for Tier A, 19 keyword topics holding 80 INFO, and
1,423 named cells of which 6 carry a keyword - all frozen.

All five defects listed in the previous handover are fixed, and the fix to the
`aedra` boundary is in. Two things worth carrying forward:

- **The cross-check earned its keep.** esmtool disagreed with the survey on
  per-actor INFO counts, and the cause was that **INFO ids are not globally
  unique** - Morrowind.esm reuses 211 of them. An INFO is identified by parent
  topic *plus* id. Merging on id alone had silently eaten half of Eno Hlaalu.
  Nothing else in the pipeline would have caught this.
- **The old JSON dumps had survived** in the scratch directory the previous
  handover said was gone. Moot now that the script converts its own inputs, but
  the note was wrong.

### Two findings that feed WO2

- **Eight player-visible strings live inside script bodies** - `MessageBox` and
  `Say` calls at the Vivec shrines and elsewhere, listed in
  `tools/reports/wo1-script-strings.csv`. Script bodies are frozen by the rules
  and the ESM carries compiled bytecode beside the text, so the transform can
  never reach them. Small, permanent residue. Whether the bytecode really
  governs is **unverified** and is a C++ question, not a Lua one.
- **`sMagicDaedrothID` holds a record ID, not display text.** It is one of the
  two GMST keyword hits and it is writable, and renaming it breaks the summon.
  The rules table needs per-record exclusions, not only per-type rules.

## Open decisions

Canon Part 10 is the register. Most of what used to be here is now closed.

- **Which specific texts are rewritten.** `OPEN` - blocked on the corrected
  actor-ID pass (defect 3 above), not on a judgement call.
- **Vivec's monologue, final wording.** `NEEDS REVISION` - Canon Part 4.
- **The mitochondrial line, text and speaker.** `PROPOSED` - Canon Part 5.

Closed since the last handover, do not reopen: `Aedra -> Zenad` **confirmed**
(and it turns out to be cosmetic, ~20 real lines game-wide); Corprus is a
weapon, not an accident - Zenar nanites running a payload authored by Dagoth
Ur, which recasts the main quest from cure to shutdown; no device tiers; hex
motif sparse and structural, dense reserved for Corprus.

Safe to build on: topic IDs are never renamed (Architecture Part 5); the
naming table in *Shared World Canon* Part 10, with the `Zenaric` (made by
them) / `Zetic` (of their cult) adjective split; magic gating by a Silence
**ability** keyed to a whitelist of equipped item IDs (Architecture Part 8,
Canon Part 8); and the hard boundary in *Shared World Canon* Part 0 - the
setting explains mechanisms, never the origin of the world, the nature of the
soul, or what happens after death.

## Next action

**The engineering is done. What is left is writing.** The mechanism is proved
end to end: rules table to two artifacts to a running game, verified on screen.
Nothing below is blocked on tooling.

1. ~~The hand-written book.~~ **Done, confirmed on screen 2026-08-29.** Both
   copies ship from `tools/handwritten/`, the transform emits authored records,
   and `tools/rules/frozen-records.csv` keeps the rules off them. The pattern is
   there for every hand-written record that follows.
2. ~~Caius Cosades.~~ **Written, not yet seen on screen.** Two of his lines are
   authored overrides: `little advice`, where the vanilla text already listed
   Daedra among what to look out for, and `Blades`, where he explains why two
   words exist for one thing. Both point the player at a wise woman and away
   from a priest, which is where the `Zenar` topic has answers.
3. ~~The `Zenar` topic.~~ **Done, confirmed on screen 2026-08-29.** Six
   informed voices answer it, nobody else does, and the topic is absent from
   every passer-by's list. The transform can now invent records as well as
   override them - `tools/handwritten/dialogue/`.
4. **Vivec's monologue is in the game**, appended to his confession under
   `Dwemer's sin`. The text is still Canon Part 4's `NEEDS REVISION` working
   wording, extracted from the document rather than retyped, so revising Part 4
   and rebuilding is the whole edit. **Read on screen 2026-08-29**, paragraphs
   and all; reachable in a test save with `Journal B8_MeetVivec 50`. The
   mitochondrial line, Canon Part 5, `PROPOSED`, is still unplaced.
5. **`--profile momw` is built.** The load order is
   `D:\Backups\OneDrive\All\Documents\My Games\OpenMW\play\openmw.cfg` - 240
   plugin files, and it already contains `delta-merged.omwaddon` **and**
   `Voices of Vvardenfell.omwscripts`. 327 of our records are defined last by a
   mod, and the build now carries their version forward: the daedric cuirass
   comes out with our name and the armour mod's mesh. Left to do: put our
   **The Delta merge turns out not to be needed for us**, measured: Delta sees
   our plugin and has nothing to reconcile, because a `--profile momw` build
   already carries the other mods' versions of every record it touches. Install
   is: build, put the plugin last, leave the pack's `delta-merged.omwaddon`
   alone, rebuild after any mod-list change. Also learned: regenerating that
   merge fails on the untouched config anyway - `deleted_groundcover.omwaddon`
   has the merge output as its master, which is circular.
   **The user's `play` profile has not been touched.**
6. **The voice mod question is answered, and the answer is worse than a break.**
   Voices of Vvardenfell finds its files by INFO record id, never by text, and
   we keep the ids - so playback works and contradicts the screen. 181 of our
   190 rewritten replies have a voice file. Architecture Part 15 carries the
   three ways out; the cheapest is the mod's own `greetingsOnly` setting.
6. The upstream ticket is written and on the user's Google Drive, for them to
   file.

Raised and scoped, not started: **AI voice acting** for the rewritten lines.
Architecture Part 15 has the measurements - vanilla voices no topic dialogue at
all, none of our 193 lines is voiced, and no vanilla bark says a target word.
The tooling exists and the one conflict is the Delta merge we already do.

## MOMW `graphics-overhaul` compatibility - `SCOPED, MEASURED`

Checked 2026-08-28 against version 8.5.0 of the list in
`D:\Games\OpenMWMods\graphics-overhaul`, 694 plugin files, by
`tools/scripts/momw_compat.py`. Write-up `tools/reports/momw-compat.md`,
per-record detail `tools/reports/momw-compat.csv`.

**The Lua half is clear.** Four plugins touch books we also touch, but all four
change icons and meshes, not text - and load-context edits land after every
content file, on one field, reading the value they substitute into. Not one Lua
file in the whole list writes `openmw.content`, so there is nothing to collide
with either.

**The plugin half collides with two mods that matter**, out of ten:

- `Patch for Purists.esm` - 83 records (80 INFO, 3 CREA), **27** after our own
  dialogue policy. Core, always active, and it exists to fix typos in the
  dialogue we are rewriting.
- `DaedricArmor.esp` (Daedric Lord Armor) - 12 records, exactly the Tier A
  renames: the daedric cuirass, boots, gauntlets, greaves, pauldrons, two
  helms, two `_htab` variants and the dai-katana.

Eight more are single records, several under `Optional/` or `Patches/`.

A Morrowind plugin overrides a record **whole**, so a collision is not a
warning, it is a silent loss: the later plugin wins the entire record and the
other's work vanishes with no message.

**The resolution is already installed.** `Tools/MOMWToolsPack/delta-merged.omwaddon`
is Delta Plugin's output and the list already depends on it. So: generate our
plugin from the **effective** record set rather than the bare masters, add it to
the merge, regenerate. Regeneration after any mod-list change is the standing
cost of the hybrid route, exactly as Architecture Part 12 records it.

Not answered: which plugins are actually in the load order - there is no
`openmw.cfg` in that directory, so every `.esp` present was analysed and the
numbers are an upper bound. Landmass mods add records rather than override
vanilla ones and none appear in the collision list; new content they add is a
scope question, not a conflict.

---

# Rules

- Never modify record IDs, RefIds, script bodies, or script variable names.
- Only modify display fields: names, descriptions, book text, dialogue
  responses, journal entries, GMST strings.
- Never edit Morrowind.esm, Tribunal.esm, or Bloodmoon.esm.
- All replacement text must be plain ASCII (bytes 0x00-0x7F only).
- Replacement strings must not be longer than the string they replace.
- Do not perform substitutions yourself. Write a deterministic transform
  script plus a rules table; the script performs all substitutions.
- Never modify DIAL topic IDs, general dialogue response text, greetings,
  or journal entries. Only uniquely-filtered INFO records may be rewritten.
- When rewriting an INFO record, keep at least one literal instance of the
  original topic keyword so the topic hyperlink still fires. Report
  before/after keyword counts for every record touched.
- **Consult Architecture Part 12 before proposing any write path.** Armor,
  weapon, clothing, creature and dialogue records are NOT writable from Lua in
  0.51. Do not design around them being available.
- **`aedra` must carry a left word boundary, and `daedra` must be applied
  before it.** The string "daedra" contains the string "aedra"; without the
  boundary the transform turns every "Daedra" into "DZenad", mechanically and
  identically, across the whole game. Rule order is fixed and versioned.
  *Shared World Canon* Part 10, `SETTLED`.
- **Never match or substitute with `string.gsub` in Lua.** Its needle is a
  Lua pattern, in which `- . % ( ) [ ] + * ? ^ $` are all special, and it has
  no plain-match flag. `string.find` does, as its fourth argument. A rules
  table of ordinary prose - apostrophes, hyphens, full stops - is exactly the
  input that makes this silently wrong. The WO1 probe's own marker counted as
  zero occurrences of itself before this was fixed, and it was a mock run that
  caught it, not the game.
- **A writable string field may hold something that is not display text.**
  `sMagicDaedrothID` is a GMST whose value is the record ID
  `Daedroth_summon`; renaming it breaks the summon. The rules table therefore
  carries a per-record exclusion list alongside its per-type rules, and every
  new GMST or name rule is checked against the possibility that the string is
  a reference. Found in the WO1 re-run, `tools/reports/wo1.md`.
- **Substitute inside a book's text field; never replace the field.** Book
  text is pseudo-HTML and the markup is load-bearing. The WO0 spike replaced
  one whole TEXT field with a bare sentinel and the page rendered blank in
  game. Substring substitution preserves the markup by construction - the
  point of this rule is that nothing may ever bypass it.
- Do not generate or edit NIF files.
- One system per change set. Report the diff summary before applying.

---

# Working method

Learned the hard way in the WO0 session. These are not style preferences.

- **Never invent an OpenMW API call.** The load context shipped in 0.51,
  after the model's training data. Check, in this order:
  1. the shipped stubs in `resources/lua_api/openmw/` - `content.lua` is the
     authoritative list of what exists;
  2. the engine's own scripts in `resources/vfs` and `resources/vfs-mw` -
     `scripts/omw/esmfallbacks.lua` is a working LOAD-context script and
     showed that in-place mutation (`effect.name = x`) is the real pattern,
     which the docs' "assign a table" summary does not convey;
  3. the 0.51 docs, pinned to `openmw-0.51.0`, not `latest`.

  If it is still unclear, **say "I don't know" and ask.** The user is a
  beginner and cannot audit a plausible-looking wrong call; a wrong one costs
  hours.
- **Read record IDs out of `tools/input/*.esm` with esmtool. Never recall
  them.** Every ID in the WO0 report was read from the master files.
- **Verify a write two ways before believing it:** from the context that
  wrote it, and from an unrelated context that could not have seen a local
  copy. A write accepted in the log and absent on screen is the failure mode
  that matters.
- **Check ASCII bytewise in Python, never with `grep -P`.** In the WO0
  session `grep -P` failed with "supports only unibyte and UTF-8 locales",
  `-q` swallowed the failure, and it reported a file with 27 em-dashes as
  clean. Read the bytes and compare against 127.
- **Syntax-check Lua against OpenMW's own `lua51.dll`** (LuaJIT 2.1, loadable
  from Python via ctypes), then execute the script against a mocked 0.51 API
  surface before handing it over. Both were done for the WO0 scripts.

---

# Paths

- ESM masters: `tools/input/` - copies. The real game folder is off limits.
- Mod output: `mod/` - registered as a data directory in the dev profile.
- Reports: `tools/reports/`
- `tools/cache/` - tes3conv JSON dumps of the masters, ~220 MB, gitignored.
  `tools/scripts/wo1_survey.py` writes them on first run and reuses them after.
- Game logs: `logs/` - the user copies `openmw.log` here after each run.
- Transform scripts: `tools/scripts/`
- `tools/bin/tes3conv.exe` - Windows binary, ESM <-> JSON.

On the user's Windows machine:

- Project: `D:\Work\Morrowind reborn`
- OpenMW: `D:\Program Files\OpenMW 0.51.0\openmw.exe`
- `esmtool.exe` sits beside it in the same folder. Note `-t <TYPE>` to filter
  by record type, `-n <name>` for a single record, and **`-p`, without which
  the contents of dialogue, books and scripts are skipped**.
- Dev profile: `D:\Backups\OneDrive\All\Documents\My Games\OpenMW\dev`
  This is **not** under `%USERPROFILE%\Documents` - OneDrive has redirected
  it, and finding it in the WO0 session took a filesystem search. Do not
  guess this path.
- `run-spike.bat` hardcodes the two paths above and launches with
  `--replace config --config <dev> --content wo0-spike.omwscripts`. The spike
  is registered on the command line rather than by editing `dev/openmw.cfg`,
  so nothing outside the project is modified. Deleting the contents of `mod/`
  removes it entirely.

## Git

**Work on `master` directly. Branches only when there is a reason.** The user
finds a branch-and-PR round trip for every change set more friction than it is
worth on a solo repo, and said so on 2026-08-28. Commit to `master` and push.

Reach for a branch when the change is genuinely risky or wants review before it
lands - a transform that rewrites many records, a change to the masters
pipeline, anything the user asks to look at first. Say why when you do.

`gh` is installed and authenticated as `FaigBagirov`, so PRs, reviews and
comments can all be driven from here when a branch is warranted.

## Two environments

This repo is worked on from two places and they can do different things.

- **Claude Code on Windows** - can read the OpenMW install, run `esmtool` and
  `tes3conv.exe`. Cannot launch the game.
- **Claude Code on the web (Linux container)** - has the repo and the three
  masters in `tools/input/`, but no OpenMW install, no `resources/lua_api` to
  check API calls against, and cannot run the two `.exe` tools. **Do not
  reason about API surfaces from here** - defer that work or ask.

**Claude Code never launches the game in either environment.** The user runs
it and brings back `logs/openmw.log`.

## How in-game tests actually run `SETTLED`

**The user loads an existing save, past character creation.** Not a new game.
They are not going to type a name and pick a class for every probe, and asking
them to is how the WO1 book probe wasted a run: its on-screen card said "start
a new game, the book is in the room you start in", and the save is nowhere
near Seyda Neen.

What follows for every probe from here on:

- **Never place a target by location.** No "it sits on the shelf in the Census
  and Excise Office". The save can be anywhere.
- **Reach the target with a console command instead**, and put the exact line
  in the probe's on-screen card so it can be copied:

      player->AddItem "bk_BriefHistoryEmpire1" 1

  Record IDs are never renamed, so the vanilla ID always works even after the
  probe has rewritten the display name.
- Items, spells and effects can all be handed over this way. If a probe needs
  something that cannot be conjured into the inventory - a specific cell, an
  NPC, a quest state - say so up front and let the user decide whether it is
  worth the trip.
- The probe must still be loaded by the launcher (`--content ...omwscripts`).
  A save opened in a plain OpenMW run shows vanilla data and proves nothing.

---

# What is in `additional/`

Transcripts of the two earlier sessions.

- `chat1.txt` is the complete local Claude Code session, 5712 lines.
- `claude_chat.log` is the same session saved earlier and cut short: it ends
  at what is line 4720 of `chat1.txt`, about a thousand lines short. It can be
  ignored - the only content that is not a prefix of `chat1.txt` is the
  OpenMW path in the opening brief, which the user corrected between the two
  saves.
- `chat2-web.md` is the **web** conversation, 17 to 27 August, 44 exchanges -
  where the fiction was designed and every document in `docs/` was written.
  Exported from claude.ai as Markdown.

  A note for whoever needs it next: saving that page with Ctrl+S produces
  almost nothing. claude.ai virtualises the message list, so an MHTML snapshot
  catches the first two exchanges, the last one, and a "Load later messages"
  button where the middle should be - zero hits for `WO0` or `Zenad`. Use the
  Markdown export.

`chat1.txt` covers the **WO0 build only** and contains exactly two user turns:
the opening brief, and a later instruction to add probes 5-8 so the run would
report what survives and not only what is broken. It ends with the scripts
built and mock-verified, **before the game was ever run** - so the actual spike
result is in `logs/wo0-spike.txt`, not in that transcript.

Everything in all three worth keeping is in `docs/` and in this file. They were
checked against the documents on 2026-08-28 and nothing was found missing.
