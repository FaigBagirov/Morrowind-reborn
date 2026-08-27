# Morrowind Sci-Fi Conversion — Architecture & Safety Rules

Companion document to the *Morrowind Next-Gen Installation Guide*. Kept in English to match that guide and to be fed directly to Claude Code as project context.

**Scope:** how to rewrite Morrowind's lore, magic system and casting visuals into a nanite/alien-technology setting without destroying the game. This document is about *method*, not content.

---

## Part 1. The One Rule That Matters

**Never change a record ID. Change only what the player sees.**

Every ESM/ESP record has an internal identifier (RefId) and, separately, human-readable fields. The identifier is referenced by MWScript code, dialogue filters, leveled lists, cell object references, quest state and journal indices. The display text is referenced by nothing.

| Safe to rewrite | Never touch |
| --- | --- |
| Object names (FNAM) | Record IDs / RefIds |
| Book and scroll text | Script bodies (SCPT) |
| Dialogue responses (INFO text) | Script variable names |
| Journal entry text | Dialogue topic IDs (see Part 5) |
| Class, faction, birthsign descriptions | Cell IDs used as script targets |
| Spell and magic effect names | Sound and mesh filenames |
| GMST strings (UI labels, school names) | Faction/rank internal IDs |

A naive find-and-replace across a converted JSON dump hits both columns. That is the single most likely way this project dies — and it dies *slowly*, with failures surfacing twenty hours into a playthrough, far from the change that caused them.

---

## Part 2. Never Modify the Master Files

Do not edit `Morrowind.esm`, `Tribunal.esm` or `Bloodmoon.esm`.

The moment a master file is forked, every patch and mod that expects vanilla records is operating against a file that no longer matches. Patch for Purists, the MOMW lists, Tamriel Rebuilt — all of them assume vanilla masters.

All changes live either in a separate plugin or, preferably, outside the plugin system entirely (Part 3).

---

## Part 3. Two Architectures — Both, With a Measured Line Between Them

> **Settled by Work Order 0, run 2026-08-21 and confirmed on screen.** This
> part originally said "pick the second one". The spike established that the
> second one cannot carry the rewrite on its own — item names, creature names
> and dialogue have no writable surface in the load context at all. Both
> architectures are now in use and the line between them is fixed by what 0.51
> exposes. Read *Result* at the end of this part before designing anything;
> the two option descriptions are kept because their trade-offs are still real.


### Option A: `tes3conv` JSON round-trip — now carries the dialogue and the equipment

Convert plugin → JSON → edit → convert back.

* Works on any OpenMW version.
* Produces a real plugin, so it can be shared.
* **But:** conflicts with any other mod touching the same records, requires careful load-order and merge handling, bloats fast, and must be re-run every time a dependency updates.

### Option B: OpenMW Lua **Load context** — now carries the books and the small records

Introduced in OpenMW 0.51. Scripts in this context run once, immediately after all content files are loaded, and receive the loaded records as mutable data. Records injected this way are not serialised into save games.

Why this is the right tool for a lore rewrite:

* **No load-order war.** Rules apply on top of whatever is loaded, in any order.
* **No save contamination.** Nothing is baked in; disabling the script reverts the game.
* **Covers mods automatically.** A rule matching "Daedra" catches text from mods you have not read.
* **Survives mod updates.** Rules reapply at every launch.
* **Claude Code edits plain `.lua` text**, not multi-hundred-megabyte JSON.

Caveat: the context is marked work-in-progress upstream, so the API may shift between releases. Pin your OpenMW version during development.

~~**Which fields are actually writable is unverified.**~~ It is now verified. See *Result* below.

---

### Result: what Work Order 0 established `SETTLED`

Measured on OpenMW 0.51.0 (commit `f4bec414`) from the load context, by
independent readback from a GLOBAL script, and on screen. Full report:
`tools/reports/wo0.md`. Raw output: `logs/wo0-spike.txt`.

`openmw.content` exposes exactly 15 sub-packages with `.records`:

