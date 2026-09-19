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

`CREDITS.md` records third-party work and what it obliges. The closed helm's
mesh is CC-BY and **must** carry its author's credit if anything is ever
published. Check that file before a release, not after.

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

Two launchers, and they are not interchangeable. `run-mod.bat` is the Gate 3
harness: clean dev profile, three masters, our two content files passed on the
command line. `run-play.bat` starts the **real** modded game - the `play`
profile as it stands, with the conversion already registered in its own
`openmw.cfg`, and `openmw.cfg.bak` beside it to undo that. Claude may run
either of them itself - see "Claude can run the game and look at it". (The old
"only the user runs them" rule was lifted by the user on 2026-09-15.)

## Who works where `2026-09-19`

Faig runs several sessions at once, each on one line of work. **The
orchestrator - "Main - Orchestrator - Morrowind reborn code local" - watches
all of them**, merges their branches and keeps this file true. Faig's words:
texts go to a separate fork; the orchestrator keeps an eye on everything at
once. It asks the others for status and never gives them orders.

Titles change and the sidebar title can differ from the name a session answers
to; find sessions with `ListAgents`. Two start with "Main": the orchestrator,
and "Main - Генерация 3Д моделей (fork)", which owns 3D generation.

| Line of work | Session | Worktree, branch | State, 2026-09-19 |
| --- | --- | --- | --- |
| Everything, this file, merges | "Main - Orchestrator - Morrowind reborn code local" | `D:\Work\Morrowind reborn`, `master` | |
| Texts - books, dialogue, the rule-rewritten replies, canon wording | "Text fork - Morrowind reborn code local (fork)" | `D:\Work\Morrowind reborn 2`, `secondary` | just made |
| Imported armour: Zenar (Ageless model) on Daedric, Wolf power armour on Dwemer | "Morrowind reborn code - armor" | `D:\Work\Morrowind reborn armor`, `new-armor` | both worn on screen; **paused until the weekend** by Faig. Next: merge master, skin arms, hands and thighs. Blocker: no vanilla donor carries the full bone set for skinned arms |
| Generated armour: a helm from a sketch, then the cuirass | "Своя модель брони" (sidebar: "Контекст проекта и память сессий") | `D:\Work\Morrowind reborn gen`, `gen-armor`, cut from `new-armor` | helm on `chitin helm` with its grid copy on `chitin_mask_helm`, on screen; waiting for new generations to compare. Its own plugin `zenar_gen_helm.esp`. Leaves `new-armor` alone |
| Generating 3D models | "Main - Генерация 3Д моделей (fork)", "... - новый поиск моделей" | `E:\AI-models`, outside this repo | |
| Local AI stack: game-control, local-workers | "Pony Diffusion V6 XL setup" | `E:\AI-models` | |
| Skyrim | the Skyrim sessions | `D:\Work\Skyrim_Reborn`; they place shared canon into `secondary` | |

For a session working in a worktree other than the main one:

- **The shell's working directory resets to `D:\Work\Morrowind reborn` after
  every command.** Use absolute paths and `git -C "<worktree>"`, always, or the
  command runs against master.
- Commit on your own branch. The main session merges it into master, as it did
  with the first fork on 2026-09-14 (`e1fcfac`). Two sessions committing in one
  worktree share one index and one set of files, which is the collision this
  split exists to avoid.
- The game for the second worktree is `run-play-2.bat` or
  `tools/scripts/play2.ps1`: an isolated second instance with its own log,
  saves and screenshots, and the play profile only ever read.

`secondary` was fast-forwarded to master on 2026-09-19, so the text fork starts
from everything above.

### Session transcripts: images out, links in `SETTLED 2026-09-19`

Screenshots made the sessions heavy - the orchestrator's transcript was 133 MB,
most of it images, and Remote Control refused it ("too much data").
`tools/scripts/swap_session.py` moves every image into
`session-images/SID8/` (gitignored, with an `index.html` gallery) and leaves a
local link in its place. **Measured on a live session:** 133.8 MB became 20 MB,
the session opened, the links click and open the pictures, and Remote Control
switched on. Done the same day for the old orchestrator (133 to 19 MB), the
first fork (98 to 14 MB) and the text fork (132 to 19 MB).

- **Never on a running session** - the script refuses while the transcript was
  written to in the last minute. A session cannot strip its own live transcript:
  the safety check blocks it, and must. Faig double-clicks
  `session-images/strip-SID8.bat` with that session closed, or a sister session
  runs `swap_session.py SID strip` for a closed one - only with his yes.
