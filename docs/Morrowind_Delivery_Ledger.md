# Morrowind Delivery Ledger

*Shared World Canon* Part 11: **a claim with no carrier does not exist.** Every
claim in the canon must be said or written by somebody inside the game, or it
reaches nobody and the conversion is two words removed with nothing put in
their place. Skyrim keeps such a ledger. This is Morrowind's.

The table is `tools/reports/delivery-ledger.csv`, one row per claim:

| Column | What it holds |
| --- | --- |
| `id` | stable row name, never reused |
| `claim` | the claim in one sentence |
| `source` | where the canon states it - *Shared World Canon* part, or *Morrowind Canon* part |
| `carrier_id` | the record: an INFO id, a BOOK id, or the artefact that carries it |
| `carrier` | who speaks it, or what it is |
| `where_in_game` | quest, place, topic, and the conditions under which it fires |
| `mandatory` | whether the player can miss the place. Rev 7, Part 11: **a load-bearing claim must live in the mandatory core** - optional places may deepen a claim, never carry it alone |
| `status` | in game / wording PROPOSED or NEEDS REVISION / partial / NO CARRIER / NOT IMPLEMENTED |
| `note` | what the row needs a reader to know |

Written 2026-09-19/20 by the text fork, on Faig's instruction. **It is a census
of what exists, not an invention of new text.** Sources: `tools/handwritten/`
and its manifest, the transform's own output, *Morrowind Canon* Part 6, and the
"Texts" section of `CLAUDE.md`. Where nothing carries a claim, the row says so.

**The maintenance rule: every new hand-written record adds a row here**, in the
same change set that adds the record. A record in `tools/handwritten/manifest.csv`
with no row in this ledger is the defect this file exists to catch.

## Where it stands, 2026-09-20

26 claims: **13 delivered** - two of them with the wording still open
(`NEEDS REVISION`) and two still `PROPOSED` - **2 partial**, **10 with no
carrier at all**, one of which is Skyrim's and not ours to carry, and **1
mechanic designed and never built**.

What is delivered rests on a small number of records: one hand-written book in
81 copies, three Caius Cosades replies in Balmora, the invented `Zenar` topic
with six informed voices, Vivec's monologue, Divayth Fyr's observation, one
Sleeper, one added paragraph in *The Firmament* - and two carriers that are not
text at all, the rename itself and the particle textures, which the player
reads and sees constantly.

## The gaps, worst first

1. **Corprus is a weapon and nobody says so** (`C14`, *Morrowind Canon* Part 3a).
   The claim recasts the whole main quest from a cure to a shutdown, and not one
   line in the game carries it. Divayth Fyr comes closest - "Not the disease" -
   and stops there. This is the largest hole in the ledger: the game's own plot
   is the thing the canon reinterprets, and the reinterpretation is unspoken.
2. **Azura and the prophecy** (`C21`, *Shared* Part 6). The prophecy is the
   spine of Morrowind and Azura appears at the end of it. The canon says she is
   an analytical input and the prophecy a forecast. No carrier. Ashlander wise
   women are the obvious mouths, and two of them already answer `Zenar`.
3. **The two Rev 7 claims have no carrier in this game at all**: the Zenad
   retooled their swarm, which is why the loss is permanent (`C17`), and what a
   soul gem holds (`C18`). Morrowind ships soul gems, Azura's Star and an
   enchanting economy, so the second has an obvious place and no text.
4. **The swarm's word sits in an optional line** (`C08`). Rararyn Radarys is a
   Sleeper in Balmora, and a player can finish the game without asking him
   about `Dagoth Ur`. Rev 7's rule 5 says a load-bearing claim belongs in the
   mandatory core. Either the word is not load-bearing - defensible, since
   nothing else depends on the player hearing it - or it needs a second carrier
   somewhere the player cannot miss. Faig's call.
5. **The magic gate was never built** (`C22`). *Architecture* Part 8 and
   *Morrowind Canon* Part 8 specify a Silence ability keyed to a whitelist of
   equipped item IDs, so that the player needs the Empire's device to cast.
   Nothing in `mod/` mentions it. This is the one row that is a mechanic rather
   than a text, and the only claim in the canon that the player would feel
   rather than read.
6. **The interface is only half converted** (`C11`). 290 arcane words are still
   in the engine's own voice: `Cast Cost`, "a magical shield", `Mage`,
   `College of Destruction`. The UI says Charge in one line and Cast Cost in
   the next.
7. **The Heart as a reactor** (`C15`) and **the Dwemer as reverse-engineers**
   (`C16`). Both are load-bearing for the setting and both rest on vanilla text
   that merely fails to contradict them. *Morrowind Canon* Part 5 drafted a
   Yagrum Bagarn line that states the Dwemer case, and it was never placed.
8. **The rest, in order of how visible the absence is**: the beast forms
   (`C23`), the elements as by-products of a job list (`C20`), racial capacity
   as trace density (`C25`), one medium and three routes (`C19`). Meridia
   (`C26`) is Skyrim's and is listed only so that the absence is a decision.

Deciding these is Faig's; naming them is this file's job.