```
activators  books   doors    enchantments  gameSettings  globals
ingredients lights  magicEffects  miscs   potions  probes
sounds      spells  statics
```

| Writable from the load context | Not reachable at all |
| --- | --- |
| BOOK `text` — confirmed on screen | ARMO `name` — no `content.armors` |
| GMST value | CREA `name` — no `content.creatures` |
| SPEL `name` — confirmed on screen | INFO response `text` — `core.dialogue` is **nil** in this context |
| INGR `name` — confirmed on screen | (also absent: weapons, clothing, NPCs) |
| MGEF `name` | |

Three doors were tried and all are shut:

1. There is no content sub-package for armour, creatures or dialogue. The
   string `armors` does not occur in the 0.51 binary at all, and the 0.52-dev
   docs do not add it — this is not an oversight the next release closes.
2. `types.Armor.records` and `types.Creature.records` are live in a GLOBAL
   script and the docs call them read-only. That is enforced: assignment
   fails with `sol: cannot write to a readonly property`.
3. There is no display-time hook for names or tooltips. The UI is C++/MyGUI
   and never routes those strings through Lua, so the string cannot be
   intercepted at render time either. See `tools/reports/ui-hook.md`.

**Part 12's fallback condition has fired.** INFO text is not writable, so
Option A is not avoidable. The split is therefore:

| Route | Carries | Keyword hits (WO1) |
| --- | --- | --- |
| **Option B**, load context, `mod/*.lua` | Book text (336), spell names (12), book names (10), ingredient names (6), misc-item names (5) | 369 |
| **Option A**, plugin via `tes3conv` | **All INFO dialogue** (960), weapon names (23), armour names (14), creature names (6), class descriptions (1), clothing names (1) | 1005 |
| Neither — frozen by policy | DIAL topic ids (37), cell names (6) | 43 |

Counts from `tools/reports/wo1-keyword-occurrences.csv`, one hit per
record-field. Book *names* are placed on the Option B side because they share
a sub-package with book text; that specific field was never probed.

So **Tier A** (equipment and species renaming, Part 5) and **all of Tier C**
(hand-written dialogue) sit on the plugin side, with every load-order
consequence Option A lists. The load context keeps the books, which is where
the bulk of the *word count* lives even though it is a minority of the records.

Consequences to design around, none of them optional now:

* **Load order matters again.** The plugin conflicts with any other plugin
  touching the same records, and a plugin conflict is resolved per record, not
  per field — the last loaded wins the whole record. Use Delta Plugin for
  record-level merges (Part 10) rather than hand-editing.
* **The plugin is baked into saves.** Disabling it no longer cleanly reverts
  the game, unlike the load context. Keep known-good saves (Part 10).
* **The plugin does not cover mods you have not read.** Option B's "covers
  mods automatically" property is lost for everything on the plugin side. A
  mod adding new Daedric equipment ships it unrenamed.
* **One rules table with a `route` column, feeding two emitters.** The setting
  stays a single reviewable file (Part 6) and the route is a property of the
  record type, which is mechanical.
* **The plugin must be regenerated** when the masters or the mod list change;
  the Lua half reapplies itself at every launch.

Still open on the plugin side, worth settling before WO2: whether it is one
plugin or two — a stable hand-authored plugin for new entities such as the
nanite device, separate from a machine-generated text plugin that is safe to
delete and rebuild. The generated half will be large and will churn; mixing
hand-written records into it risks them on every regeneration.

---

## Part 4. Text Encoding

Morrowind stores text in a single-byte codepage: Windows-1252 for English installs, CP1251 for Russian ones. UTF-8 characters that look innocent will corrupt or fail conversion:

* Curly quotes `" " ' '` → use straight `" '`
* Em dash `—` and en dash `–` → use `-`
* Ellipsis `…` → use `...`
* Non-breaking space → use a normal space

**Prompt rule for Claude Code: replacement text must be plain ASCII only.** Add a post-processing assertion that rejects any output byte above 0x7F.

