# Morrowind Next-Gen Installation Guide (Sci-Fi Base)

*Revised August 2026.*

This step-by-step guide will help you assemble a modern, stable version of Morrowind with excellent graphics and the necessary mechanics, while keeping the original lore clean for future AI overhauls.

## Step 1. Base Game and Engine Preparation

1. **Original Game:** Buy and install **The Elder Scrolls III: Morrowind Game of the Year Edition** (on Steam or GOG).
   * *Important:* Run the game once through the official launcher to the main menu and exit to register registry keys.
2. **OpenMW Installation:**
   * Download the latest engine version from the official site: openmw.org
   * **Minimum version: 0.50.** Current stable release is **0.51** (June 2026). Do NOT use 0.48 — most of the Lua combat mods in Step 4 will refuse to start on it, and 0.49 introduced animation blending which the combat section depends on.
   * Install the program. On the first launch, the OpenMW wizard will ask for the path to the `Morrowind.esm` file in your Steam folder. Provide it.
   * *Note on upgrades:* saves made in a newer version cannot be loaded in an older one, so pick your engine version before starting a long playthrough.

## Step 2. Graphical Foundation (Graphics Overhaul)

Since you do not have a Nexus Mods Premium subscription, we will install a compact but beautiful graphics base without altering the lore or adding new lands.

1. Go to **Modding-OpenMW.com**.
2. Navigate to the **Modlists** section and select **Graphics Overhaul** (or **I Heart Vanilla** for the fastest start).
3. **Do not download manually — use the automatic installer.** Grab the **MOMW Tools Pack** and run **umo**, which downloads, extracts and sorts an entire mod list for you. Without Nexus Premium it simply prompts you to click "Download" on each mod instead of fetching them silently; everything else stays automatic. The pack also bundles TES3CMD, Delta Plugin, S3LightFixes and OpenMW-Validator, all of which you will want later.
   * `umo sync graphics-overhaul` then `umo install graphics-overhaul`
   * Follow the **Automatic Installation Guide** on the site — it walks through the whole process, and the MOMW Configurator writes a correct `openmw.cfg` for you.
4. Key graphical mods to focus on:
   * **Morrowind Optimization Patch** (Smoothes blocky models and fixes collision meshes)
   * **Intelligent Textures** (AI-upscaled HD textures)
   * **MacKom's Heads / Robert's Bodies** (Detailed faces and bodies)
   * **MOMW Post Processing Pack** — replaces the old "Zesterer's shaders" advice. A single bundle containing XE-Shaders, OMWFX-Shaders, Zesterer's Volumetric Clouds, Zesterer's SSAO and Wareya's shaders. Add each subfolder as a separate data path.

## Step 3. Essential Fixes and QoL (Quality of Life)

* **Expansion Delay:** Critically important. Delays the Dark Brotherhood assassin attacks from the Tribunal expansion until your character is famous and high-leveled.
* **Graphic Herbalism (OpenMW version):** Makes plant harvesting instant, visually removing the harvested plant part.
* **Keyring:** Combines all found keys into a single inventory item to reduce clutter.
* **Big Icons / Modern UI Fonts:** Replaces small icons and pixelated fonts with crisp, high-resolution vector versions.
* ~~Ownership Indicator~~ — **no mod needed.** This is built into the engine: *Launcher → Settings → Interface → "show owned"*. Set it to colour the crosshair, the tooltip background, or both.

## Step 4. Gameplay, Combat, and AI Overhauls

These mods transform the outdated 2002 gameplay into a modern experience using OpenMW Lua scripts.

