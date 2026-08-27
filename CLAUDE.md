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
| WO1 | Dialogue survey (Architecture Part 13) | **First pass done**, results recorded in Canon Part 7. The headline number is a **lower bound** and three reports need regenerating - see below |
| WO2 | Rules table + transform script | Not started |

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

Where the line falls, counting keyword hits from
`tools/reports/wo1-keyword-occurrences.csv` (one hit per record-field):

| Route | Hits | Contents |
| --- | --- | --- |
| Load context, Lua, `mod/` | 369 | BOOK text 336, SPELL name 12, BOOK name 10, INGREDIENT name 6, MISCITEM name 5 |
| Plugin via `tes3conv` | 1005 | INFO text 960, WEAPON name 23, ARMOR name 14, CREATURE name 6, CLASS description 1, CLOTHING name 1 |
| Frozen by policy | 43 | DIAL id 37, CELL name 6 |

So Tier A (equipment and species renaming) and all of Tier C (hand-written
dialogue) are on the plugin side. The load context keeps the books and the
small records. One unmeasured assumption in that table: BOOK *name* sits on
the load-context side because it shares a sub-package with BOOK text. It was
never probed. 10 hits ride on it.

### Outstanding on WO0 - small, none of it blocking

- Whether BOOK `name` is writable. Assumed, never probed: the spike wrote
  `text` only. 10 keyword hits ride on it, and Architecture Part 12 now
  carries the same caveat.
- Why a book with unmarked-up text renders blank. Not a gate - the transform
  never replaces a whole field - but it is unexplained.

`mod/` can be emptied whenever you like; deleting its contents removes the
spike entirely.

## WO1 - the number, and what is wrong with how it was got

`tools/scripts/wo1_survey.py` walking tes3conv JSON dumps of the three
masters. Keywords `daedra` `daedric` `daedroth` `aedra`, case-insensitive
substrings.

**The number Part 13 asks for: 11,502 words**, across **227** INFO records
filtered by a specific actor ID and spoken by **82** actors. Plus roughly
**65 name-field records** for Tier A.

**Treat 11,502 as a lower bound, not the answer.** Canon Part 7 records why:
the cast list was filtered by *keyword* rather than by *actor ID*, so it lists
who says "daedra", not who knows. Yagrum Bagarn and Divayth Fyr - the two
primary sources the fiction is built on - are absent from it entirely. Caius
Cosades appears with 3 records and 195 words, implausibly little for his role.
The true figure needs a second pass and may be a multiple, not a margin.

Concentration is convenient: the top 10 actors hold 42% of the words, the top
30 hold 70%, the median actor has 86 words, and 41 actors have exactly one
line. Two record types carry 92% of the work.

Top of the cast list: Sinnammu Mirpal (25 records / 1177 words), Lalatia
Varian (9 / 601), Smokey Morth (15 / 559), Garothmuk gro-Muzgub (8 / 428),
Vala Catraso (12 / 389). The Ashlander wise women and Temple figures rise to
the top mechanically - the same set Canon Part 6 named from the fiction,
arrived at without a judgement call. That agreement is the evidence that the
actor-ID selection rule works.

2884 topics inventoried (2098 Topic, 758 Journal, 10 Persuasion, 10 Greeting,
8 Voice); 19 carry a keyword in the id, holding 77 INFO between them. All
frozen under the Architecture Part 5 policy.

### Defects - do not build WO2 on these numbers until they are fixed

1. **The cell report is empty and wrong.** `wo1-cell-report.csv` has exactly
   one row: blank `cell_id`, `is_interior=False`,
   `referenced_by_script_count=1231`. The script reads `rec["id"]` for Cell
   records, which does not hold the name, so every cell collapsed onto the key
   `""` - and 1231 is just the number of scripts containing the empty string.
   `is_interior` was never parsed either. Cells with keywords do exist: the
   keyword table has `daedroth CELL name: 6`. This report is empty by bug.
2. **It cannot be re-run.** The script hardcodes its inputs to
   `C:\Users\faig3\.gemini\antigravity-ide\brain\...\scratch\*.json` - a
   scratch directory from a different tool that no longer exists - and its
   output to `d:\Work\Morrowind reborn\tools\reports`. The JSON dumps were
   never kept. Reproducing the run currently means re-running tes3conv over
   three masters first.
3. **The cast list is filtered by keyword, not by actor ID.** It keeps an INFO
   record only if it is actor-filtered *and* contains a keyword (`if speaker
   and has_kw`). Part 13 asks for every actor with actor-filtered INFOs, and
   Canon Part 6 defines Tier C as "who knows", not "who says daedra". Re-run on
   the actor-ID filter alone. This is what makes 11,502 a lower bound.
4. **`occurrence_count` is not occurrences,** and there is no unique-record
   count at all. It counts one hit per record even when the word appears five
   times, and the column name contradicts that. Worse for books: 163
   occurrences of `daedric` in BOOK text could be one book or 163. **Add a
   unique-record-count column** (Canon Part 7).
5. **No cross-check.** Part 13 asks for an esmtool check on a sample of
   records precisely because a walker with a field-traversal bug produces
   confident wrong numbers. Defect 1 is that bug.
6. **The field map only looks at `name`, `text` and `description`.** Any
   record whose display string lives elsewhere is invisible to the survey.
   Concretely: **the report contains zero GMST rows.** GMST strings are
   writable from the load context and are explicitly in scope per the rules
   below, so zero is a number to verify rather than trust.
7. **`aedra` counts are almost entirely phantom.** See the substring rule
   below - this is settled canon now, not a survey defect, but it means the
   `aedra` rows in the keyword report are near-worthless as written.

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

Canon Part 7 sets the first four; they are all one WO1 re-run.

1. Regenerate the cell report.
2. Re-run the cast list on actor-ID alone, no keyword filter. This is what
   turns the lower bound into the real number.
3. Add a unique-record-count column to the keyword report.
4. Fix the `aedra` word boundary and the rule ordering in the rules table
   **before any transform runs**.

Then, and only then:

5. Make the survey reproducible while it is being touched anyway - it
   currently cannot re-run at all (defect 2).
6. Pick a route from Architecture Part 12's three: load-context only, hybrid
   with a plugin for ARMO/WEAP/CREA names, or the upstream request. The
   upstream ticket is worth sending regardless, and worth splitting in two -
   Part 12 explains why the weak half would sink the strong one.
7. WO2 - the rules table.

Raised by the user and not yet scoped: **will the mod be compatible with the
MOMW `graphics-overhaul` list?** The Installation Guide already names that
list as the target. Short answer: the Lua half is compatible by construction;
the plugin half needs a mechanical check that has to run where the mods are
installed, because it means intersecting the record IDs our plugin edits with
the record IDs every plugin in the list edits. Not started.

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

---

# What is in `additional/`

Transcripts of the earlier local Claude Code session.

- `chat1.txt` is the complete one, 5712 lines.
- `claude_chat.log` is the same session saved earlier and cut short: it ends
  at what is line 4720 of `chat1.txt`, about a thousand lines short. It can be
  ignored - the only content that is not a prefix of `chat1.txt` is the
  OpenMW path in the opening brief, which the user corrected between the two
  saves.

They cover the **WO0 build only** and contain exactly two user turns: the
opening brief, and a later instruction to add probes 5-8 so the run would
report what survives and not only what is broken. The session ends with the
scripts built and mock-verified, **before the game was ever run** - so the
actual spike result is in `logs/wo0-spike.txt`, not in the transcripts.
Everything in them worth keeping is summarised above.