---

## Part 5. Dialogue Topic Highlighting

Morrowind links dialogue by scanning response text for the names of known topics. Rename a word in a response and the link to that topic silently dies; rename the topic itself and every existing reference to it dies instead. Nothing warns you — the conversation simply becomes unreachable.

### Policy: topic IDs are never touched `SETTLED`

**Decision: the DIAL record IDs stay exactly as they are. `Daedra` remains the topic under the hood.**

Rationale: the conversion must run *on top of* an arbitrary mod list, remain compatible with mods released in the future, and never diverge from the mainline game. Any mod that adds dialogue referencing the `Daedra` topic keeps working, because the topic it references still exists under that name.

This eliminates the entire hazard class described above. There is no atomic rename, no reference counting requirement, no silently broken branch.

**Consequence to understand:** a DIAL record has no separate display field — its ID *is* what the player sees in the topic list. So the topic list will read `Daedra`. This is not a compromise. Under the unreliable-narrator principle (*Canon* Part 7), the topic list is the player character's own list of subjects, phrased in the vernacular they learned it in. Locals say Daedra. The player learned the word from locals. It is correct.

### What this makes safe, and what it forbids

| Rename freely | Never rename |
| --- | --- |
| Item, armour and weapon names (FNAM) | DIAL topic IDs |
| Creature names (FNAM) | General dialogue response text |
| Spell and ingredient names | Greetings |
| Book text of *informed* sources | Journal entries |
| GMST strings | Voice-type records (all audio) |

The right-hand column is not a restriction — it is the unreliable narrator doing the work for you. Locals speak the local word everywhere, which is both free and correct.

### The one rule for hand-written lines

When rewriting an informed character's dialogue, **keep at least one literal instance of the original keyword in the text** so the topic hyperlink still fires. This is effortless in practice, because informed characters are usually talking *about* the word. Yagrum Bagarn's line opens with "Daedra. Not-our-ancestors." — the link survives untouched.

### Where the visible change actually comes from

If unreliable narrator is applied to everything, almost nothing is renamed and the player notices no difference. The felt change comes from a middle tier:

* **Tier A — always rename.** Manufactured objects and the species itself: `Daedric Cuirass → Zenaric Cuirass`, `Daedroth → Zenaroth`. High visibility, zero topic risk, and already required by the Rename Test in *Canon* Part 8.
* **Tier B — never rename.** The right-hand column above.
* **Tier C — hand-written.** Unique lines of informed characters, plus a small set of books.

Tier A carries the experience. A player who loots Zenaric armour and summons a Zenaroth while every priest in the game says "daedra" is reading a real signal: **the craft vocabulary is more accurate than the religious vocabulary.** Smiths who work the material know what it is; theologians never asked. This is true of the real world too, and it costs nothing to implement.

### Interior cells need checking, not assuming

For interior cells the ID *is* the displayed name, and cell IDs are referenced by doors and scripts. Any cell whose name contains a target keyword therefore falls under "never rename" by default. Work Order 1 reports them so the decision is made from data rather than guesswork.

### MRK files remain available

OpenMW 0.51 supports the topic-marking files from the Russian release, which override the keywords used for implicit highlighting. Under the current policy they are not needed — but they are the escape hatch if a displayed word ever has to differ from its linking key.

---

## Part 6. The LLM Writes Rules, Not Replacements

The three master files as JSON run to hundreds of megabytes. They do not fit in a context window, and processing them in chunks produces drift: `Xenari` in one file, `Ksenari` in another, a missed occurrence in a third.

Correct division of labour:

```
Claude Code  →  writes a deterministic transform script + a rules table
Script       →  applies every substitution, mechanically and identically
Claude Code  →  reviews a sample of the diff, refines rules, re-runs
```

The model is the author of the rules and the reviewer of the output. It is never the thing performing the substitution.

Rules table should be a single versioned file, roughly:

```
pattern | replacement | applies_to_fields | case_handling | notes
```

