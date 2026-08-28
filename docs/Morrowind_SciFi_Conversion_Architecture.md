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

## Part 3. Two Architectures — Pick the Second One

### Option A: `tes3conv` JSON round-trip (the original plan)

Convert plugin → JSON → edit → convert back.

* Works on any OpenMW version.
* Produces a real plugin, so it can be shared.
* **But:** conflicts with any other mod touching the same records, requires careful load-order and merge handling, bloats fast, and must be re-run every time a dependency updates.

### Option B: OpenMW Lua **Load context** (recommended)

Introduced in OpenMW 0.51. Scripts in this context run once, immediately after all content files are loaded, and receive the loaded records as mutable data. Records injected this way are not serialised into save games.

Why this is the right tool for a lore rewrite:

* **No load-order war.** Rules apply on top of whatever is loaded, in any order.
* **No save contamination.** Nothing is baked in; disabling the script reverts the game.
* **Covers mods automatically.** A rule matching "Daedra" catches text from mods you have not read.
* **Survives mod updates.** Rules reapply at every launch.
* **Claude Code edits plain `.lua` text**, not multi-hundred-megabyte JSON.

**Superseded in part by Part 12.** The above was written before Work Order 0 ran. Measured result: the context reaches books, GMST strings, spells, magic effects, ingredients and nine other record types, and does **not** reach armour, weapons, clothing, creatures or dialogue. Read Part 12 before designing anything on this section.

Caveat: the context is marked work-in-progress upstream, so the API may shift between releases. Pin your OpenMW version during development.

**Recommended split:** Load context for all text substitution. A small conventional plugin only for things that must be real records — new items, new spells, new magic effects.

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

**No tiers.** `SETTLED` The device is a switch, not a ladder: it grants access to techniques the character has already learned, nothing more. Progression stays in skills, where vanilla put it. See *Canon* Part 8 for why a tiered design was rejected.

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
  original topic keyword so the topic hyperlink still fires.
- Consult Part 12 before proposing any write path. Armor, weapon, clothing,
  creature and dialogue records are NOT writable from Lua in 0.51. Do not
  design around them being available.
- Do not generate or edit NIF files.
- One system per change set. Report the diff summary before applying.
```

---

## Part 12. Work Order 0 Results — Load Context Writability `SETTLED, MEASURED`

**This ran. These are measurements from OpenMW 0.51.0, not predictions.** Everything in Part 3 is subordinate to this section.

### What the load context actually exposes

Enumerated at runtime, not read from documentation. `openmw.content` holds 16 keys, 15 of which carry `.records`:

```
activators  books   doors     enchantments  gameSettings  globals
ingredients lights  magicEffects  miscs     potions       probes
sounds      spells  statics
```

There is no `armors`, no `weapons`, no `clothing`, no `creatures`, no `npcs`, no `dialogue`. `core.dialogue` is `nil` inside the load context entirely.

### Results, ten probes

| Record type | Field | Write | In-game | Notes |
| --- | --- | --- | --- | --- |
| BOOK | text | **OK** | confirmed | see the HTML caveat below |
| BOOK | name | **OK** | confirmed | probed separately in WO1, 2026-08-28 |
| GMST | value | **OK** | changed* | strongest log evidence; readback via `core.getGMST`, unavailable to load scripts |
| SPEL | name | **OK** | confirmed | |
| INGR | name | **OK** | confirmed | |
| MGEF | name | **OK** | changed* | survives `esmfallbacks.lua` overwriting effect names from GMST |
| ARMO | name | fail | - | `NO_API_SURFACE` |
| CREA | name | fail | - | `NO_API_SURFACE` |
| INFO | text | fail | - | `core.dialogue` is nil in this context |
| ARMO from GLOBAL | name | fail | - | `sol: cannot write to a readonly property` |
| CREA from GLOBAL | name | fail | - | `sol: cannot write to a readonly property` |

The last two rows matter as much as the rest. `types.Armor.records` and `types.Creature.records` are live and readable from a global script, and the engine **refuses the write explicitly** through its binding layer. There is no runtime path to those names in 0.51 from any context.

\* **GMST and MGEF rest on a recollection, not a read-out.** The user recalls
that on the one spell they inspected every line of the tooltip had changed, but
not the exact strings. Those three lines are the spell name, the GMST section
header and the effect name, so nothing there still read its vanilla value —
which rules out the failure mode this check exists for. It is weaker than the
other three rows, and the `confirmed` that stood here earlier was written by a
Claude session, not observed. Both are two lines of one tooltip if ever
re-checked.

**BOOK `name` is now measured too.** The WO0 spike wrote BOOK `text` and never touched `name`, so the book's title in the inventory stayed vanilla during that in-game check — correctly, since nothing had been written to it. That left the field assumed rather than demonstrated. A separate probe closed it on 2026-08-28: written from the load context, read back from a GLOBAL script and from a PLAYER script in a live session, and seen renamed in the inventory. Nothing in the available column is an assumption any more.

### There is no silent-failure trap

Every failure is loud: a missing sub-package or a thrown error. Nothing was accepted and then discarded. This is the best available outcome for a negative result, because it means code either works or announces that it does not.

### Consequence for scope

Cross-referenced against the tiers in Part 5:

* **Tier C is fully available.** Books, GMST strings, spell names, magic effect names, ingredient names. The whole informed-source layer, which *Canon* Part 6 identifies as the substance of the project, can be built today.
* **Tier A is unavailable.** Armour, weapons and creature names, which Part 5 identifies as carrying the felt change, cannot be touched at runtime.
* **Hand-written dialogue is unavailable.** *Canon* Part 5 grumble lines and Part 6 informed characters cannot be delivered through Lua.

`Daedra's Heart` renames to `Zenar Heart`. `Daedric Cuirass` does not.