### 4.1. General Mechanics
* **Purist Friendly Magicka Regen:** Adds slow, balanced, real-time magicka regeneration (perfect for simulating battery recharge in a Sci-Fi setting).
* **Crafting Framework** or **Morrowind Crafting:** Allows forging weapons, armor, arrows, and cooking.
* **NPC schedules — pick exactly one of these three.** They all do the same job and will fight each other if stacked:
  * **Living Cities of Vvardenfell (LCV)** — the classic ESP-based option.
  * **Go Home!** — OpenMW Lua, by the MOMW team. **Not on Nexus** — it lives on GitLab under the `modding-openmw` group, and `umo` installs it as part of the MOMW lists. NPCs walk home at night or in bad weather; if they have no home they despawn out of sight. Extensive blacklists, and a debug mode under *Options -> Scripts* that logs which NPCs it took control of.
  * **(OpenMW) Lua NPC Schedule** — on Nexus. Does what Go Home! does plus daytime activity: NPCs go shopping and visit temples. The most complete of the three. On OpenMW 0.51 it no longer needs `go-home.omwaddon` for its weather logic.
* **Starfire's NPC Additions:** Adds travelers and patrols to the empty roads between cities.

### 4.2. Combat & Artificial Intelligence

**Install these one at a time and test in an actual fight after each one.** All of them are OpenMW Lua mods: unpack each into its own folder, add the folder under *Data Directories*, then tick its `.omwaddon` / `.omwscripts` files under *Content Files*.

#### 4.2.1. The core: N'Garde — Active Block and Parry

The single biggest change to how combat feels. **Requires OpenMW 0.50+.**

* Active shield block and weapon parry — for the player, for NPCs, and NPC vs NPC. The native random shield-block chance is switched off entirely.
* **Perfect parry:** a short window right after you raise your guard. Land it and all damage is negated and the attacker is staggered. Miss the window and you get a "weak" parry that still absorbs damage based on skill.
* Window length and effectiveness scale with the Block skill *and* the skill of whatever you are parrying with — shields are strongest, heavy weapons beat light ones, short blades are weakest.
* NPCs read your wind-up and parry with human-like reaction times. Low-skill or low-fatigue enemies parry less reliably and react slower.
* Stagger has a cooldown of 0.5–3.0 s scaled by Endurance, Strength and Block, so you cannot be stun-locked.
* Bare-handed blocking, plus "Iron Palm" — parry armed attacks with your fists at high Hand-to-Hand.
* Arrows can be blocked with shields; at very high weapon skill both you and NPCs can deflect arrows with a weapon.
* **Miss feedback:** 11 short bob-and-weave animations so a missed swing reads visually instead of passing through the enemy silently.

**Installation notes:**
1. Enable `ngarde.omwaddon` and `ngarde.omwscripts`.
2. In the launcher, enable **Use Additional Animation Sources**, **Smooth animation transitions** and **Smooth movement** (see Step 4.4). The last two prevent NPC jitter during parries.
3. In game: *Settings → Scripts → N'Garde* and assign a parry hotkey. If the key does nothing at first, save and reload.
4. Load N'Garde *after* other mods that add onHit handlers.
5. Safe to add or remove on an existing save.

> **This replaces "Manual Blocking".** N'Garde fully supersedes Shields Up and every other active-blocking mod — do not run two of them.

> **This also replaces "True Attack".** Instead of deleting the dice roll, turn on N'Garde's optional **Glancing Blows** mode: the vanilla hit chance is preserved, but a "miss" becomes a glancing hit dealing at most 20% damage and granting no skill XP. Time-to-kill stays roughly vanilla; what changes is that you always get feedback. Pick *either* Glancing Blows *or* a 100%-hit mod, never both.
>
> If you would rather keep pure vanilla hit chance, **Can't Touch This** is just the miss-feedback animations from N'Garde as a standalone mod.
>
> If you specifically want dice rolls gone, use **True Strike — Skill Scaling Combat (OpenMW)**: 100% hit chance, but weapon damage scales with skill (multiplier = 0.5 + 0.01 × skill), so a low-skill character is still bad at fighting. Far better balanced than the ancient `Accurate Attack` esp, which simply adds +1000 Attack to every race and trivialises the game.

#### 4.2.2. Optional additions (all playtested against N'Garde and Mercy)