- **Nothing is deleted.** A full backup is kept beside the images;
  `restore-SID8.bat` puts it back and sets the current file aside first.
- SID is the transcript's file name (the CLI id), not the app's `local_...` id.
- **Never clear a conversation to make room.** It was tried once and scared
  Faig; lightening is the answer, wiping is not.

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
- **Canon Part 8 against *Shared World Canon* Rev 5.** Closed 2026-09-07,
  Canon Rev 5. The integrated-interface wording is gone: everyone carries a
  key in some form (Shared Part 11), the player arrives without one and the
  Empire issues it, humanoid casters carry theirs in forms the engine does
  not model, so the player-only gate stands. The Abilities and Powers rows
  stay: congenital endowment is the endosymbiont of Shared Part 3, not the
  key.
- **Vivec's monologue against the Rev 5 framing rule.** Checked 2026-09-07.
  Placement passes; the second sentence of the appended text, "Now the only
  thing worth knowing, and then I am done", is a lead-in and goes when the
  monologue is revised. Canon Part 4 constraint 6. The in-game record keeps
  the working text until then. Rev 5 also adds Part 9A (authorless text) and
  expands Part 6 (Azura, Meridia, the beast forms); none needs a Morrowind
  change.
- **Morrowind Canon against *Shared World Canon* Rev 6.** `OPEN` - Rev 6
  landed 2026-09-09, written in the Skyrim project and carried up here
  unchanged; this repository owns the file, so nothing of it was authored
  locally. Two additions. Part 3: the Zenad trace is unevenly distributed
  between populations and that, and only that, is what racial differences in
  capacity are; the Altmer are right that less was lost in them and wrong
  about what was lost, and Breton resistance is the same fact read backwards.
  Part 11: swarm and field are one medium seen from two sides, reached by
  three routes (commands in the system's own language, a controller, direct
  supply), and capacity from Part 3 never substitutes for access from Part
  11. What to check here: whether the racial magicka and resistance numbers
  the conversion inherits now have a stated cause that any Morrowind text
  contradicts, and whether Canon Part 2 or Part 8 says anything about the
  medium that the three-route table supersedes. No Morrowind text is known to
  break; the check has not been run.
- **Four reading flags from the Skyrim project.** `OPEN` - written up in
  `docs/Skyrim_Project_Flags_v1.md`, placed here 2026-09-10 by a Skyrim
  session. Not canon, not authoritative over `docs/`, and nothing in this
  repository has been changed for them. Skyrim has now read its entire book
  corpus, 1 119 records, and four texts came out of it that this project
  decides: The Firmament, where the divergence from Skyrim's shipped text
  turns out to be exactly one inserted paragraph and nothing else;
  Nchunak's Fire and Faith and Hanging Gardens, both Dwemer voices about
  the Heart that Skyrim carries and mirrors; and The Warrior's Charge, a
  Redguard poem Skyrim found in its final sweep that dramatises the
  Firmament's Warrior and his three Charges exactly, which means any
  decision here about the constellations has a second Skyrim text
  downstream of it. Nothing blocks Skyrim; it will touch none of them
  until this side answers.
- **Shared World Canon Rev 7.** Applied 2026-09-19, approved by Faig in a
  conversation between the orchestrator and the Skyrim chat on claude.ai
  ("Skyrim sci-fi mod"): Retooling (Part 3), the job list and soul gems
  (Part 11, with the first ever change to Part 0 rule 2), `Aedric` to `Zenad`
  (Part 10), and four delivery rules (Parts 5, 8, 11). The revision log has the
  detail. Still `OPEN`: the Tribunal under Part 8's contact rule, and the
  Morrowind texts have not been checked against Rev 6 or Rev 7. Two text rules
  follow, **in the rules table since 2026-09-19** (text fork, `secondary`):
  `R590` turns `Aedric` into `Zenad` in *Sithis* (`BookSkill_Alteration3`), and
  `R580` turns "like an Aedra" into "like a Zenad" before the Aedra rule can
  make it "an Zenad". One firing each, both in that book; the Lua engine agrees
  with the Python one on all 190 fields. The Skyrim chat read the Firmament paragraph and found it
  clean - a description with no name in it.

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
2. ~~Caius Cosades.~~ **Done, read on screen 2026-08-29 on the `play` profile.**
   Two of his lines are authored overrides: `little advice`, where the vanilla
   text already listed Daedra among what to look out for, and `Blades`, where he
   explains why two words exist for one thing. Both point the player at a wise
   woman and away from a priest, which is where the `Zenar` topic has answers.
   `Blades` came up whole, and its inherited topic links still fire - `Temple`,
   `guilds and factions` and `orders` are all live in the rendered text.
