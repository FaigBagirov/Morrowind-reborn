# WO1 — working detail

Canonical headline numbers live in *Canon* Part 7. This file is the working
record: what the second pass changed, how each number was cross-checked, and
what is still open.

Run: `python tools/scripts/wo1_survey.py`, 2026-08-28, ~21 seconds end to end
including converting the three masters with `tes3conv`. Inputs `tools/input/*.esm`,
outputs `tools/reports/wo1-*.csv` and `wo1-summary.md`.

---

## The five defects the first pass carried, and what each was worth

**1. The cell report was empty by bug.** A `Cell` record holds its name in
`name`; the walker read `rec["id"]`, which does not exist on that record type,
so all 2,856 cells collapsed onto the key `""`. `is_interior` read the
top-level `flags` field, which is the record header and always empty here — the
interior bit is in `data.flags`. The lone `referenced_by_script_count=1231` was
the number of scripts containing the empty string, i.e. all of them.

Now: **1,423 named cells, 1,328 of them interior**, plus 1,433 unnamed exterior
cells which are not listed because they display their region name and have no
string of their own to rewrite. Six named cells carry a keyword, all of them
Ald Daedroth and its five interiors, all frozen by policy.

**2. It could not be re-run.** Inputs were hardcoded to a scratch directory of
a different tool. The script now takes paths, defaults to `tools/input/`, and
converts to `tools/cache/` with `tools/bin/tes3conv.exe` when the JSON is not
already there. `tools/cache/` is gitignored — 220 MB, regenerated on demand.

The dumps from the first pass did in fact survive in that scratch directory,
contrary to the note in CLAUDE.md, and both routes produce identical record
counts: 48,296 / 10,000 / 10,776. The conversion is faithful and the point is
moot now.

**3. The cast list was filtered by keyword, not by actor ID.** It kept an INFO
only if `speaker and has_kw`. Part 13 asks for every actor with actor-filtered
INFOs; Part 6 defines Tier C as "who knows", not "who says daedra".

Three numbers now, and they answer different questions:

| Selection | Actors | INFO | Words |
| --- | --- | --- | --- |
| Every actor-filtered line in the game | 1,111 | 16,225 | 473,221 |
| Every line of an actor who says a keyword at least once | 80 | 3,099 | 113,613 |
| Lines that actually carry a keyword | 80 | 208 | 10,645 |

The middle row is the one to plan against. The bottom row is what the transform
touches; the middle row is what has to be *read* for the rewrite to stay
consistent, because an actor whose one line changes still has fifty that must
not contradict it. The top row is the ceiling, not a target.

**4. `occurrence_count` was one hit per record-field.** It now counts matches,
and `unique_record_count` is a new column beside it. The gap is real: 452
occurrences of `daedric` sit in 402 records; in BOOK text specifically, 182
occurrences sit in 160 books.

**5. No cross-check.** Done, below.

Plus the two rules items: `aedra` now carries a left word boundary
`(?<![A-Za-z])aedra`, and the field map is an explicit per-record-type table
(`DISPLAY_FIELDS`) instead of a blanket name/text/description sweep — which is
what had made GMST strings invisible, since a GMST's string lives in
`value.data`.

---

## Cross-checks against esmtool

Four checks, all against `esmtool dump` on `tools/input/*.esm`.

| Check | esmtool | Survey |
| --- | --- | --- |
| Total INFO records in the three masters | 36,954 | 36,954 parsed |
| SPEL names carrying a keyword | 12 | 12 |
| `Ald Daedroth` interior flag | exterior; five sub-cells interior | same |
| INFO records per actor, top of the list | see below | see below |

The per-actor check is the one that found a real bug. esmtool counts 17,425
INFO records with an `Actor:` filter; the survey reported 16,038. Per actor:
Falco Galenus 309/309 and Gentleman Jim Stacey 174/174 agreed, but Eno Hlaalu
was 231 against 113 — half his dialogue missing.

Cause: **INFO ids are not globally unique.** Morrowind.esm alone reuses 211 of
them, and the survey was merging records across the masters on the id alone, so
unrelated lines that happened to share an id collapsed onto each other. An INFO
is identified by its parent topic together with its id. Fixed, and the count
went to 16,225.

