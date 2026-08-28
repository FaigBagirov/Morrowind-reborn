# `bk_AedraAndDaedra` — hand-written replacement, DRAFT

**Status: draft for review. Not wired into the build.** The record is on the
frozen list (`tools/rules/frozen-records.csv`), so the transform leaves it
alone; nothing ships until this text is approved and emitted through the plugin.

## Why this record is hand-written and not substituted

It is the one place in the game where the mechanical rules produce a sentence
that is false in our own fiction. Run through the table, the vanilla text says:

> "**Zenar**" means, roughly, "not our ancestors." ... "Zenad" and "Zenar" are
> not relative terms. They are **Elvish and exact**.

Both claims break. `Zenar` is what they call themselves; it cannot also be the
Elvish word for *not ours*. And `Zenar` is not an Elvish word at all.

That is not bad luck. Explaining what a word means and replacing that word
everywhere are opposite operations, so the collision was guaranteed — and it
landed on exactly the book we want as the explainer.

## Where the player meets it

81 copies in 45 places. The nearest to the main quest is **Dorisa Darvel's
bookshop in Balmora**, the same town the player is sent to for Caius Cosades.
It is also stocked in the High Fane, the Hall of Justice Secret Library and
Holamayan Monastery — the Temple and the Dissident Priests both keep it.

## What the replacement has to do

1. Keep the book a **scholarly Imperial tract**, not a revelation. It is a
   lore book, and the reveal has to arrive as a scholar's footnote.
2. Keep the vanilla structure and most of the vanilla sentences. The player who
   read this book in 2002 should recognise it.
3. Teach the distinction the player needs: `Daedra` is a **mortal word about
   mortals** — a claim of kinship, or the refusal of one. `Zenar` is what the
   things themselves use.
4. Say why the Temple never adopted it, which is the political point and the
   reason the old word survives in every priest's mouth.
5. Keep the topic words `Aedra` and `Daedra` literally present, so the topic
   links still fire.
6. Stay inside *Shared World Canon* Part 0: no claim about the origin of the
   world, the nature of the soul, or what happens after death. The vanilla
   sentence about the Aedra creating the world is a **Dunmer belief reported by
   a scholar**, and it stays phrased that way.
7. ASCII only, and the markup preserved exactly.

## Draft text

Vanilla is 1,077 characters. This is 1,4xx — longer, which the plugin route
allows (the length rule binds replacements in the rules table, not authored
records). If it has to fit the vanilla length, the third and fourth paragraphs
are what to cut.

```
<DIV ALIGN="CENTER"><FONT COLOR="000000" SIZE="3" FACE="Magic Cards"><BR>
Aedra and Daedra<BR><BR>
<DIV ALIGN="LEFT"><BR><BR>
The designations of Gods, Demons, Aedra, and Daedra, are universally confusing to the layman. They are often used interchangeably.<BR>
<BR>
"Aedra" and "Daedra" are not relative terms. They are Elvish and exact. Azura is a Daedra both in Skyrim and Morrowind. "Aedra" is usually translated as "ancestor," which is as close as Cyrodilic can come to this Elven concept. "Daedra" means, roughly, "not our ancestors."<BR>
<BR>
The careful reader will note what these words describe. Not the things themselves, but our standing toward them. They are words of kinship, and kinship is a claim made by the speaker, not a property of the thing spoken of.<BR>
<BR>
This distinction was crucial to the Dunmer, whose fundamental split in ideology is represented in their mythical genealogy. Aedra are associated with stasis. Daedra represent change. The Aedra are held to have made the mortal world and to be bound to the Earth Bones; the Daedra, who cannot create, have the power to change.<BR>
<BR>
As part of the divine contract of creation, the Aedra can be killed. Witness Lorkhan and the moons. The protean Daedra, for whom the rules do not apply, can only be banished.<BR>
<BR>
It should be recorded, finally, that the subjects of this treatise do not use either word. The few who have spoken with them at length and been believed report that they name themselves Zenar, and that those we call Aedra are Zenad, which differs by a single letter and is meant to. They hold themselves one people, divided by an old quarrel rather than by kind.<BR>
<BR>
The Temple has never adopted these names, and its reasons are not scholarly. Call a thing kin and you owe it something. Call it not-kin and you may do as you please with it. The word does work, and that is why it has outlived every scholar who complained of it.<BR>
<BR>
```

## Notes on choices

* **"and been believed"** carries the whole Schism in three words. The
  informed-source layer in *Canon* Part 6 is people nobody believed; this is the
  book admitting the category exists.
* **"differs by a single letter and is meant to"** is the naming table's own
  logic (*Shared World Canon* Part 10) put in a character's mouth. The player is
  told what to notice rather than being expected to notice it.
* **"divided by an old quarrel rather than by kind"** points at the Schism
  without explaining it. The book is a lore tract by an Imperial scholar; he
  would not know more than that.
* The **Temple paragraph** is the political reading. Until now it lived only in
  our own documents and no character said it. Here it becomes something written
  in-world, by a scholar with an axe to grind, which is the right voice for it.
* The vanilla claim that the Aedra made the world is reported as belief - "are
  held to have made" - rather than asserted, which keeps Part 0 intact without
  the reader noticing a change.

## Open questions for Faig

1. **Length.** Fine to run longer than vanilla, or cut back to 1,077?
2. **Should the book name change?** It is currently `Aedra and Daedra`. Leaving
   it is the conservative choice and keeps the shelf recognisable.
3. **Tarer's copy** (`bk_Aedra_Tarer_Unique`) is the same text. Same replacement,
   or should his personal copy carry a marginal note in his hand - a cheap way
   to characterise one more informed reader?
