# Check card — the mod in the real load order

Profile: `play`. Backup of the untouched config is `openmw.cfg.bak` beside it;
restoring that file undoes everything. **Copy a save before you start, and do
not save while testing** — two of the checks move the main quest on.

On the first load OpenMW will say the plugin list does not match the save.
That is normal when any mod is added. Continue.

---

## 1. The visuals — the only genuinely unknown part

Everything else has been seen on screen already. This has not.

    player->AddSpell "fireball"
    player->AddSpell "summon flame atronach"
    player->AddSpell "light"

Cast each one and watch the particles.

* **Fireball** uses `vfx_particle064` and is the fastest read - a burst, gone.
* **Summon flame atronach** is the important one. Summoning runs about a
  second, so the shape is legible: this is where the hexagons either read as
  machinery or read as noise.
* **Light** is slow and lingering, which shows what a single plate looks like
  when you can stare at it.

What to look for, in order of importance:

1. **Do the plates read as made rather than as dirt?** Six sides, a bright rim,
   a dim middle. If they read as smudges the texture is too soft.
2. **Do the threads hold the cloud together?** They are what separates a swarm
   from dust. You asked for them a touch stronger; this is where that is judged.
3. **Does anything flicker or vanish at distance?** Cast, then back away. There
   is a faint core in the texture for exactly this; if it still flickers the
   core needs raising.
4. **Colour.** Fire should still be warm, frost still cold. The colour is
   sampled from Vurt's own textures, so if a school looks wrong that sampling
   is wrong.

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