### Practical finding: books carry HTML, and substring substitution survives it

The vanilla target was 5403 characters beginning `<DIV ALIGN="CENTER"><FONT COLOR="000000" SIZE="3" FACE="Magic Cards">`. Writing plain text over the whole field succeeded at the data level and rendered as a **blank page**.

**Any book rewrite must preserve the surrounding markup.** This is a hard check in the rules table.

**The substitution rule that follows from it is measured, not assumed.** The WO1 probe rewrote the page-one heading of the same book in place — same length, markup untouched — and the page rendered normally: centered heading, Magic Cards face, pagination unchanged, the rest of the text intact. Screenshot check, 2026-08-28. So the transform's chosen method is known to work end to end on a real book, which is what the blank page left open.

One hazard the probe surfaced on the way, and it belongs to the transform rather than to books: **Lua's `string.gsub` treats its needle as a pattern**, in which `- . % ( ) [ ] + * ? ^ $` are all special, and it offers no plain-match flag. `string.find` does, as its fourth argument. A rules table full of ordinary prose — apostrophes, hyphens, full stops — is exactly the input that turns this into silent corruption. Every match and every substitution in the transform goes through the plain path.

### Three routes forward

1. **Load context only.** Zero conflicts, permanently. Tier A and dialogue never happen.
2. **Hybrid: a plugin for ARMO, WEAP and CREA names.** Morrowind plugins override a record whole, not field by field, so a rename plugin clobbers mesh and icon changes made by other mods to the same records. Delta Plugin merges field-wise, but the merge must be regenerated whenever the mod list changes. "Works on top of anything" becomes "works on top of anything, regenerate after changes."
3. **Upstream request.** Split into two, never one ticket. The strong half asks for `armors`, `weapons`, `clothing` and `creatures` in `openmw.content`: bindings for these record types already exist for record *creation* (MR !2944 for armor, clothing, misc, weapon; 0.51 for creatures and containers at runtime), so the ask is to expose an existing store through an existing pattern, not to build something new. The weak half asks for dialogue writes, and is weaker because read-only access there was a deliberate decision, not an oversight. Combining them lets the weak half sink the strong one.

Timeline discipline: seven months separated 0.50 and 0.51. Send the ticket, then proceed as though it will not land.

---

## Part 13. Work Order 1 — Dialogue Survey

**The first job. Runs before the rules table, before any text is written, before anything is renamed.**

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

---