* **Riposte** — a fast counter-attack window after a perfect parry, dealing armour-ignoring damage. Requires OpenMW 0.51.
* **Dash Dodge** — a dodge dash; also improves how NPCs reposition in combat.
* **Better Armor Training** — recommended alongside N'Garde: you get hit far less often, so armour skills stop levelling. This compensates.
* **Bullseye** — worth installing if you use the arrow-deflection feature. Load N'Garde *after* it.
* **Disarm Them All** — knock weapons out of hands. Load N'Garde after it.
* **Gothic Style Knockout** — non-lethal knockouts.
* **Dual Wielding**, **GRIP**, **Iron Fist**, **Take Cover**, **Maxar's Timed Attack** — all confirmed compatible.
* **Solthas Combat Pack (OpenMW Lua)** — a different design direction: charged attacks, timed directional attacks, dodge rolls, staves for spellcasters, every module toggleable. Overlaps with N'Garde in places, so test carefully rather than assuming it stacks.

#### 4.2.3. Difficulty and AI

* **Mercy: Combat AI Overhaul:** Drastically improves enemy AI in combat. NPCs will strafe, retreat, and humanoid enemies may even surrender and drop their weapons if their health is too low.
  * **Warning:** Mercy is incompatible with most other mods that directly drive NPC combat behaviour, unless they explicitly integrate with its interface. Do not stack a second AI overhaul on top of it. N'Garde and HBFS are both explicitly compatible.
* **HBFS (Harder Better Faster Stronger)** — reworks actor stats and, crucially, stops actors from running backwards while in a weapon stance. This kills the classic "backpedal and poke" exploit. Requires 0.49+, better on 0.50+.
* **Fair Care** — NPCs and creatures drink potions and cast healing on themselves and their allies. Noticeably raises difficulty; your own followers benefit too.

#### 4.2.4. Hit feedback

Morrowind gives you almost no information about what just happened in a fight. Either of these fixes that:

* **Hit Kill Feedback (OpenMW)** — floating damage numbers, miss notifications, screen shake, hit-stop, optional slow-motion on a kill.
* **Hit and Miss Percentage Indicators for Combat (OpenMW)** — floating indicators showing damage dealt or the hit-chance percentage of the swing. Requires 0.50+.

#### 4.2.5. Compatibility warning

**MWSE mods do not work in OpenMW at all** — these are two different engines. Popular combat mods such as *Combat Enhanced*, *Ashfall* and *Smart Ammo* are MWSE-only. On Nexus both kinds are listed side by side; filter by the **OpenMW** tag.
* **Passive Healthy Wildlife:** Makes normal animals (like mudcrabs or nix-hounds) peaceful or territorial. They will only attack if you get too close or if they are infected with the blight disease.
* **Protective Guards (OpenMW Lua):** Guards will actively protect the player and citizens by attacking any hostile NPCs or assassins they spot.
* **OpenMW Enhanced Stealth (Lua):** Ties stealth mechanics directly to light levels, distance, armor weight, and noise.

### 4.3. Combat Animations

Vanilla animations were built with no transitions between them, which is most of why swinging a sword feels wooden.

* **ReAnimation v2: Rogue (first-person animation pack)** — remakes the first-person combat animations, adds separate sets for short blades/daggers and bows, sneaking variants, and alternating attack animations for one-handers. Download the *OpenMW* file for 0.49+.
* **Third Person Alt-Attacks** (ReAnimation plugin) — extends the alternating-attack animations to third person.
* Both are what the N'Garde demo footage was recorded with, so they pair cleanly.

### 4.4. Launcher Settings (free, no mods required)

These cost nothing and change the feel of movement and combat more than half the mod list above. All are in **Launcher → Settings → Visuals**:

* **Smooth animation transitions** — engine-level animation blending, added in 0.49. Interpolates between every animation in the game. This alone removes most of the vanilla jerkiness, and it applies to modded animations too.
* **Smooth movement** — smooths NPC acceleration and turning.
* **Turn to movement direction** — characters rotate toward where they are actually moving.
* **Use Additional Animation Sources** — required by N'Garde and by most animation replacers.

Under **Settings → Interface**: `show owned` (see Step 3), and `show melee info` if you want weapon damage in tooltips.

## Step 5. Optics and Atmosphere