Keep it in git. Every change to the setting is a diff in one file.

### Length discipline

Morrowind record fields are not unbounded. IDs in particular are fixed-width, and overlong display names get truncated or overflow UI elements. Keep replacements at or below the length of what they replace, and add a rule-table check that flags any replacement longer than its pattern.

---

## Part 7. What the Rewrite Does *Not* Cover

* **Lua mod text.** Setting names, N'Garde's block-skill description, mod-added item names. Not in ESP records — needs separate handling.
* **Voiced lines.** Mercy's combat barks are ElevenLabs audio. Unfixable by text substitution; either accept them or disable that feature.
* **Textures and meshes.** Signage, book covers, the Daedric alphabet. *Fortunate accident:* the Daedric script reads perfectly well as an alien writing system with zero changes.
* **Sound effect names** referenced by scripts.

---

## Part 8. Magic Gating — Design Notes

Goal: spells require a worn nanite device.

### Mechanism

There is no clean "cancel the cast" hook in stable OpenMW 0.51 — spellcasting dehardcoding is still in draft. The working approach uses a vanilla mechanic instead:

A Lua script watches the player's equipment. When no qualifying device is equipped, it adds a permanent **Silence** ability to the player; when one is equipped, it removes it.

Apply it as an **ability**, not as a cast spell. Abilities are permanent, cannot be dispelled, and are not resisted by Willpower — a cast Silence would be resisted and could be dispelled, which defeats the gate.

### What Silence blocks, and what it does not

| Blocked | Still works |
| --- | --- |
| Casting spells | Potions |
| | Scrolls |
| | Enchanted items |
| | Abilities |
| | Powers |

This distribution is unusually convenient for a technology setting:

* **Enchanted items still working** reads as "manufactured tech functions on its own."
* **Potions still working** covers the story sections that hand you levitation — reskin them as nanite ampoules.
* **Scrolls still working** gives a fictional slot for single-use data-chips and a practical escape hatch if the player loses their device.
* **Racial and birthsign powers still working** is a leak in the gate. Frame it as inherited or congenital nanite endowment rather than trying to close it.

### Device design

Do not hardcode a single slot. Check a **whitelist of item IDs across all equipped slots** — ring, glove, robe, amulet may all qualify. This is trivial in Lua and buys you flexibility.

Slot trade-offs:

| Slot | Pros | Cons |
| --- | --- | --- |
| Ring | Two slots available | Consumes prime enchanting real estate |
| Glove/bracer | Visually reads as a device | Conflicts with armoured gauntlets |
| Robe | Free slot for most builds, worn over armour, highly visible | Hides pauldrons and greaves visually |
| Amulet | No armour conflict | Prime enchanting slot |

**No tiers.** `SETTLED` The device is a switch, not a ladder: it grants access to techniques the character has already learned, nothing more. Progression stays in skills, where vanilla put it. See *Canon* Part 13 for why a tiered design was rejected.

### Failure modes to plan for

* **Character creation.** A mage build is unplayable until the first device is found. Place one in Seyda Neen — Census and Excise office, or as a starting-kit item.
* **Loss of the device.** Theft, a disarm mod, an unequip during a scripted sequence. Keep scrolls working as the recovery path.
* **Magicka regeneration.** If regen is gated by fiction, gate it mechanically too, or the battery charges without a battery.

### Do not gate NPCs mechanically

Tempting for consistency; wrong in practice.

* A large fraction of ordinary Morrowind NPCs carry spells in their spell list, not just visible mages.
* Many casters are **creatures** — Daedra, undead, ash creatures — which cannot meaningfully wear clothing. Under an alien reframing this resolves itself: they *are* nanite constructs and need no device.
* Armoured casters (Ordinators, Buoyant Armigers) do not wear robes.
* Silencing NPCs breaks combat balance globally, breaks scripted fights, and interacts badly with combat AI mods.