## Part 14. Work Order 2 — The Rules Table and the Transform `SPEC`

**Runs after WO1, which is closed. This is the first work order that changes what the player sees.**

Everything before this measured the ground. This one puts weight on it. The failure mode that matters is not a crash — it is a substitution landing somewhere it should not have, inside one of 227 book texts nobody will read again before release.

### One rules table, two artifacts

The routing measured in Part 12 splits the output, not the input:

| | Records | Delivery |
| --- | --- | --- |
| Lua half | **115** record-fields — BOOK text 90, SPELL 12, MISCITEM 5, BOOK name 4, INGREDIENT 3, GMST 1 | a generated Lua data file, applied in the load context at every game start |
| Plugin half | 496 record-fields — INFO text 455, WEAP 21, ARMO 14, CREA 4, CLAS 1, CLOT 1 | a `tes3conv` plugin, merged into the list's Delta Plugin output |

The Lua figure is what the rules table actually rewrites, measured by the dry run — not the 253 record-fields WO1 counts as carrying a keyword. The gap is 137 book texts whose only keyword is the `FACE="Daedric"` font attribute and one GMST that is a record ID. Both are protected, and both are counted in the survey.

**Both are emitted from the same rules table by the same script.** Two emitters, one source of truth. If the halves can drift, they will, and the same word rendered `Zenar` in a book and `Zenaric` on a weapon is exactly the drift Part 6 exists to prevent — which no amount of reading either half alone will catch.

### Preconditions

* WO1's reports regenerated and current. The transform's target list is derived from the same walker, never typed by hand.
* **Input is the *effective* record set, not the bare masters.** Masters plus the active plugins, as the game resolves them. `tools/reports/momw-compat.md` measured why: a plugin generated from vanilla text would silently revert Patch for Purists' corrections in 27 dialogue records and strip the Daedric Lord Armor meshes from 12 equipment records. Against a clean vanilla profile the effective set is just the three masters, and the transform must not care which it was handed.
* Masters untouched, as always. The transform reads them and writes elsewhere.

**Profiles, because the mod must run on a vanilla install and on the mod list.**
`--profile vanilla` reads the three masters; `--profile momw` reads the
effective set. Everything else is shared: one rules table, one script, and a
**byte-identical Lua half**, which needs no variant because it substitutes into
whatever text is loaded. On the plugin side the equipment and creature renames
also need no variant - measured field by field, the graphics mods rewrite
`MODL` and `ITEX` and leave `FNAM` alone, so a field-wise merge keeps both. The
only records where the two builds genuinely differ are **thirteen dialogue
records** whose text Patch for Purists has corrected. Supporting both
configurations is a build flag, not a second mod.

### The rules table

One versioned file, `tools/rules/naming.csv`, reviewed as a diff. Columns:

```
id, order, pattern, replacement, applies_to_types, applies_to_fields,
left_boundary, right_boundary, case_handling, exclude_records, notes
```

* `order` — integer, ascending, **explicit and total**. Rules apply in this order, and the order is data rather than an accident of file layout. `daedroth`, `daedric` and `daedra` all precede `aedra`.
* `left_boundary` / `right_boundary` — booleans. `aedra` carries a left boundary and that is settled canon (*Shared World Canon* Part 10). Without it every `Daedra` in the game becomes `DZenad`, mechanically and identically.
* `case_handling` — `mirror` (the replacement takes the case shape of what it replaced: lower, Title, UPPER) or `literal` (written exactly as given). Anything the mirror cannot classify falls back to `literal` **and is reported**, never guessed at.
* `exclude_records` — record IDs this rule must skip. It exists because `sMagicDaedrothID` is a writable GMST whose value is the record ID `Daedroth_summon`, and renaming it breaks the summon. Per-type rules are not enough; this column is the reason.

### Rule semantics, all of them checkable

