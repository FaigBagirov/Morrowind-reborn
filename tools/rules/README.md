# The rules table

`naming.csv` is the whole setting change, as data. Nothing else in the project
performs a substitution, and no substitution exists outside this file — that
division of labour is *Conversion Architecture* Part 6, and the file format is
Part 14.

Validate and preview with:

```
python tools/scripts/check_rules.py
```

It refuses the table on any rule violation and writes a preview of every
substitution to `tools/reports/rules-preview.csv` without touching a game file.

## Columns

| Column | Meaning |
| --- | --- |
| `id` | Stable rule name. Appears in every report. Never reused. |
| `order` | Ascending, unique, total. Rules apply in this order and the order is data, not file layout. |
| `pattern` | Literal text to find. **Never a regular expression.** |
| `replacement` | Literal text to write. Never longer than `pattern`. |
| `applies_to_types` | `*` or a list of four-character record codes: `WEAP ARMO CLOT MISC BOOK SPEL INGR CREA CLAS INFO GMST`. |
| `applies_to_fields` | `*` or a list of `name text description value`. |
| `left_boundary` | `yes` requires a non-letter (or start of string) before the match. |
| `right_boundary` | `yes` requires a non-letter (or end of string) after the match. |
| `case_handling` | `mirror` or `literal`. |
| `exclude_records` | Record IDs this rule must skip, space-separated. |
| `notes` | Why the rule exists, and the measurement behind it. |

## `mirror` case handling

The replacement takes the case shape of the text it replaced:

| Matched | Written |
| --- | --- |
| `daedric ruin` | `zetic ruin` |
| `Daedric Ruin` | `Zetic Ruin` |
| `Daedric ruin` | `Zetic ruin` |
| `DAEDRIC RUIN` | `ZETIC RUIN` |

Anything the classifier cannot place — `DaEdRiC` — falls back to writing the
replacement literally **and is reported**. It is never guessed at.

`Ancient daedric Key` is a real vanilla item name, and mirror turns it into
`Ancient zenaric Key`. That preserves Bethesda's own inconsistency rather than
silently tidying it, which is the correct default; override it with a specific
rule if you would rather it read `Zenaric`.

## Boundaries

`left_boundary` on `aedra` is the rule the whole table is ordered around. The
string `daedra` contains the string `aedra`; without the boundary the transform
turns every `Daedra` in the game into `DZenad`, mechanically and identically.
*Shared World Canon* Part 10, `SETTLED`.

Most rules carry a left boundary and **no** right boundary, deliberately. No
right boundary is what makes one rule cover a family: `Daedric ruin` also
catches `ruins`, `Daedra` also catches `Daedra's` and `daedra-worshipper`.

## The three senses of "Daedric"

The word carries three unrelated meanings in the vanilla text, not two. Counted,
not guessed — the collocations behind every rule are in the `notes` column:

1. **Made by them** → `Zenaric`. Equipment, materials, artefacts, their script.
   This is the default, rule `R300`, and everything not caught earlier lands
   here.
2. **Of their cult** → `Zetic`. Ruins, shrines, sites, cults, worship, standing
   stones. Rules `R100`–`R160`. Numerically the largest group: `Daedric ruin`
   alone is 109 occurrences.
3. **The beings themselves** → `Zenar`. Servants, lords, princes, forces,
   messengers. Rules `R200`–`R270`, all marked `PROPOSED` — *Shared World Canon*
   Part 10 defines two adjectives, not three, so this group is an extension
   awaiting sign-off. It coins no new word: the beings are Zenar, so a Zenar
   servant is a servant who is one of them.

## Adding a rule

Measure first. A rule that fires zero times is a defect under Part 14, so a
collocation belongs in this table only after it has been counted in the masters.
The preview reports every occurrence that reached the `R300` default, which is
where the next rule's evidence comes from.
