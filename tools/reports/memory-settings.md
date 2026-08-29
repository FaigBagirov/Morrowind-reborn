# Running out of memory at Vivec exterior — what to change, and in what order

## What was actually measured

2026-08-29, loading a save standing in the Vivec **exterior** on the `play`
profile, 240-odd plugins, the `graphics-overhaul` list:

| | |
| --- | --- |
| `openmw.exe` private bytes | **12.9 GB** |
| working set | 8.06 GB |
| system RAM free | **0.7 GB of 15.9 GB** |
| CPU over a 15-second sample | **unchanged, 50.8 s** |
| `Responding` | **False** |

The flat CPU is the diagnosis. A process that is computing burns CPU; a process
that has stopped moving while the machine has 0.7 GB free is waiting on the
memory manager. This is exhaustion, not a hang in our code.

**Our contribution is about 50 MB** — 36 particle textures at 1.4 MB, plus a
1.6 MB plugin and a handful of Lua. Today's change to 1024 DXT5 did not move
that number: the file is 1,398,256 bytes where the 512 uncompressed one was
1,398,228. So the conversion is not the cause and cannot be the cure.

The same session **loaded the Vivec Fighters Guild interior without trouble** —
2.0 GB working set, 3.6 GB private, responsive throughout. The exterior is the
problem, and specifically the largest exterior scene in the game.

## What has not been measured

Which setting costs what. Everything below is ordered by expected RAM saved per
unit of visual loss, from the OpenMW 0.51 defaults and what each setting does —
not from a measurement of this machine. **Apply one tier, load the same Vivec
exterior save, and the process can be watched while it loads.** That turns this
list into evidence.

Read out of `defaults.bin` (base64, decodes to the commented default config),
not recalled.

## Result: Tier 1 was enough

Applied 2026-08-29 and the same exterior loaded. From `logs/openmw-play.log`,
nine exterior cells over a fifteen-minute session, walked rather than
teleported:

    Vivec (2, -10)   Vivec (3, -9)          Vivec, Foreign Quarter (3, -10)
    Vivec, Redoran   Vivec, Hlaalu          Vivec, Foreign Quarter (4, -10)
    Vivec, Arena     Ascadian Isles (2, -9) Ascadian Isles (4, -9)

Spells cast, particles rendered, `Quitting peacefully.` Free RAM back to 8.5 GB
afterwards. **Tiers 2 and 3 were not needed and have not been applied** - the
three lines that cost nothing on screen were sufficient, so the visual settings
stay where Faig had them.

Which of the three did the work is still unmeasured. `preload exterior grid` is
the likely one, since it is the only one that scales with how heavy the
neighbouring exterior cells are, and Vivec's are the heaviest in the game - but
that is reasoning, not evidence, and all three were changed at once.

## Tier 1 — no visual cost at all

These change what is held in memory ahead of time, not what is drawn.

```ini
[Cells]
preload exterior grid = false
preload instances = false
preload cell cache max = 12
```

* **`preload exterior grid`** (default `true`) preloads the eight neighbouring
  exterior cells as you approach a cell border. In Vivec, with Beautiful Cities
  of Morrowind on top, those are eight of the heaviest cells in the game, held
  for a border you may not cross. Cost: a brief hitch when you do cross one.
* **`preload instances`** (default `true`) — the shipped comment is explicit:
  "results in higher memory usage proportional to the number of cells that are
  preloaded". Cost: cell transitions take slightly longer.
* **`preload cell cache max`** (default 20) is how many cells stay cached. 12 is
  the floor, since `preload cell cache min` is 12.

If this alone fixes it, nothing on screen has changed.

## Tier 2 — small visual cost, and aimed at Vivec specifically

```ini
[Shaders]
maximum light distance = 8192
max lights = 32

[Water]
rtt size = 1024
```

* **`maximum light distance`** is at **16384**, twice the default. Vivec is
  thousands of lanterns, and doubling the radius multiplies the number of lights
  every object has to consider. Cost: distant lights fade out sooner.
* **`max lights`** is at **64** against a default of 8. Cost: only visible where
  more than 32 lights reach one object at once.
* **`rtt size`** is at **2048** against a default of 512 — sixteen times the
  pixels, for a reflection *and* a refraction target. Vivec is a city built on
  water, so this is where it is paid. Cost: reflections slightly softer.

## Tier 3 — visible, only if Tiers 1 and 2 are not enough

```ini
[Water]
reflection detail = 3

[Groundcover]
rendering distance = 4096

[Navigator]
max tiles number = 512
```

* **`reflection detail`** at 5 reflects everything including actors; 3 keeps
  terrain and statics. Cost: people stop appearing in the water.
* **`rendering distance`** (default 6144) — grass fades sooner. Little grass in
  Vivec; this one is for the rest of the island.
* **`max tiles number`** (default 1024) caps resident navmesh tiles. The disk
  cache is **1.6 GB** and every tile that gets used is held in RAM. Cost:
  possible pathfinding hitches for distant NPCs.

Also available and not recommended yet, because each costs real quality:
dropping `ssao_hq` from the post-processing chain, `number of shadow maps` back
to 3, and `object paging active grid = false`.

## Two things outside OpenMW

* **The pagefile.** With 12.9 GB committed on a 16 GB machine, the pagefile is
  what stands between a slow frame and a frozen process. Worth checking that
  Windows is managing it and that it lives on a fast drive. That is a system
  setting and is the user's to change.
* **Load an interior save when testing the conversion.** Every check on the card
  works indoors, and indoors the machine has 12 GB of headroom. The Vivec
  exterior is a separate problem that predates this mod.

## Reverting

`settings.cfg` sits beside `openmw.cfg` in
`My Games\OpenMW\play\`. Copy it to `settings.cfg.bak` first; restoring that file
undoes everything here.