1. **Plain text, never patterns.** Lua's `string.gsub` treats its needle as a pattern and has no plain-match flag; Python's `re` offers the same hazard through a different door. Both emitters match literally — `string.find(..., true)` in Lua, `str.find` / `str.replace` in Python. The WO1 probe's own marker counted as zero occurrences of itself before this was fixed.
2. **A replacement is never longer than its pattern.** Checked per rule when the table loads, not per substitution at runtime.
3. **ASCII only, bytes 0x00–0x7F**, verified bytewise in Python. Never with `grep -P`.
4. **Substitute inside a field, never replace a field.** Book text is pseudo-HTML and the markup is load-bearing. Measured 2026-08-28: substitution in place leaves the page rendering normally; whole-field replacement renders blank.

4a. **Never substitute inside a markup tag.** Everything between `<` and `>` is a machine reference, not prose. `FACE="Daedric"` names a **font**, and it occurs 137 times across the masters; rewriting it points the page at a font that does not exist. This is the same trap as `sMagicDaedrothID` — a string that reads like display text and is not — and it is the reason the transform masks tag spans before matching rather than trusting the rules table to be careful. It also corrects the scope: of the 227 book texts WO1 counts as carrying a keyword, **137 carry it only in that font attribute**, and the real book workload is 90 records.
5. **Idempotent.** Running the transform over its own output changes nothing. This is a test, not an aspiration: `transform(transform(x)) == transform(x)`.
6. **Topic keywords survive.** When an INFO record is rewritten, at least one literal instance of the original topic keyword must remain or the topic hyperlink stops firing. Before and after counts are reported for every record touched.
7. **Deterministic.** The same input and the same rules file produce the same bytes. The report records the rules file's hash.

### The transform script

`tools/scripts/transform.py`. It applies rules and does nothing else. It has no opinions, contains no replacement strings of its own and holds no special cases — a special case belongs in the rules table, where it can be reviewed as a diff.

It must **refuse to run**, loudly, when: a replacement is longer than its pattern; any string in the table is not ASCII; two rules share an `order`; a rule targets a record type Part 12 measured as unreachable; or the target list disagrees with WO1's current reports.

The default is a **dry run**. Writing artifacts is an explicit flag.

### Required outputs

**1. Diff report**, one row per record touched:

```
record_type, record_id, field, rule_ids_applied, before, after,
length_delta, topic_keyword_before, topic_keyword_after
```

**2. Summary**: records touched and skipped, per rule, per type, per route. **A rule that fires zero times is a defect** — the pattern is wrong or the record list is stale — and the summary says so rather than leaving a silent zero in a table.

**3. Exclusion audit**: every record an `exclude_records` entry protected, and every record it would otherwise have hit. An exclusion that never fires is as suspicious as a rule that never fires.

**4. The artifacts**: the Lua data file into `mod/`, the plugin JSON for `tes3conv` into `tools/build/`.

### Verification, three gates, none of them optional

* **Gate 1, mechanical.** Idempotence, ASCII, length, keyword retention, determinism. Runs on every invocation.
* **Gate 2, review.** Claude reads a *sample of the diff* — the most-changed records plus a random draw — and refines the rules. Part 6 stands: the model writes rules and reviews output, and never performs a substitution.
* **Gate 3, in game.** The user runs it. **The log is not evidence on its own** — WO0's book write was accepted at every layer and rendered blank on screen. The first run checks at least: one rewritten book renders with its markup intact, one renamed item reads correctly in the inventory, and one rewritten INFO still hyperlinks its topic.

Testing convention: the user loads an existing save, so the check card hands its targets over by console command and never by location.

### Definition of done

The rewrite applies to a running game, the three gates pass, and the diff report accounts for every record WO1 says exists — each one either transformed, or excluded with a reason recorded in the table.

### What WO2 does not cover

* **The eight script-body strings.** `MessageBox` and `Say` calls at the Vivec shrines and elsewhere carry keywords the player reads. Script bodies are frozen, and the ESM carries compiled bytecode beside the text. Permanent residue, listed in `tools/reports/wo1-script-strings.csv`.
* **Hand-written text.** Canon Part 4's monologue, Part 5's grumble lines, Part 6's informed characters. Those are written, not substituted, and they are a separate work order.
* **Merging into the mod list.** Regenerating `delta-merged.omwaddon` is an install step, not a transform step. `tools/reports/momw-compat.md` carries the detail.