The residual gap against esmtool is exactly the expansion overrides, verified
record by record: Eno Hlaalu 229 + 2 overridden = 231, Artisa Arelas 217 + 3 =
220, Caius Cosades 172 + 5 = 177, Nileno Dorvayn 160 + 0 = 160. 3,299
topic+id pairs are defined in more than one master; every one of them spans
files rather than repeating inside one, which is what an override looks like.
esmtool counts each file's copy, the survey keeps the last, as the engine does.

## Reconciliation with the first pass

The old rules replayed over unmerged records reproduce the published figures
exactly — **227 records, 82 actors, 11,502 words** — so the new script is a
strict superset of the old behaviour and the whole difference is accounted for:

| Step | Records | Actors | Words |
| --- | --- | --- | --- |
| First pass, as published | 227 | 82 | 11,502 |
| `aedra` word boundary applied | 224 | 80 | 11,419 |
| Cross-master overrides merged | **208** | **80** | **10,645** |

Only **three** INFO records matched on the phantom `aedra` alone, and they cost
two actors their place on the list. The phantom mattered enormously for the
keyword *counts* — 338 claimed occurrences in INFO text against 22 real ones —
and barely at all for the cast list, because those records nearly all said
"daedra" too.

---

## What the numbers say now

Distinct records carrying at least one keyword, by route:

| Route | Record-fields | Where |
| --- | --- | --- |
| Plugin via `tes3conv` | 496 | INFO text 455, WEAPON name 21, ARMOR name 14, CREATURE name 4, CLASS description 1, CLOTHING name 1 |
| Lua load context | 253 | BOOK text 227, SPELL name 12, MISCITEM name 5, BOOK name 4, INGREDIENT name 3, GMST value 2 |
| Frozen by policy | 57 | SCRIPT text 32, DIAL id 19, CELL name 6 |

Counted per record-field, so a book with a keyword in both its title and its
text appears in two rows.

Tier A, the name fields: **64 records**. The `~65` in Canon Part 7 was right.

Concentration in the keyword-bearing dialogue is as reported before and still
convenient: top 10 actors hold 42% of the keyword words, top 30 hold 70%,
median 84 words, and 43 of the 80 have exactly one keyword line between them
(2,591 words).

The head of the list is unchanged and still lands where the fiction wanted it —
Sinnammu Mirpal (23 keyword records / 1,103 words), Lalatia Varian (9/601),
Smokey Morth (15/559), Garothmuk gro-Muzgub (8/428), Vala Catraso (12/389).

Caius Cosades is explained. Canon Part 7 called 3 records and 195 words
implausible for his role and used it as evidence the survey was wrong. It was
not wrong about him: he really does say the keywords twice, for 135 words. His
dialogue load is 172 records and 8,878 words, and that is the number his role
predicted.

## Two findings that are new

**Player-visible text lives in script bodies, and it is out of reach.** Eight
lines across the 32 keyword-bearing scripts are `MessageBox` or `Say` calls with
a keyword in the displayed string — the Vivec shrine plaques at Puzzle Canal and
Mount Kand, the Mehrunes Dagon summoning prompt, the Dregas Volar reward
message. Listed in `wo1-script-strings.csv`. Script bodies are frozen by the
rules, and the ESM carries compiled bytecode beside the text, so a text-only
edit would very likely not change what the player reads even if the rule were
lifted. **Not verified against the engine** — if this residue turns out to
matter, that is the thing to check first, and it is a C++ question, not a Lua
one.

**One of the two GMST hits must not be touched.** `sEffectSummonDaedroth` holds
`"Summon Daedroth"`, a display string, and is fair game. `sMagicDaedrothID`
holds `"Daedroth_summon"`, which is a **record ID**, and renaming it would break
the summon. The rules table needs a per-record exclusion for it, not just a
per-type rule — the first case found where a writable string field holds
something that is not display text.

## Still open

- BOOK `name` writability is still assumed, not probed. It carries 4 of the
  keyword records. Same caveat as in Architecture Part 12.
- Whether the script-body residue is truly unreachable, above.
- What Tribunal and Bloodmoon add on top of a Morrowind-only baseline is not
  broken out; the survey merges the three. Nothing currently depends on the
  split.