**Gate the player. Solve NPC consistency through fiction and optional cosmetics** — hand devices to Mages Guild and Telvanni NPCs for flavour, treat the rest as having internal implants.

---

## Part 9. Casting Visuals — Three Tiers

Ordered by effort-to-payoff.

### Tier 1: Particle textures (do this first)

Casting effects are NIF particle systems, but the particle image is an ordinary DDS/TGA file. Replacing that texture with a hex-grid or nanite motif changes every cast in the game without touching a single byte of geometry. Highest payoff per unit of work in the entire project.

### Tier 2: Post-processing shader (right tool for grain)

OMWFX shaders are GLSL — plain text, well within what Claude Code writes reliably. OpenMW 0.51 exposes post-processing control to Lua, so a grain or scanline effect can be triggered on cast and faded out afterwards.

Useful 0.51 additions here: unattached visual effects can now be named, looped and removed; custom magic effect records can be injected through the load context; custom spells and enchantments can be created via the context or at runtime.

### Tier 3: NIF editing (do not automate)

Binary format, interactive tooling (NifSkope). Machine-generated NIFs get rejected by the engine's model validation. If geometry must change, do it by hand.

---

## Part 10. Working Discipline

1. **Git the entire mod directory** before the first transform. Every rule change is a reviewable diff.
2. **Keep originals alongside outputs** so any record can be diffed against vanilla.
3. **Use Delta Plugin** (MOMW Tools Pack) for record-level merges rather than hand-editing conflicting ESPs.
4. **Run OpenMW-Validator** after every rebuild to catch broken references before entering the game.
5. **Use `esmtool`** to dump and inspect individual records when verifying a transform.
6. **Test with a throwaway character.** OpenMW can spawn a test character directly into Seyda Neen.
7. **Change one system at a time.** Text pass, then magic gating, then visuals. Never two at once — you will not know which broke the save.
8. **Keep a known-good save from before each system lands.**

---

## Part 11. Prompt Rules for Claude Code

Paste into project instructions:

```
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
- Do not generate or edit NIF files.
- One system per change set. Report the diff summary before applying.
```

---

## Part 12. Work Order 0 — Load Context Spike `ANSWERED`

**The first thing built. Half an hour of work; it decides which architecture the project uses.**

> **Done.** Log run 2026-08-21, on-screen check reported afterwards. Report:
> `tools/reports/wo0.md`. Raw output: `logs/wo0-spike.txt`. The answer is in
> Part 3 under *Result*.
>
> The trigger condition below fired: **INFO text is not writable** — in fact
> `core.dialogue` does not exist in the load context at all, so the failure is
> harder than "read-only". Item and creature names are equally unreachable.
> Five of the eight probed fields do work: BOOK text, GMST, SPEL name, INGR
> name, MGEF name, each confirmed by two independent Lua contexts, and three
> of them confirmed on screen as well.
>
> **The on-screen check caught something the logs could not,** which is exactly
> why this part demanded it. The book whose `text` was overwritten renders as
> a *blank page* rather than showing the sentinel. The write landed — the
> vanilla text is gone — but the vanilla pseudo-HTML markup went with it. The
> rule that follows: book text is rewritten by substituting inside the
> existing field, never by replacing the field. See section 7 of the report.
>
> Everything from "The unverified assumption" down is kept as the record of
> what was asked and why. It is history now, not instruction.

### The unverified assumption

Part 3 recommends the load context on the strength of the upstream release note: scripts in this context receive the loaded records *as mutable data*. What that note does not say is **which fields of which record types are actually writable**.

The project needs three things to be mutable:

| Need | Record type | Field |
| --- | --- | --- |
| `Zenaric Cuirass`, `Zenaroth` | ARMO, WEAP, CLOT, CREA | FNAM |
| Dwemer records, rewritten books | BOOK | text |
| Informed characters' lines | INFO | response text |

**If INFO text turns out to be read-only, the architecture changes completely** and the project falls back to plugins via `tes3conv`, with every load-order conflict that implies. This must be known before anything is built on top of it.

