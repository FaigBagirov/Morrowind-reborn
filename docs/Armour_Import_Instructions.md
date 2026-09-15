# Инструкция по импорту брони - Armour import instructions

For Claude sessions. How to put a downloaded, rigged 3D suit into Morrowind
(OpenMW 0.51) in place of an armour set, without guessing. Written 2026-09-15
after the Ageless Armor import finally sat on screen. Everything here was
measured or read from the engine's source; the old route's failures are listed
so nobody repeats them.

Branch: `new-armor` (worktree `D:\Work\Morrowind reborn armor`). Never master
unless Faig says so explicitly.

---

## 1. What you need from the download

- **GLB (glTF binary), rigged and skinned.** One file with geometry, UVs,
  base-colour images, joints, weights and inverse bind matrices. Ask for GLB.
- A humanoid rig with recognisable bone names (`pelvis`, `spine_0N`,
  `clavicle_l`, `upperarm_l`, `lowerarm_l`, `hand_l`, `thigh_l`, `calf_l`,
  `foot_l`, `neck_01`, `head`). Other rigs: extend `TWIN`/`AIM` in
  `fit_suit.py` and `SLOTS` in `glb_bodyparts.py`.
- The licence. Record it in `CREDITS.md` before anything is published.

`.nif` is a family, not a format: only 4.0.0.2 is Morrowind.

## 2. The engine facts everything rests on

Read from OpenMW 0.51 source (`components/sceneutil/attach.cpp`,
`apps/openmw/mwrender/npcanimation.cpp`), not recalled:

1. Each biped slot hangs its bodypart under a named node of `base_anim.nif`:
   `Head`, `Neck`, `Chest`, `Groin`, `Right/Left Clavicle`, `... Upper Arm`,
   `... Forearm`, `... Wrist`, `... Hand`, `... Upper Leg`, `... Knee`,
   `... Ankle`, `... Foot`.
2. **Rigid part on a node whose name contains `Left`: the engine inserts
   scale (-1, 1, 1) between node and part.** The `Right` nodes are exactly the
   mirror of the `Left` ones composed with that scale (measured). So author a
   piece once, in the `Right` node's frame, and the engine makes the left one.
   Ignoring this is what made arms grow *up* from the shoulder for a whole day.
3. A `BoneOffset` node inside a rigid part moves it by its translation.
4. **Skinned part** (file contains a skeleton + NiSkinInstance): not attached
   to a node and never mirrored; shapes named `Tri <slot>...` are bound to the
   actor's bones by name. Vanilla cuirasses are all skinned.
5. An armour record only shows a slot it lists. Vanilla Daedric greaves have
   no `Knee`, gauntlets no `Forearm`: the naked body part is drawn there
   (bare brown knees). Add the slots (`bodyparts.EXTRA_SLOTS`).

## 3. The route (commands)

    set G=<path to model.glb>
    python tools/scripts/model_textures.py %G% --write --out tools/build/armour-vanilla/Textures [--zenar]
    python tools/scripts/fit_suit.py %G% --write --out tools/build/armour-vanilla [--paint]
    python tools/scripts/transform.py --profile vanilla --import-armour --write
    tools/bin/tes3conv.exe tools/build/scifi-rewrite.json tools/build/scifi-rewrite.esp
    powershell -File tools/scripts/fitcheck.ps1 [-LoadSeconds 55]

- `model_textures.py`: author's base colours as DDS (`zenar_body.dds`,
  `zenar_helm.dds`). `--zenar` recolours to the conversion palette. Faig chose
  the **original colours** on 2026-09-15.