3. ~~The `Zenar` topic.~~ **Done, confirmed on screen 2026-08-29.** Six
   informed voices answer it, nobody else does, and the topic is absent from
   every passer-by's list. The transform can now invent records as well as
   override them - `tools/handwritten/dialogue/`.
4. **Vivec's monologue is in the game**, appended to his confession under
   `Dwemer's sin`. The text is still Canon Part 4's `NEEDS REVISION` working
   wording, extracted from the document rather than retyped, so revising Part 4
   and rebuilding is the whole edit. **Read on screen 2026-08-29**, paragraphs
   and all; reachable in a test save with `Journal B8_MeetVivec 50`. The
   mitochondrial line is **written, placed and read on screen 2026-08-29**:
   Divayth Fyr, topic `corprus disease`, appended after the vanilla paragraph,
   right after he has had the player's blood on the glass. Canon Part 5 - which
   is still `PROPOSED` there, because being in the game is not the same as the
   wording being approved.
5. **`--profile momw` is built.** The load order is
   `D:\Documents\My Games\OpenMW\play\openmw.cfg` - 240
   plugin files, and it already contains `delta-merged.omwaddon` **and**
   `Voices of Vvardenfell.omwscripts`. 327 of our records are defined last by a
   mod, and the build now carries their version forward: the daedric cuirass
   comes out with our name and the armour mod's mesh. **Confirmed on screen
   2026-08-29** - `Zenaric Cuirass`, armour rating 26, value 70000, worn as
   Daedric Lord Armor. That was the one part of the hybrid route that had only
   ever been measured.
   **The Delta merge turns out not to be needed for us**, measured: Delta sees
   our plugin and has nothing to reconcile, because a `--profile momw` build
   already carries the other mods' versions of every record it touches. Install
   is: build, put the plugin last, leave the pack's `delta-merged.omwaddon`
   alone, rebuild after any mod-list change. Also learned: regenerating that
   merge fails on the untouched config anyway - `deleted_groundcover.omwaddon`
   has the merge output as its master, which is circular.
   **The user's `play` profile has not been touched.**
6. **The voice mod question is answered, and decided.** Voices of Vvardenfell
   finds its files by INFO record id, never by text, and we keep the ids - so
   playback works and contradicts the screen. 181 of our 190 rewritten replies
   have a voice file. **Faig decided 2026-08-31: those lines get re-voiced**,
   and nothing - `greetingsOnly` included - is reconfigured in the meantime to
   hide the mismatch. Architecture Part 15. Text settles first, audio last.
7. ~~The particle textures.~~ **Done, all 36, confirmed in the `play` profile
   2026-08-29.** Light, `self dispel` and `hearth heal` cast in the Vivec
   exterior: every one a hexagon swarm in its own colour, plates at the finer
   size, and the Light redirect took. Nothing in the visuals is unproven any
   more. Only the grain shader is left, and Canon Part 9 puts that in
   post-processing rather than in particles.
8. The upstream ticket is written and on the user's Google Drive, for them to
   file.

Raised and scoped, not started: **AI voice acting** for the rewritten lines.
Architecture Part 15 has the measurements - vanilla voices no topic dialogue at
all, none of our 193 lines is voiced, and no vanilla bark says a target word.
The tooling exists and the one conflict is the Delta merge we already do.

## Texts: what the first fork did, and the queue `MERGED 2026-09-14`

The first fork, "Morrowind reborn code local (fork)", did the lore work on
2026-08-30/31 while the main session fitted armour. All of it is on master.
The detail is in `tools/reports/magicka.md` and `tools/reports/whats-left.md`;
this is what a new session must not have to rediscover.

**Magicka is Charge, in the game's own voice.** 59 records, all on the Lua
route: 14 game settings, 20 spell names, 15 potion names, 10 effect
descriptions. The damage-type sense is `Discharge` - Faig's word, over the
proposed `Signal`. **Mortals keep "magicka"**: 121 dialogue lines and 39 book
fields, *Shared World Canon* Part 9. Faig put it as "for now", so the split is
his to revisit. Seen on screen 2026-08-31: the stat sheet reads `Charge 40/40`,
a spell reads `Resist Discharge`, a potion `Cheap Restore Charge`.

- **Effect names are a separate write.** The engine copies them out of a game
  setting before our script runs, so they are not a field of any record. The
  effect id comes from the setting's *value*, not its id - Bethesda's two names
  disagree, and the ESM and OpenMW spell one effect differently - and is checked
  against the engine's own list before a target is emitted.
