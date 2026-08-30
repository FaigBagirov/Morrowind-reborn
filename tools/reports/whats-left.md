# What is left, measured

Faig asked what still reads as misleading or unfinished, and what is missing
before the game can be played and handed to a friend. This is the answer with
numbers behind it. The counts come from `tools/scripts/audit.py`, run over the
three masters with the rules table applied first, so everything here is what
survives the conversion rather than what it started with.

The audit files every player-visible string under one of two voices before
counting it, because the same word is a defect in one and the point in the
other. **The game in its own voice** - a game setting, an effect description, a
skill, a spell name - must be consistent. **A mortal speaking** - a book, a
dialogue line, a class biography - keeps the old words by design, *Shared World
Canon* Part 9.

## The good half: the rename is complete

| In the engine's voice | Occurrences |
| --- | --- |
| `daedra` family | **1** |
| `magicka`, `magika`, `spell points` | **0** |

The single hit is `sMagicDaedrothID`, whose value is `Daedroth_summon` - a
record ID, not display text, excluded on purpose because renaming it breaks the
summon. So there are **no misses**: nothing the game says in its own voice
still calls a Zenar a Daedra, and nothing still calls Charge magicka.

For scale, in mortals' mouths those words remain 174 and 173 times. That is the
design working, not a backlog.

## The visible half: 290 words the setting has no answer for

| Where | Occurrences | Records | Example |
| --- | --- | --- | --- |
| GMST value | 108 | 91 | `sCastCost` = "Cast Cost" |
| MGEF description | 101 | 54 | "This effect creates a magical shield around the subject's entire body." |
| SPEL name | 25 | 25 | "Restore Mage", "Detect Enchantment" |
| SKIL description | 15 | 7 | the seven schools: "mastery of the spell effects of the College of Destruction" |
| CLAS name | 9 | 9 | Mage, Enchanter, Battlemage |
| items and NPCs | 32 | 29 | "Spell Breaker", "Wizard's Staff", "Ice Witch" |

**This is the one thing a player will notice.** The interface says Charge and
Discharge, and then the same interface says Cast Cost, and the effect
description under it says the spell creates a magical shield. Half a sentence
in the new denomination, half in the old.

It is not a hard build. It is the same shape as the magicka pass - a rules
table, scoped to the engine's voice, leaving books and dialogue alone. The work
is not mechanical: it is deciding the words. `spell`, `cast`, `enchant`,
`Mage`, `College of Destruction` all need an answer that is not a thesaurus
substitution, and one of them - `scroll` - is a physical object rather than a
concept.

A separate 87 occurrences are religious rather than arcane - god, divine, holy,
soul, blessing, mostly spell names like Almsivi Intervention. Canon keeps the
Temple as a cult, so these are a judgement call and are listed here only so
that the judgement is made against a number.

## Three contradictions that are not vocabulary

1. **The voice mod says the old word out loud.** 181 of our 190 rewritten
   replies have a file in Voices of Vvardenfell, which finds audio by record id
   and never reads the text, so playback works and disagrees with the screen in
   95% of the lines we touched. *Architecture* Part 15; cheapest fix is that
   mod's own `greetingsOnly` setting.
2. **Eight strings live inside script bodies** - `MessageBox` and `Say` at the
   Vivec shrines and elsewhere. The ESM carries compiled bytecode beside the
   text, the rules freeze script bodies, and no transform can reach them.
   Permanent, small, listed in `wo1-script-strings.csv`.
3. **Daedric weapons and shields were never restyled.** The armour is
   white-and-gold ceramic and the dai-katana beside it is still black and red.
   `tools/reports/armour.md` records why - no specular map exists for them in
   this load order, so it is a different tuning problem, not an oversight.

## To play it: nothing is missing

Everything is built and confirmed on screen. Installing into a profile is one
plugin line, one script line and two data lines, and removing it is deleting
those four lines.

## To hand it to a friend: five things, none of them large

1. **There is no install document.** `CLAUDE.md` is a working handover, not
   something a friend can follow. A short README is the whole gap.
2. **The plugin is built against one load order.** `--profile momw` reads
   *this machine's* 240-plugin list so that other mods' work is carried
   forward. A friend with a different list needs a rebuild. `--profile
   vanilla` builds cleanly - measured today, 237 plugin records, the same as
   momw - so a friend on plain Morrowind is already served.
3. **`mod/` still carries the WO1 probe.** `wo1-bookname.omwscripts` and
   `mod/scripts/wo1/` rewrite a book's name to a sentinel. Measured: they are
   *not* in the play profile's content list, so nothing is wrong today - but
   they must not go into a package.
4. **The armour textures exist only for the momw profile**, because they
   repaint a mod's armour. A vanilla friend gets the particle conversion and
   the text, not the ceramic suit.
5. **Third-party work has to be credited before anything is published.**
   `CREDITS.md` is the register and it lives on the main branch.