- `fit_suit.py`: pose + cut + write + read-back check + preview
  (`tools/reports/suit-preview.png`, drawn by the engine's rules, both sides).
  Look at the preview before launching anything.
- `transform.py --import-armour`: bodypart records and repointed armour
  records. For the play profile use `--profile momw` and its out dir.
- `fitcheck.ps1`: dev profile, ToddTest, no sound, dresses the player,
  static camera front/side/back/side, 8 F12 shots, one sheet
  `tools/reports/fitcheck.jpg`, closes the game by pid.

## 4. How `fit_suit.py` places a piece

1. Model axes to game: `(-x, z, y)`; model Y-up facing +Z, game Z-up facing
   +Y, model left (+X) is game left (-X).
2. One global scale: Bip01 Head-to-foot height over the model's.
3. Pose into `base_anim.nif` rest pose. Mapped limb bones (clavicle, upper
   arm, forearm, hand, thigh, calf) are **swung, never twisted** onto the
   Morrowind bone direction; heads snap to Bip01 joint positions; unmapped
   bones (twist, deform, cloth, fingers) ride their nearest mapped ancestor.
   Vertices follow by the model's own weights. A-pose palms that faced down
   end up facing the thighs.
4. Slot = dominant joint, walking up the hierarchy for bones with no slot.
   Calf splits into knee/ankle at half height. Neck folds into chest; any
   helmet-primitive triangles go to the head (one sheet per shape).
5. Grow each piece one triangle ring into its neighbours (hides seams), write
   both facings (open shells otherwise show the room).
6. Local = inverse of the `Right` node frame, then inverse of the donor's own
   node chain (root node(s) + NiTriShape transform). Donors must be rigid and
   single-shape (vanilla naked body parts, Daedric pauldron/boot).
7. Read the written NIF back, compose as the engine does, stop if off by more
   than 1e-3.

## 5. Looking at the result

- **Diagnostic paint first** (`--paint`): each slot its own colour, right side
  warm, left cool, F-glyph grid (a mirrored piece reads backwards), emissive
  material so dark rooms and busy backgrounds do not matter. Left pieces get
  `_l` records only to carry the cool colour.
- **Several candidates in one launch**: put each on a different vanilla armour
  record covering the same slots (read slots with esmtool), not one restart
  per guess.
- **F12 is the truth.** game-control's window grab returned stale frames for
  minutes. `shot.ps1` presses F12; the dev profile writes screenshots where the
  log's `Screenshots dir:` line says (currently the old OneDrive path).
- **Mouse turns the character in the dev profile**, not the camera
  (`deferredPreviewRotation` differs from play). Idle orbit is cancelled by any
  input, F12 included. Use the static camera in `tools/viewer/`.
- **Console key does not arrive under a Russian layout.** Use
  `--script-run tools/viewer/equip.txt` instead of typing.
- Close the game as soon as a round is done, **by pid, never by image name**
  (Faig may have his own copy open). The game and a local model share 6 GB of
  VRAM: unload models before launching, look at screenshots after closing.
- Local vision model gives a first look only; it once called a helmet
  "simple, no horns" because the crop cut it off. Verify on a downscaled sheet.
- When Faig's opinion is needed, send the screenshots into the chat
  (SendUserFile); he may be away from the PC.

## 6. Things that went wrong before, and why

| Symptom on screen | Cause |
| --- | --- |
| Arms 30-70 % too high, fingers up, hands swapped | Pieces authored in `Left` node frames without the engine's X mirror |
| Torso a blade reaching the floor | Geometry put into a *skinned* donor with stale weights |
| Suit scattered, each piece its own size | Fitting to donor bounding boxes |
| 9 % of vertices missing, floor visible through torso | Bones with no slot dropped instead of inheriting the parent's |
| No helmet / no collar | Only the first skinned primitive was read |
| Holes showing the room | One-sided faces on open shells |
| Rebuild silently lost renames | The build scanned its own installed plugin |
| Bare knees, missing forearms | Vanilla records lack Knee / Forearm slots |
| Thigh lying across hips in a preview | Ignoring the NiTriShape's own transform |

## 7. Open

- Chest is rigid on `Chest`. If it separates from the body in motion, make it
  skinned: map the model's joints to Bip01 names, at most 3-4 weights per
  vertex, write NiSkinInstance/NiSkinData on the pattern of a vanilla cuirass,
  shape name `Tri Chest`. Blender (io_scene_mw) is the fallback; not installed.
- Only checked standing. Walk, run and combat poses are unverified.
- `build_armour_set.py` is superseded; delete it once `fit_suit.py` has served
  a second model.