- **Architecture Part 12's `GMST | writable` was a Lua readback, not the
  screen.** The screen now confirms it for the stat sheet. One early run showed
  `Magicka` while the readback said `Charge`; why is not established, and the
  fork's first conclusion from it - that settings never reach the interface -
  was wrong. Do not repeat it.
- **The Firmament carries one added paragraph** after the Mage entry: a hint
  that it is done with nanites, not an explanation - Faig's call. Read on
  screen, page 5-6. `tools/handwritten/bk_firmament.txt`. Skyrim's flag 1 asks
  whether this paragraph is final.
- The length rule is measured now, not a proxy - see Rules.

**The queue**, counted by `tools/scripts/audit.py` over the masters with the
rules applied:

1. **191 replies rewritten by rule, across 83 topics, and nobody has read
   them.** A rule guarantees the word changed, not that the sentence still
   means something. Before and after are in `tools/reports/transform-diff.csv`.
   **Faig will read them as a diff, the way git shows one, with the changed
   words marked in the line** - not as before/after columns, which he finds
   hard to read. Building that view is the text fork's first task.
2. 80 of those 191 keep one literal old keyword so the topic link fires, and
   so carry Zenar and Daedra in one paragraph.
3. **17 topics in the player's list are still spelled the old way**, holding
   74 replies - `Daedra`, `Daedra worship`, `Daedric sites` and the rest.
   Structural: a topic's id is the word shown, and ids are frozen (Architecture
   Part 5).
4. **290 arcane words in the engine's own voice** - `Cast Cost`, "a magical
   shield", `Mage`, `College of Destruction`, `Spell Breaker`. The interface
   says Charge and then says Cast Cost. The same shape of pass as magicka, but
   the words have to be decided, not substituted. Separately, 87 religious
   words (Almsivi Intervention and the like) - a judgement call, listed so it
   is made against a number.
5. Canon still open: Vivec's monologue `NEEDS REVISION`, the mitochondrial line
   `PROPOSED`, the Rev 6 check, the four Skyrim flags. All must settle before
   the re-voicing of those lines.
6. The hand-written layer is small: three books, five overridden replies, one
   invented topic with six answers.

Handing the game to a friend is **too early**, Faig said 2026-08-30; what he
meant was the list above. The five packaging gaps are in `whats-left.md` for
when it is time.

## Particle visuals - `DONE, ALL 141 EFFECTS, CONFIRMED IN THE REAL PROFILE`

Canon Part 9, report `tools/reports/vfx.md`, generator
`tools/scripts/make_vfx.py`. Output is `tools/build/vfx-<profile>/Textures/`,
36 files a profile, added to a config with one `data=` line and removed by
deleting it. Nothing goes into `mod/`.

**Confirmed on screen 2026-08-29.** The user cast `summon flame atronach` in the
Vivec Fighters Guild, saw the hexagon field on his hands, and called it good for
a first iteration. Shape, threads, plate size and the torn Corprus variant are
all settled at this iteration.

**What he caught in the same run is the lesson.** Only that one spell had
changed. The first pass shipped the six textures with the highest effect counts,
which the report's own table called most of the game - it is 85 of 141, so 56
effects still cast vanilla, and the player's magic changed denomination between
one spell and the next. **A partial visual conversion reads as a bug, not as a
style.** The generator no longer picks: it reads every texture named by any
magic effect straight out of the masters, 36 of them, 141 of 141 effects.

Three things worth carrying forward:

- **The field is computed once and reused.** It never depended on the source -
  only the colour does, and that is sampled from what is installed. One
  technology, one structure, each school's own light. The six textures the user
  approved regenerate **byte for byte identical**, which is how that refactor
  was allowed to happen at all.
- **`tools/scripts/bsa.py` reads Morrowind BSAs directly**, so the vanilla
  profile no longer needs `delta_plugin vfs-extract`. Verified against it: the
  six files the first pass extracted come back identical.
- **`tools/scripts/dds.py` writes every DDS in the project**, mipmapped, BGRA or
  DXT1 or DXT5. `add_mips.py` is deleted: its whole purpose was a second command
  run after the generator, forgetting it once nearly shipped 36 mipless
  textures, and the separateness was the defect. All 36 particle textures
  regenerate byte for byte identical across that move.
- **1024 DXT5, 36 plates across.** Faig asked for smaller hexagons; the limit
  turned out to be the rim rather than the cell, so the answer was resolution.
  DXT5 pays for it exactly - 1,398,256 bytes against 1,398,228 for the 512
  uncompressed it replaces. The earlier refusal to compress was reasoning, not
  measurement, and measurement reversed it: mean alpha error 1.5 of 255.