* **Project Atlas:** Optimizes thousands of architectural textures into single atlases to drastically boost FPS in large cities.
* **Dwemer Mesh Improvements:** Replaces ancient dwarven mechanisms and robots with high-polygon models (perfect for Sci-Fi atmosphere).
* **Weapon Sheathing:** Displays equipped weapons in sheaths on the belt or back.

### 5.1. OPTIONAL: Visuals
* **OMWFX Post-Processing Shaders:** The framework is built into the engine, but the shaders themselves are separate downloads (see the MOMW Post Processing Pack in Step 2). First tick **Enable post-processing** in the launcher, then press **F2** in game — that is the shader HUD, where you can toggle and reorder effects and tweak their sliders live. Try `Saturation`, `ColorLut` or `Bloom` to make colors vibrant and deep.
  * *Performance tip:* if you have the Morrowind Optimization Patch installed (Step 2), you can turn **transparent postpass** off in settings.cfg for a decent FPS gain.
* **Skies IV:** Replaces the muddy original sky with bright blue days, volumetric clouds, and vivid orange/purple sunsets.
* **Aesthesia Groundcover:** Covers the empty rocky wastelands with dense 3D grass and flowers.
* **Improved Thrown Weapon Projectiles:** Makes thrown weapons (like throwing stars and knives) physically rotate in the air during flight instead of remaining static.

## Step 6. Installation via Virtual File System (VFS)

**Never copy mod files directly into the original game folder (Data Files)!** OpenMW allows connecting mods from any folder.

1. Create a main folder for your mods on your drive, e.g., `C:\Games\OpenMW_Mods`
2. Create a separate subfolder for each downloaded mod. Example:
   * `C:\Games\OpenMW_Mods\Animation_Compilation`
   * `C:\Games\OpenMW_Mods\Weapon_Sheathing`
3. Extract the mod archives into their respective folders.
4. Open the OpenMW launcher and go to the **Data Directories** tab.
5. Click the **Append** button at the bottom and point to each of your mod folders one by one.
6. Go to the **Data Files** tab and check the boxes next to all new plugins (`.esp` or `.omwaddon`). Ensure `Morrowind.esm` is at the very top.

## Step 7. Water Physics and Settings

In the OpenMW launcher, under the **Graphics** and **Advanced** tabs:
* Enable **Water Shaders** and check the boxes for Reflections and Refractions.
* Enable dynamic shadows and set the shadow map quality to an acceptable level for your GPU.
* Enable **Distant Terrain** to remove the original fog.

## Step 8. Sci-Fi Conversion (Lore Rewrite Project)

> **This step is superseded.** The method below was the original sketch and is kept only for context. The current approach is documented in two companion files:
> * *Morrowind Sci-Fi Conversion — Architecture* — method, safety rules, work orders
> * *Morrowind Sci-Fi Conversion — Canon* — the setting and its rules
>
> Key deviations from what is written below: the master files are never converted or edited; text rewriting happens through the OpenMW 0.51 Lua **load context** rather than through plugins; and the model writes a deterministic transform script rather than performing substitutions itself.

Once the base is assembled and tested in-game, you are ready to rewrite the lore:
1. Download the **tes3conv** console utility.
2. Use your Antigravity agent to convert the necessary plugins into `.json` format.
3. Instruct the AI to find terms (Magic, Gods, Temple) and replace them with Sci-Fi equivalents (Nanites, Technologies, Corporations).
4. Compile the `.json` back into a plugin and load it last in the launcher list.

**Important caveats for this step:**

* **Lua mods are not plugins.** Everything in Step 4.2 lives in `.omwscripts` and `.lua` files, not in ESP records, so `tes3conv` will not see them and your rewrite pass will not break them. Conversely, any lore text they display (setting names, N'Garde's block skill description, Mercy's voice lines) will stay in fantasy terms unless you edit those files separately.
* **Version-control your plugins before rewriting.** Keep the original `.esp` alongside the converted one so you can diff them if the AI mangles a record.
* **Delta Plugin** (included in the MOMW Tools Pack) is the correct tool for merging record-level changes across plugins, rather than hand-editing conflicting ESPs.
* Run **OpenMW-Validator** (also in the Tools Pack) after recompiling to catch broken references before you start a playthrough.