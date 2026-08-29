# Check card — the mod in the real load order

Profile: `play`. Backup of the untouched config is `openmw.cfg.bak` beside it;
restoring that file undoes everything. **Copy a save before you start, and do
not save while testing** — two of the checks move the main quest on.

On the first load OpenMW will say the plugin list does not match the save.
That is normal when any mod is added. Continue.

---

## 1. The visuals — the shape is settled, the coverage is what is new

The shape passed on screen: `summon flame atronach` read as machinery, and you
approved it. What failed was **coverage** — six textures out of thirty-six, so
the next spell you cast came up vanilla. Now all thirty-six are converted, and
this list exists to catch any that did not take.

Every spell below is cheap, harmless and castable in a room. Paste the block,
then cast them in order and watch the hands.

    player->AddSpell "Ogrul's_Strong_Again"
    player->AddSpell "self dispel"
    player->AddSpell "sotha's grace"
    player->AddSpell "lock"
    player->AddSpell "fleabite"
    player->AddSpell "weariness"
    player->AddSpell "righteousness"
    player->AddSpell "fireball"
    player->AddSpell "frostball"
    player->AddSpell "shockball"
    player->AddSpell "light"

What each one is for. The count is how many magic effects share that texture, so
the top of the list is most of the game's casting:

| Spell | Texture | Effects | Should look |
| --- | --- | --- | --- |
| `Ogrul's_Strong_Again` | `vfx_bluecloud` | 28 | pale blue — the second biggest after the summons |
| `self dispel` | `vfx_particle064` | 9 | near-white |
| `sotha's grace` | `vfx_greenglow` | 4 | cyan-green |
| `lock` | `vfx_ill_glow` | 4 | violet |
| `fleabite` | `vfx_alpha_bolt01` | 5 | red |
| `weariness` | `vfx_map21` | 5 | orange |
| `righteousness` | `vfx_myst_flare01` | 5 | magenta |
| `fireball` | `vfx_firealpha00a` | 3 | hot orange |
| `frostball` | `vfx_icestar` | 1 | pale blue-white |
| `shockball` | `vfx_map39` | 2 | violet |
| `light` | `vfx_zen_light` | 1 | warm — **the one that may fail, see below** |

**The only thing to judge: does any of them still show a plain smooth glow?**
That is a texture that did not take, and the spell name tells us which. The
shape itself is already approved; nothing about it changed.

Colour is sampled from what you have installed, so each school keeps its own
light — fire warm, frost cold, poison green. If a school's colour looks wrong,
the sampling is wrong, not the shape.

### Light is the one deliberate risk

Light's effect record points at `tx_firealpha00a`, which is not a magic texture
at all — it is the flame sheet every torch, brazier and campfire in the game
wears. Overriding it would put hexagons on every fire in Vvardenfell to convert
one spell, so we do not. Instead Light's record is pointed at a private copy
from Lua, and **that write has never been proved to work in 0.51** — it was not
one of the WO0 probes.

It is guarded: if the engine refuses, Light keeps the vanilla flame and nothing
else is affected. Either way the answer is one line in the log —

```bash
findstr /c:"[REWRITE] light:" "D:\Backups\OneDrive\All\Documents\My Games\OpenMW\play\openmw.log"
```

To compare against what you had: delete the one line
`data="D:/Work/Morrowind reborn/tools/build/vfx-momw"` and Vurt's comes back.

---

## 2. Corprus, which should look damaged rather than dense

    player->AddSpell "summon daedroth"

Not the same thing as the corprus effect, but the closest thing you can cast at
will. The real Corprus texture appears on corprus victims and in the
Corprusarium; if you pass through Tel Fyr, look at a victim. Half its plates
should be missing a side or two. That is the distinction: same material,
damaged.

---

## 3. Nothing the mod list did was undone

This is the part that was built specially for your load order, and the part a
bare-masters build would have broken.

    player->AddItem "daedric_cuirass" 1

* Name reads **Zenaric Cuirass**.
* It still looks like the Daedric Lord Armor version, not vanilla. Both at once
  is the whole point of building against your load order.

---

## 4. The written text, now with 240 plugins under it

    player->AddItem "bk_AedraAndDaedra" 1

First page, third sentence: **Zenar**, and a promise to explain it. The page
should render normally - centred heading, Magic Cards face.

    player->AddTopic "Daedric summonings"
    player->PlaceAtPC "sinnammu mirpal" 1 1 1

* She has the topic **Zenar** and answers it.
* In her other replies the word **Zenar** is highlighted and clickable.
* Ask any passer-by about Zenar: the topic is not in their list at all. That
  silence is deliberate.

    player->PlaceAtPC "caius cosades" 1 1 1

Topic `little advice`. Two of its three answers now end by pointing you at a
wise woman and away from a priest. It is random which one you get, so ask a few
times.

---

## 5. The two late ones — these move the main quest, do not save after

    Journal B8_MeetVivec 50
    player->PlaceAtPC "vivec_god" 1 1 1

Topic `Dwemer's sin`. His confession ends "If we sinned, we have paid the
price" and continues straight into "I have told you what we did." Six
paragraphs, blank lines between them, "It is elementary." alone on its line.

    Journal A2_2_6thHouse 50
    player->PlaceAtPC "divayth fyr" 1 1 1

Topic `corprus disease`. After his joke about the Nerevarine being a fat corprus
monster, he should add what he saw in your blood.

---

## 6. The voice mod, which will now contradict the screen

Not a bug and not fixable today. Voices of Vvardenfell finds its audio by record
id, and we keep the ids, so it plays - saying "Daedra" while the text says
"Zenar" in 181 of the 190 replies we rewrote.

Listen to one and judge how much it costs. That decides whether regenerating
those 181 lines is worth doing later.

---

## If something is wrong

Restore `openmw.cfg.bak` over `openmw.cfg` and everything is exactly as it was.
Nothing else on disk was touched.