- **The generator writes into bounding boxes, not the whole canvas.** Thirty
  seconds a profile instead of ten minutes, and one colour byte in 1,048,576
  differs from the old code, none in alpha.

**`Light` is converted, and the write is proved.** Its effect record names
`tx_firealpha00a`, which is not a magic texture - it is the world flame sheet
every torch and campfire wears, and overriding it would put hexagons on every
fire in the game to convert one spell. So it is excluded by name, and instead
`mod/scripts/rewrite/apply.lua` points the record at a private copy.

`MagicEffect.particle` **is writable from the load context in 0.51.** It was not
a WO0 probe and nothing documented that it had a setter, so the write was
guarded. It took, 2026-08-29:

    [REWRITE] light: particle tx_firealpha00A.tga -> vfx_zen_light.dds

Verified the two ways the working method asks for: the readback in the load
context, and the engine's own use of the field on screen - Faig cast Light in
the Vivec exterior and got the warm hexagon swarm, not the vanilla flame. Add
`particle` to the short list of MGEF fields known to be writable, beside `name`.

## Zenaric armour - `WORN AND ITERATED, HELM SETTLED`

Report `tools/reports/armour.md`, generator `tools/scripts/make_armour.py`,
output `tools/build/armour-momw/Textures/jy_daedric/` - 15 files, one `data=`
line in the play profile, delete the line to undo it.

Faig asked on 2026-08-30 for the Daedric armour reworked toward a white-and-gold
ceramic reference, "with notes of the original". **No geometry** - the rules and
Canon Part 9 both forbid generating NIFs - so the silhouette is untouched, which
is what supplies the second half of the brief for free.

**Where it landed after several rounds on screen:** silver-grey plate at 0.50,
cool, with the marbling he asked to keep and to spread from the helm to the
cuirass; a dark kant around every plate, drawn from the gradient of the plate
mask; a sheen baked out of the mod's own normal map. The helmet is the **Face of
Terror with its gold removed**.

**The closed-helm experiment is over.** He chose the Ebony Closed Helm shape,
asked for a Pragmata-like paint job, and after four rounds called it off. Our
override of `tx_a_ebony_helmet` is deleted and every ebony helm in the game is
vanilla again. Kept from it: `uv_calibrate.py` (which way does a piece face -
answered by measurement, right first time) and `uvmap.py` (parse and rasterise a
mesh, validates its own parse). `paint_helm.py` is deleted rather than left
switched off.

We write the diffuse and the glow. `_n` and `_s` are deliberately not written,
so Daedric Lord Armor's own normal and specular maps stay in use.

Three things worth carrying forward:

- **The specular map is the source of structure, not the diffuse.** The diffuse
  has median luminance 0.094 and p90 0.191, so the whole sculpt is in a dark
  band and stretching it turns compression noise into dirt. The specular has the
  range - and it carries the artist's own judgement of what is hard armour
  against what is cloth or mail, which is what separates ceramic from mechanism.
- **Gold has to be qualified by that mask.** Red in the source marks the hot
  veins, but it also marks dyed leather and cloth, and unqualified it turned the
  collar strap and the cuirass's fabric panel solid gold.
- **Contrast has to sit close to the plate.** Trim at 0.78 against a 0.50 plate
  read as black-and-white stripes on screen, twice. Trim should say "a different
  metal", not "a different object". Steel is 0.60 and the mechanism is lifted
  off black.
- **The dark mottling was the right answer.** It is the Daedric coral pattern,
  painted low-specular, so the mask calls it not-plate. It was flagged as an
  open question and Faig's call went the other way from the guess: he liked it
  and asked for the cuirass to match, so grain is 1.0 across the suit.

**On the no-geometry rule: measured, and the claim was false.** Canon Part 9
said "the engine validates models on load and rejects machine-assembled files",
and I quoted it to Faig as fact although nobody here had ever checked it.
OpenMW ships `niftest`, which is the authority, and it accepts a script-scaled
mesh, a script-deformed one, and a file carrying 3,269 vertices of downloaded
geometry. Corrected in Canon Part 9; full account in `tools/reports/nif.md`.

The rule is kept on better grounds - good geometry is sculpting rather than
scripting, and a bad mesh sits under animation and collision - but **reusing
someone else's mesh is now a working route**, not a theoretical one.

## The imported model lives on `new-armor`, not on master

Faig asked on 2026-08-31 for master to stay playable while the imported suit is
still being fitted. So:

