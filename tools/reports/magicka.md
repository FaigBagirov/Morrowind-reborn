# Magicka to Charge — measured, built, partly seen on screen

Faig asked whether the word could be renamed, and offered `power` or `charge`.
The survey answered a different and better question than the one asked, twice.

## What the game actually calls this resource

| Spelling | Occurrences | Records |
| --- | --- | --- |
| `magicka` | 259 | 178 |
| **`spell points`** | **41** | **41** |
| `Magika` — one k, a vanilla typo in `sSpellmakingHelp2` | 1 | 1 |

**There are two names, not one.** Bethesda renamed the resource during
development and left the old name in place: `sEffectRestoreSpellPoints` still
holds the string `Restore Magicka`, and 41 records still say "spell points" -
spells called `absorb spell points`, `curse spell points`, and one effect
description. A rename that matched only "magicka" would have left a second,
untouched term on screen, and nothing in the request hinted at it.

The typo is the same kind of trap in miniature. One record, invisible to any
rule that spells the word correctly.

## Two senses, and only one of them is Charge

| Sense | Examples | Records |
| --- | --- | --- |
| the resource | `sMagic`, Restore / Fortify / Damage / Drain Magicka, Magicka Leech | ~42 |
| **magic as a damage type** | Resist Magicka, Weakness to Magicka, Magicka Resistance, "damage from magicka-based attacks" | ~17 |

`Charge` is right for the first and wrong for the second: "Resist Charge" reads
as resistance to being charged. The second sense got its own rules and its own
word, **Discharge** - Faig's choice over the proposed Signal, and the better
one: your Charge against their Discharge is one idea, not two.

**`Power` was rejected on measurement, not taste.** `sPowers` and `sTypePower`
are both the string "Powers", the category header in the same magic window, and
20 spells are of that type. The player would have read "Power: 87/120" above a
list titled "Powers".

## Where the line falls, and why it is not a compromise

Renamed - the game speaking in its own voice: **59 records**, every one on the
Lua route. 14 game settings, 20 spell names, 15 potion names, 10 effect
descriptions.

Kept - mortals speaking: **121 dialogue lines and 39 book fields**. *Shared World
Canon* Part 9 keeps a word that is a mortal's interpretation, and "magicka" is
exactly that: the premise is that there is no magic.

Frozen regardless: 13 script bodies, 1 topic id.

The split is not a hedge. What the instrument reports and what people call it
differ, which is the same device as Zenar against Daedra. **Confirmed on screen**:
the stat sheet reads `Charge` while *The Firmament* still reads "magicka".

## A length rule replaced by a measured one

`Discharge` is two characters longer than `Magicka`, and the table refused it.
The rule was "no replacement longer than its pattern", which is a proxy: what it
protects is a name overflowing its widget, and whether a string grew is not the
same question as whether it fits.

So the proxy became the default and the real measure became the check. A rule
may opt out with `allow_longer`, and both the validator and the transform then
hold every string it produces to **the longest vanilla string already shipping
in the same record type and field**, measured off the masters.

18 strings grow. None exceeds its ceiling. Potion names are the tight one - 30
produced against 31 available, one character - and that is now a number rather
than a hope.

## Four defects the gates caught

Every one was found by a check rather than by looking, and every one would have
shipped.

**The generated Lua did not parse.** `absorb spell points [ranged]` is a spell id
ending in a bracket, and `[[...]]` around it makes `]]]`. The quoter only refused
when `]]` appeared *inside* the text.

**The rule scope never reached the Lua half.** `rules.lua` carried the pattern,
the replacement and the boundaries but not the record types a rule applies to,
so `apply.lua` ran every rule on every target. Invisible until the first scoped
rules arrived - and then the Lua half renamed magicka inside books while the
reports said books were untouched. Two halves describing different mods is the
one thing a shared rules table exists to prevent.

**The equivalence harness called `applyAll` with two arguments** where the game
calls it with four, so it had been testing an engine slightly unlike the shipped
one.

**The Lua half enforced "never longer than what it replaces"**, which would have
silently dropped all 18 strings that legitimately grow. It now carries the same
measured ceiling, emitted as data.

## Effect names are a separate mechanism, and it was wrong

Seen on screen: a spell called `Resist Discharge` whose effect line still read
`Resist Magicka`. An effect's name is not a field of any record - the engine
copies it out of a game setting before our script runs - so it has to be written
separately. That separate write was failing on eight targets.

**Six pointed at records that do not exist.** The effect id was made by cutting
`sEffect` off the setting's id, which works only where Bethesda's two names
agree. They do not here: `sEffectAbsorbSpellPoints` names the effect
`absorbmagicka`. Worse, the masters call one effect `FortifyMagickaMultiplier`
while OpenMW answers only to `fortifymaximummagicka` - the ESM id and the
engine's id are different strings for the same thing.

The id now comes from the setting's **value** - the display name, letters only,
lowercased - and is checked against the engine's own documented list before a
target is emitted. Validated: the rule holds for 139 of the 144 effect settings,
and the five it misses are two unused Bloodmoon placeholders, two renamed
summons and a menu label, all of which the check catches. Anything unmatched is
reported instead of emitted.

**Two were dropped for length**, because an effect name is not a field of any
record, so no value was ever measured for it and its ceiling stayed at zero. The
names live in the settings, so the ceiling comes from there: 27.

## One thing that stays unexplained

The first run with these rules showed `Magicka` on the stat sheet. The second,
with the same rules and only logging added, showed `Charge`. In between, a
readback logged from inside the load context returned `Charge` at the moment the
screen was showing `Magicka`.

I concluded from the first observation that a game setting written from the load
context never reaches the interface, said so with more confidence than one
observation earns, and was wrong. **It does reach it.** Why the first run did not
is not established, and guessing at it here would repeat the original mistake.

What the episode does establish is narrower and worth keeping: *Architecture*
Part 12's `GMST | writable` was measured by a Lua readback, not by the screen.
Those are different claims. The screen now supports the stronger one for the
stat sheet, and refutes it for effect names, which need the separate write above.

## Still to do

* Confirm on screen: the effect line reading `Resist Discharge`, the potion
  `Cheap Restore Charge` (**already seen**), and the Firmament's new paragraph.
* The interface will say Charge while effect descriptions still say "magic",
  "magical", "spell" and "cast". That is a separate and much larger question
  than the one asked, and it has not been touched.
