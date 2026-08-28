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

The text itself is `bk_AedraAndDaedra.txt` beside this file, in the exact bytes
the record will carry: ASCII, vanilla markup, CRLF line ends. 2,137 characters
against vanilla's 1,077 - about a page and a half in game, three screens of
reading.

It keeps the vanilla opening almost word for word, so a player who read this
book twenty years ago recognises it, and then it turns.

### The shape

1. **The vanilla definitions**, intact. `Aedra` is ancestor, `Daedra` is not our
   ancestors. Nothing to unlearn.
2. **The hinge, three sentences long.** *Read the two again, and mark what they
   measure. Not the thing. Us.* The reader is not told a secret; he is shown
   what he has been saying all along.
3. **The vanilla theology**, kept, because it is good and because the reveal
   needs something solid to stand against. The world-making claim is reported as
   belief - *are held to have made* - which is what keeps *Shared World Canon*
   Part 0 intact without the reader noticing a change.
4. **One line of turn.** *Elegant. And in all the centuries of it, no one
   thought to ask them.*
5. **The reveal, through witnesses nobody believed** - a hermit, an Ashlands
   wise woman, a smuggler. That is *Canon* Part 6's informed-source layer,
   named. Their independence is the argument: *They do not know one another.
   They agree.*
6. **`Zenar` and `Zenad`.** One letter, and they insist upon the letter. One
   people parted by an old quarrel - the Schism, seen from outside by a man who
   does not know he is describing it.
7. **The Temple's answer**, given by the priests themselves and set down
   *without improvement, for it is better than mine*. Call a thing kin and you
   owe it something.
8. **The last line.** *The word is not an error. It is a decision, and it is
   repeated every morning in every chapel on this island.*

The narrator never claims to have met one. He is a scholar who asked, was
answered, and understood more than he wanted to - which is the only voice that
can carry this without becoming a revelation scene.

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

1. **Length.** 2,137 characters, roughly double vanilla. The plugin route has no
   limit, and the pacing wants the room. Cut back if you would rather it fit on
   one page.
2. **Title.** Still `Aedra and Daedra`. Leaving it keeps the book recognisable
   on the shelf and keeps both topic words in the title.
3. **Tarer's copy** (`bk_Aedra_Tarer_Unique`) carries the same text today. Same
   replacement, or a marginal note in his own hand - one line, and one more
   reader who knew?