- **master** carries the Zenaric *recolouring* and nothing else of the import.
  That is textures written by `make_armour.py` into
  `tools/build/armour-momw/Textures/jy_daedric`, reached by one `data=` line.
  `transform.py` no longer emits bodypart records or repoints the Daedric
  armour: the step is behind `--import-armour`, off by default.
- **`new-armor`** carries the whole import - the cut, the fit, the tables of
  corrections, and `--import-armour` in the build command.

The built meshes under `tools/build/armour-momw/Meshes/zenar` are gitignored
and stay on disk either way; with the plugin not naming them they are simply
unused, so no profile edit is needed to go back and forth.

## Testing a mesh in game: two methods Faig set, `SETTLED 2026-09-14`

Every round of the imported-suit fitting cost a full rebuild and a restart per
guess, and several rounds were lost to one question a screenshot could not
answer - which way round a piece is. Faig proposed both fixes. **Use them
before the next fitting round, on `new-armor`, never on master.** Merge master
into that branch first; it was cut before this section existed.

**1. One restart, several candidates.** Build every candidate - four turns of
a hand, three drops of a forearm - as its own bodypart, and repoint a
*different* vanilla armour record at each: chitin gauntlets carry candidate A,
bonemold B, ebony C, glass D. One launch, then `Equip` each through
`console.ps1`, photograph, compare. A restart is paid when the method changes,
not per guess.

- The stand-in records must cover **the same biped slots** as the piece under
  test. A gauntlet record carries Hand and Wrist; a pauldron test needs
  pauldron records. Read the slots with esmtool, never recall them.
- Hand the player every candidate item in the card, `player->AddItem "<id>" 1`,
  so nothing depends on what the save happens to carry.
- The stand-ins are a test build. Their own meshes are borrowed for the
  session and must never reach a plugin on master.

**2. A diagnostic sheet instead of the model's texture.** Paint the pieces
under test with a grid of small cells, **no two alike** - hue by column,
lightness by row - so any patch on screen names its place on the UV sheet and
therefore on the piece. The rainbow bands of `uv_calibrate.py` were the first
version of this; the grid extends them from one axis to two.

- **Every cell also carries an asymmetric glyph**, an F or an L-notch.
  Colour alone gives position but not handedness: a mirrored piece shows the
  same colours in reversed order, which is easy to miss, while a backwards F is
  not. That is exactly the failure behind the swapped hands and the
  fingers-up-or-down rounds.
- Generate it through `dds.py` like every other texture here, and point the
  candidates at it with `--texture`. The model's own atlas goes back on once
  the fit is settled.

**3. Always two copies, both in the same launch.** `SETTLED 2026-09-19`,
Faig's rule after the generated helm on `gen-armor`. **Every** 3D model checked
in this game - and any 3D model at all - goes in twice: once in its real
texture, once in the diagnostic sheet of method 2, each on a **different** free
vanilla armour record of the same slot (chitin carries the real one, another
free record the diagnostic one). Both are loaded in one launch and **both are
looked at, every time**.

- The reason is Claude, not the model: Claude does not always read a render
  correctly. On 19.09 a spiked vanilla mask showing through the new helm was
  taken for the vanilla helm itself, and dark blotches that were a flipped UV
  were blamed on shading, twice. The grid copy would have named both at once.
- Coloured copy for shape, direction, mirroring, holes and UV; real copy for
  how it looks. Neither replaces the other.
- Use records nobody else is repointing: the Daedric set belongs to the
  imported suit on `new-armor`.

## The Zenaric suit from an imported model - `WORN, WHOLE, ON SCREEN`

Twenty pieces off one downloaded model, head to foot, built by
`build_armour_set.py` in one command and seen on the character. Read that
script's header for the route and the traps; what follows is only the state.

**Every slot: head, neck, chest, groin, both clavicles, upper arms, forearms,
hands, upper legs, knees, ankles, feet.** The four Daedric helms, the cuirass,
greaves, boots, pauldrons and gauntlets are all repointed at them, and the
cuirass gains a Neck slot that vanilla armour does not carry - vanilla leaves
the throat to the naked body, which we replace.

Five things went wrong in front of Faig and each one is now a rule in the
script rather than a memory:

- **A donor must not be skinned.** Every cuirass in the game is. Replacing the
  geometry leaves its bone weights describing the old vertices, and the torso
  shears into a blade reaching the floor.
- **Both sides must be built.** Vanilla records leave the left slots empty and
  let the engine mirror; mirroring negates an axis of the local coordinates,
  which throws an offset piece off the body. Faig's left leg vanished.
- **A bone with no slot inherits its parent's.** Name-matching alone dropped
  1,107 of 12,290 vertices - hip cloth, straps, a tail, elbow deformers - and
  the holes showed as a torso you could see the floor through.
