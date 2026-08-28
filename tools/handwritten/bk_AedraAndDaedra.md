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

## The text

Two files beside this one, in the exact bytes the records will carry - ASCII,
vanilla markup, CRLF:

* `bk_AedraAndDaedra.txt` - 1,987 bytes, 1,796 characters of prose.
* `bk_Aedra_Tarer_Unique.txt` - the same, plus one line in Tarer's hand.

### The hook comes first, and the page measurement second

A Morrowind spread holds about **880 characters of prose** - calibrated against
`bk_darkestdarkness` in the Gate 3 screenshot, where the last visible line of
the first spread sits at character 882.

The first draft put the turn past that break, which was the real danger: since
the opening deliberately reads like the vanilla book, a reader who did not click
Next would have seen only the book he already knew and closed it.

Trimming fixed the symptom. Faig's instruction fixed the cause - **name the new
word on the first page and promise the answer**, rather than hoping the reader
turns a page for a payoff he does not know is there:

> A third word belongs on that list and is not on it. Zenar. Who bears it, and
> why you have never heard it, I shall come to.

That lands at character **200** - the third sentence, unmissable, before the
familiar definitions begin. The book now announces on sight that it is not the
one the reader remembers, and the rest is a countdown rather than a gamble.

With the promise made, the page break costs nothing. The turn falls at 895 and
the spread ends mid-theology, on Bethesda's own line about Lorkhan and the
moons. The reader is not being asked to guess whether there is more; he was told
there is.

### The shape

0. **The hook**, third sentence, at character 200. The word, and a debt:
   *Where it comes from, and why it has not reached you, I will come to.*
1. **The vanilla definitions**, cut to the two lines that carry meaning.
2. **The hinge.** *They do not measure the thing. They measure us.* Then the
   image the book turns on: **kinship is no property of the creature. It is a
   hand held out, or held back.**
3. **The theology as consequence of that gesture**, in four short sentences.
   *What is bound to the world may be killed. What is bound to nothing can only
   be sent away.* Bethesda's own Lorkhan line sits inside it, and the
   world-making claim stays a Dunmer belief rather than an assertion, which is
   what keeps *Shared World Canon* Part 0 intact.
4. **Three words.** *Elegant. Very old. Nobody thought to ask them.*
5. **The witnesses, as fragments.** *A hermit nine years silent. A wise woman
   who answered in the plural. A smuggler who lied about everything else.* No
   sentence explains why any of that matters. The argument is the distance
   between them: *They have never met. Their accounts do not differ by a word.*
6. **`Zenar` and `Zenad`.** One letter, and they are careful with it.
7. **The Temple's reasoning**, ending on the word that indicts it: *and you may
   do as you like with it, and sleep.*
8. **The last two sentences, which belong to no one in the book.** *They have
   not corrected us. I no longer think they mean to.*

The scholar's self-commentary is gone. Every line he used to spend explaining
his own discomfort now belongs to an image or to silence.

## Three decisions, all made on one criterion: does the player get there

1. **Length: 1,938 bytes**, and the shape matters more than the number. The
   first page names `Zenar` and promises to explain it; everything after that
   is paced rather than rationed.
2. **Title stays `Aedra and Daedra`.** The surprise depends on the reader
   believing he already knows this book - a new title throws that away, and
   costs the topic links in the title besides.
3. **Tarer's copy gets the marginal note.** One line, and it teaches the same
   lesson from the other side:

   > I have met one. He did not correct me when I said Daedra. He waited to see
   > whether I would correct myself. -- T.B.

   It costs nothing, it makes one more reader who knew, and a player who finds
   both copies gets a small discovery for noticing.

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

## Still to do

The transform does not yet emit authored records. These two need a path onto
the plugin side: read the .txt, override the BOOK record whole, keep everything
else in it untouched.
