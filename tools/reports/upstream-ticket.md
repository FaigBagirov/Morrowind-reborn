# Upstream ticket, ready to file

Target: https://gitlab.com/OpenMW/openmw/-/issues — feature request.

This is **the strong half only**. *Conversion Architecture* Part 12 route 3 says
never to combine it with the dialogue-write request: read-only access to
dialogue was a deliberate design decision, and pairing a "please reconsider your
design" ask with a "please finish an existing pattern" ask lets the first sink
the second. File the dialogue one separately, later, or not at all.

Everything below is measured on OpenMW 0.51.0, not recalled.

---

## Title

Lua load context: expose `armors`, `weapons`, `clothing` and `creatures` in `openmw.content`

## Body

### Summary

The Lua load context exposes 15 record stores as mutable data. Armor, weapon,
clothing and creature records are not among them, and there is no other context
from which those records can be modified. A mod that renames existing items —
a total conversion, a translation, a themed overhaul — can reach books, spells,
ingredients, potions, GMST strings and magic effects, but not a single piece of
equipment or a single creature.

### What 0.51.0 exposes

Enumerated at runtime rather than read from documentation. `openmw.content`
holds 16 keys, 15 of which carry `.records`:

```
activators  books   doors    enchantments  gameSettings  globals
ingredients lights  magicEffects  miscs   potions  probes
sounds      spells  statics
```

There is no `armors`, `weapons`, `clothing`, `creatures` or `npcs`.

### The records exist and are readable — writes are refused

From a `GLOBAL` script, `types.Armor.records` and `types.Creature.records` are
live and readable. Assignment is rejected at the binding layer:

```
sol: cannot write to a readonly property
```

So this is not a case of "use the other API": there is no path to these display
names from any context in 0.51.0.

### Minimal reproduction

```lua
-- LOAD context
local content = require('openmw.content')
print(content.books ~= nil)     -- true, and content.books.records is writable
print(content.armors ~= nil)    -- false, the sub-package does not exist

-- GLOBAL context
local types = require('openmw.types')
print(types.Armor.records['daedric_cuirass'].name)  -- reads fine
types.Armor.records['daedric_cuirass'].name = 'x'   -- sol: cannot write to a
                                                    -- readonly property
```

### Why this looks small

The pattern already exists on both sides of the gap:

* **Read access** to records of all object types landed under
  [#6727](https://gitlab.com/OpenMW/openmw/-/issues/6727), which is closed;
  armor, weapon and clothing are on its checklist.
* **Record creation** for Activator, Armor, Clothing, Misc and Weapon landed in
  [!2944](https://gitlab.com/OpenMW/openmw/-/merge_requests/2944), and 0.51.0
  added container, creature, door, probe and static creation at runtime.
* **Mutable stores** in the load context already work for books, spells,
  ingredients and others.

What is missing is the intersection: mutating *existing* records of types whose
data is already exposed and whose creation is already supported. The request is
to expose an existing store through an existing pattern, not to design anything
new.

### Why a plugin is not a substitute

It is the current workaround and it is a poor one. A Morrowind plugin overrides
a record **whole**, not field by field. Renaming a cuirass in a plugin discards
whatever mesh and icon another mod set on the same record, silently and with no
warning — the later plugin simply wins. Measured against a 694-plugin mod list,
our own rename plugin would collide with a retexture mod on 12 equipment records
for no reason other than that both must rewrite the whole record to change one
field each.

The load context has none of that problem: it edits one field in memory after
every content file has loaded, so it composes with any load order by
construction. That property is exactly what makes the gap worth closing.

### Use case

A sci-fi total conversion of Morrowind that renames one term family across the
game. 115 of the affected record-fields are reachable from the load context
today. 496 are not, and they are the ones the player actually sees on screen:
equipment names, creature names, dialogue.

### Not part of this request

Writes to dialogue records (`INFO` response text). `openmw.core.dialogue` is nil
in the load context and read-only elsewhere, and that appears to be deliberate
rather than an oversight. Filed separately if at all.