- **Read every distinct skinned primitive.** The body and the helmet are
  separate meshes, each listed three times with a different material. Stopping
  at the first meant no helmet, and the collar lives on the helmet.
- **Write both facings.** 15 to 27 per cent of the edges in each piece belong
  to one triangle; with the body replaced, a hole shows the room.

Left open: the model's own dark under-suit reads as black in places, which is
the model rather than a fault; and the texture is the model's atlas recoloured,
not yet tuned to the rest of the conversion's palette.

## Meshes from outside - `WORKING END TO END, BEING FITTED`

Five tools, each doing one thing, all validated against something rather than
asserted:

| Script | Does |
| --- | --- |
| `nif_info.py` | version, UVs, polycount and OpenMW's own verdict on any downloaded `.nif` |
| `uvmap.py` | parse and rasterise a mesh; per-pixel height and azimuth |
| `glb.py` | read glTF and GLB, list primitives, extract one to OBJ |
| `obj.py` | OBJ in and out; round-trips a mesh with 4.6e-08 of error |
| `obj_split.py` | cut a whole suit into pieces, by label or by connected component |
| `nif_write.py` | put new geometry into a donor NIF, fitted and retextured |
| `glb_bodyparts.py` | cut a rigged body into Morrowind's slots, by bone |
| `bodyparts.py` | emit the bodypart records and repoint the armour at them |
| `build_armour_set.py` | the whole route in one command, and the instruction |

What the community says about Blender, NifSkope versions and skinning weights -
not measured here - is in `tools/reports/mesh-tools.md`.

Four things worth carrying forward, because each cost a round:

- **`.nif` is a family, not a format.** Morrowind is 4.0.0.2, Oblivion
  20.0.0.5, Skyrim 20.2.0.7. Same extension, only one loads.
- **The polycount budget I quoted was wrong.** 89 to 177 vertices is what
  *vanilla* helmets use, not a ceiling. Across 828 mesh files in the installed
  modpack: median 986, ninetieth percentile 3,407, largest 14,696.
  `DaedricArmorM.nif`, worn while I said it, is 8,230.
- **A donor's texture name is baked into it.** A mesh built on the ebony helm
  wears the ebony texture until `--texture` repoints it.
- **Morrowind bodyparts are Y-up with +Z forward**, same as glTF, so no axis
  swap is wanted. Measured on the ebony helm - the sheet's vertical axis runs
  along -Y at 0.998 correlation, and Faig's colour-band calibration puts the
  front at +Z. Swapping is a ninety-degree roll about the ear-to-ear axis, and
  on screen that is a helmet nodding at the floor.

**The build must never scan its own output.** Installed, the plugin sits last
in the load order and wins every record it defines - already converted - so the
next `--profile momw` build reads `Zenar` back as the effective text, matches no
rule, and emits a plugin with the renames missing. It happened once: 347 records
became 21, 327 defined-last became 519, and **nothing warned, because every step
succeeded**. Excluding our own build directory fixed it once and then failed:
the installed file is `scifi-rewrite-momw.esp` while `--out-name` defaults to
`scifi-rewrite`, and a profile can name our plugin from the other worktree. So
`transform.py` now reads the stamp `Generated by transform.py` from each
file's own header (`MADE_BY`, `is_ours`), which no rename or move removes. If a
rebuild ever comes out small, check this first and compare against
`--profile vanilla`, which cannot be affected.

**A parse bug of mine, now fixed and worth knowing about.** Four bytes sit
between the vertex count and the vertex array, and `uvmap.py` read every mesh
four bytes short. A float array at the wrong offset is still a float array, so
nothing complained - the vertices simply came back shifted against their own
UVs. That is what made the ebony helm's azimuth map look like a patchwork, and
I concluded from it that the unwrap could not be painted on. The parser now
verifies itself against the file's own bounding sphere, which no wrong offset
can satisfy.

