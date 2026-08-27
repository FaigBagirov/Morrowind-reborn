# Morrowind Sci-Fi Conversion

Rewrite Morrowind's lore, magic system and casting visuals into a nanite /
alien-technology setting without breaking the game.

Docs: `docs/` - Architecture (method), Canon (setting).
**Read "State of play" below first**, then both docs, before proposing changes.

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
| WO0 | Load context writability spike (Architecture Part 12) | **DONE** - both log layers plus the on-screen check. Written up in `tools/reports/wo0.md` and Architecture Parts 3 and 12 |
| WO1 | Dialogue survey (Architecture Part 13) | **First pass done.** Produces the headline number, but has defects - see below |
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

On screen the user confirmed: the spell **renamed**, the egg **renamed**, the
cuirass and the mudcrab **not** renamed - matching the logs exactly on all
four. Checks 5 (GMST) and 8 (MGEF) were not reported; they are two lines of
the same tooltip that already showed the spell renamed, so they cost one hover
next time.

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

- Checks 5 (GMST) and 8 (MGEF) on screen. One tooltip hover.
- Whether BOOK `name` is writable. Assumed, never probed.
- Why a book with unmarked-up text renders blank. Not a gate - the transform
  never replaces a whole field - but it is unexplained.

`mod/` can be emptied whenever you like; deleting its contents removes the
spike entirely.

## WO1 - the number, and what is wrong with how it was got

`tools/scripts/wo1_survey.py` walking tes3conv JSON dumps of the three
masters. Keywords `daedra` `daedric` `daedroth` `aedra`, case-insensitive
substrings.

**The number Part 13 asks for: 11,502 words**, across **227** INFO records
filtered by a specific actor ID and spoken by **82** actors. That is the cost
of Tier C.

Top of the cast list: Sinnammu Mirpal (25 records / 1177 words), Lalatia
Varian (9 / 601), Smokey Morth (15 / 559), Garothmuk gro-Muzgub (8 / 428),
Vala Catraso (12 / 389). The Ashlander wise women and Temple figures rise to
the top mechanically - the same set Canon Part 10 named from the fiction,
arrived at without a judgement call. That agreement is the evidence that the
actor-ID selection rule works.

2884 topics inventoried (2098 Topic, 758 Journal, 10 Persuasion, 10 Greeting,
8 Voice); 19 carry a keyword in the id. All frozen under the Part 5 policy.

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
3. **`occurrence_count` is not occurrences.** It counts one hit per record
   even when the word appears five times in it. A code comment admits the
   choice; the column name contradicts it. Decide which is wanted and label it.
4. **The cast list is narrower than Part 13 asks.** It keeps an INFO record
   only if it is actor-filtered *and* contains a keyword (`if speaker and
   has_kw`). Part 13 asks for every actor with actor-filtered INFOs. The
   current file is the Tier C worklist, which is more immediately useful - but
   it is not what the spec says, and the difference is not recorded anywhere.
5. **No cross-check.** Part 13 asks for an esmtool check on a sample of
   records precisely because a walker with a field-traversal bug produces
   confident wrong numbers. Defect 1 is that bug.
6. **The field map only looks at `name`, `text` and `description`.** Any
   record whose display string lives elsewhere is invisible to the survey.
   Concretely: **the report contains zero GMST rows.** GMST strings are
   writable from the load context and are explicitly in scope per the rules
   below, so zero is a number to verify rather than trust.

## Open decisions that block writing

From Canon Part V. Q5 was called the critical path; WO1 has answered its
mechanical half (the cast list). Which specific texts get rewritten is still
a judgement call only the user can make.

- **Q1 `Aedra -> Zenad` is `PROPOSED`, not settled.** 338 INFO hits and 84
  BOOK hits ride on it. Nothing in the rules table can be written until this
  is confirmed or replaced.
- Q2 What Corprus is, precisely. `OPEN`
- Q3 Device tiering. `OPEN` - note that Architecture Part 8 records "no tiers"
  as `SETTLED`, so this entry contradicts it and needs closing out.
- Q5 Which specific texts are rewritten. `OPEN`
- Q6 Hex motif density. `OPEN`

Settled and safe to build on: topic IDs are never renamed (Architecture
Part 5); the naming table in Canon Part 9 with the `Zenaric` (made by them) /
`Zetic` (of their cult) adjective split; magic gating by a Silence **ability**
keyed to a whitelist of equipped item IDs (Architecture Part 8, Canon
Part 13).

## Next action

1. Second WO1 iteration: fix the cell report, make the survey reproducible,
   settle the counting semantics, add the cross-check, re-run.
2. Get Q1 answered.
3. Decide one plugin or two (Architecture Part 3, end of *Result*).
4. Then WO2 - one rules table with a `route` column feeding two emitters, so
   the setting stays a single reviewable file while the load-context half and
   the plugin half are generated separately.

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
  original topic keyword so the hyperlink still fires. Report before/after
  keyword counts for every record touched.
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