### The spike

A load-context script that attempts to modify one field of each required type and logs the outcome — succeeded, failed, silently reverted. One item, one creature, one book, one INFO record. Nothing more.

Then launch the game and confirm with your eyes: did the item name change in the inventory, the book text on the page, the line in the NPC's mouth? **A write that succeeds in the log but does not appear in game is the failure mode worth catching**, and only a visual check catches it.

### Output

```
record_type, field, writable, persists_in_game, notes
```

That table determines the boundary: what goes through the context, and what has to be a real plugin record.

### A hybrid is certain regardless of outcome

Even in the best case, some things must be actual records in a plugin:

* The nanite device — a new item
* Custom magic effects, if any are needed

So the shape is fixed in advance: **a small stable plugin for new entities, plus the load context for bulk text rewriting.** The spike only establishes where the line falls.

### The risk this makes visible

The topic-ID policy (Part 5) was chosen for maximum mod compatibility and longevity. Sound reasoning — but the load context is marked work-in-progress upstream, and its API may change between engine releases. The risk did not disappear; it moved. **The mod will survive any mod list and may break on an OpenMW update.**

Accept it, for one specific reason: **load-context breakage is loud.** The script throws on startup and you know within two seconds. Broken dialogue branches are silent — discovered twenty hours in, not reproducible. Trading a silent failure for a loud one is always the right trade.

Practical consequence: **pin the engine version for the duration of development.** Update deliberately, with a test character run afterwards, never incidentally.

---

## Part 13. Work Order 1 — Dialogue Survey

**Runs after Work Order 0, before the rules table and before any text is written.**

Until this pass has run you do not know the size of the project. You cannot scope it, schedule it, or decide what is worth doing.

### Preconditions

* **Clean vanilla install.** Morrowind.esm + Tribunal.esm + Bloodmoon.esm, no mods. This is your baseline; run it again later against the full mod list to see what the mods added.
* **Read-only.** This pass produces reports. It modifies no game file. If the script can write to the data directory, it is written wrong.

### Target keywords

`daedra` `daedric` `daedroth` `aedra` — case-insensitive, matched as substrings so inflected forms are caught. The list is deliberately over-broad at this stage; narrowing happens after you see the hits.

### Required outputs

**1. Cast list.** Every actor with INFO records filtered by their own actor ID, sorted by count descending.

```
actor_id, actor_name, unique_info_count, total_words
```

This is simultaneously the cast and the estimate. The top of the list is your hand-written personalities; `total_words` is how much writing Tier C actually costs.

**2. Keyword occurrences by record type.**

```
keyword, record_type, field, occurrence_count
```

Record type must distinguish at minimum: DIAL (by dialogue type), BOOK, NPC_, CREA, SPEL, ALCH, INGR, ARMO, WEAP, CLOT, MISC, CELL, GMST, FACT, CLAS, BSGN.

This is what tells you where the work is. Expect the distribution to be lopsided — that lopsidedness is the plan.

**3. Topic inventory.**

```
topic_id, dialogue_type, info_count, contains_target_keyword
```

Under the settled policy these are never renamed. The report exists so that decision is auditable, and so you can see which topics informed characters will need to preserve a literal keyword for.

**4. Cell report.**

```
cell_id, is_interior, contains_target_keyword, referenced_by_script_count
```

Interior cell IDs are their displayed names and are referenced by doors and scripts. This report is the input to deciding each one case by case.

### Output format

CSV or JSON. Four files, machine-readable. **Not a prose report** — these are working tables that feed the rules table, not a document to read once.

### Suggested method

`tes3conv` the three masters to JSON, then walk the structure in Python. The full dump is large; stream it or process one record type at a time rather than loading everything. Cross-check counts with `esmtool` on a sample of records — if the two disagree, the walker has a bug in its field traversal, and finding that now is much cheaper than finding it after a transform.

### Definition of done

You can answer, with a number: *how many words does this project require me to write?* If you cannot, the pass is not finished.