Out of scope on purpose, and each for a reason: Dremora skin (a creature's body,
not equipment), vanilla Daedric weapons and shields (no specular map exists for
them in this load order, so a different tuning problem - but a white cuirass
beside a black dai-katana will show), and Daedric ruins (those are Zetic, the
cult's architecture, not Zenaric manufacture).

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
- Replacement strings must not be longer than the string they replace,
  unless the rule sets `allow_longer`. Then every string it produces is held to
  the longest vanilla string already shipping in the same record type and
  field, measured off the masters - the validator, the transform and the Lua
  half all enforce it. `tools/reports/magicka.md`, 2026-08-30.
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
- Do not generate or edit NIF files. **The reason is not the one Canon Part 9
  gave.** That sentence - "the engine validates models on load and rejects
  machine-assembled files" - was measured on 2026-08-30 and is false: OpenMW's
  own `niftest` accepts a mesh a script reshaped. `tools/reports/nif.md`. The
  rule is kept because good geometry is sculpting rather than scripting, and
  because a bad mesh sits under animation and collision and cannot be undone by
  deleting a `data=` line the way a bad texture can. Reading a mesh is fine and
  is done: `tools/scripts/uvmap.py`.
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
- Profiles and user data: `D:\Documents\My Games\OpenMW\` - `dev\`,
  `play\`, `saves\Faig\TEST1.omwsave`, `screenshots\`. **This has moved
  once already.** It used to be `D:\Backups\OneDrive\All\Documents\...`, where
  OneDrive had redirected Documents; by 2026-09-14 the folder was at
  `D:\Documents` and every build failed with `FileNotFoundError` on the
  old `openmw.cfg`. Neither location is `%USERPROFILE%\Documents`. Do not guess
  the path - ask Windows: `[Environment]::GetFolderPath('MyDocuments')`.
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
  `tes3conv.exe`, and launch the game and look at it (section below).
- **Claude Code on the web (Linux container)** - has the repo and the three
  masters in `tools/input/`, but no OpenMW install, no `resources/lua_api` to
  check API calls against, and cannot run the two `.exe` tools. **Do not
  reason about API surfaces from here** - defer that work or ask.

**Claude Code on Windows may launch the game** (the user lifted the old
"never" rule on 2026-09-15). The web container still cannot - it has no OpenMW
install - so from there the user runs it and brings back `logs/openmw.log`.

**Local AI tools from `E:\AI-models`** (moved from `D:\Work\AI models` to the SSD on 2026-09-17) are registered for this repo in
`.mcp.json` (both files are gitignored, they hold local paths):

- `game-control` - mouse and keyboard only inside an allowed, foreground
  `openmw.exe` window; PAUSE is the user's kill switch. Screenshots are saved as
  files in `D:\AI-Workspace\screenshots` - look at the files. If more than one
  game window is open, pin the right one with `game_target` (the pid rule
  below still applies).
- `local-workers` - local models for drafts, reviews, summaries and
  `local_look` (a local model describes a screenshot).

Who does what between Claude and the local models is written in
`E:\AI-models\CLAUDE.md`, section "Распределение ролей", and in
`E:\AI-models\ИНСТРУКЦИЯ для сессий Claude - локальные модели.md`. Read them before
delegating anything.

## Claude can run the game and look at it `SETTLED 2026-08-30`

**Launch it skipping the menu, straight into `TEST1`.** Faig asked for this to
be the default, and the save loads in about twenty-five seconds:

    Start-Process "D:\Program Files\OpenMW 0.51.0\openmw.exe" -ArgumentList
      '--replace config --config "<play profile>" --skip-menu --load-savegame
       "<...>\saves\Faig\TEST1.omwsave"'

**Never redirect the game's output.** With `-RedirectStandardOutput` that same
load ran fourteen minutes and never finished. Read the profile's `openmw.log`
instead. This one cost an hour.

Two ways to see the result, and both need the window **in the foreground and
actually rendering** - that was the whole of the earlier trouble, not the
capture method:

- `tools/scripts/grab.ps1 -Target <pid> -Front` reads the window off the
  screen. One window, nothing else, read-only.
- **F12 in the game**, sent with `SendInput`, and OpenMW writes a full
  2.5 MB PNG into `<user data>\screenshots`. This is the better picture.

`minimize on focus loss = false` is set in the play profile. Without it the
window parks itself off screen the moment anything takes focus, which is what
used to put the start menu in Faig's own screenshots. `settings.cfg.bak` undoes
it.

Faig runs a second session of this project in parallel, and its game is a
different copy. **Always pass `-Target <pid>`**; without it the first version
grabbed his other window.

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
- **`AddTopic`, `Journal` and `PlaceAtPC` take no `player->` prefix.** With one
  the console prints `warning: Stray explicit reference` in red and then runs the
  command anyway, which looks like a failure and is not. `AddItem` and `AddSpell`
  do want it. Seen 2026-08-29.
- **To read a book**, click it once in the inventory, carry it - button
  released - onto the player's portrait, and click again. Faig, 2026-08-30.
- **The console key is the backtick, left of 1, without Shift.** Faig sometimes
  plays over AnyDesk from a phone, where the on-screen `~` is Shift+backtick
  and the Russian layout turns the key into `ё`; neither opens the console.
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
