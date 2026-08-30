#!/usr/bin/env python3
"""Give the imported armour to the game: bodypart records, and repointing.

A mesh sitting in a data directory is invisible. Morrowind reaches a worn piece
through two hops - an armour record names a **bodypart** per slot, and the
bodypart names the mesh - so an import needs a bodypart record of its own and
the armour record has to be told about it.

Both go in our plugin, which already invents records (the `Zenar` topic) and
already rewrites the Daedric armour records for their names. This adds the
bodyparts and edits one field of each armour record we were touching anyway.

## Why repoint rather than overwrite a mesh

Overwriting the mod's file was the alternative and it does not work here:
Daedric Lord Armor puts the whole worn body in one `DaedricArmorM.nif` with
eighteen shapes, and our writer replaces one. Repointing also keeps the change
inside the plugin, where removing one `content=` line undoes all of it.

## What the player keeps

Everything except the shape. The armour records are untouched apart from the
bodypart each slot names, so the name, class, weight, armour rating,
enchantment and value all stay exactly as the load order left them.
"""

import os

# Our pieces. The Morrowind part name has to match what the slot expects, and
# the mesh path is relative to a data directory's Meshes/.
PARTS = {
    "chest": ("zenar_chest", "Chest"),
    "groin": ("zenar_groin", "Groin"),
    "clavicle": ("zenar_clavicle", "Clavicle"),
    "upperarm": ("zenar_upperarm", "UpperArm"),
    "forearm": ("zenar_forearm", "Forearm"),
    "upperleg": ("zenar_upperleg", "UpperLeg"),
    "knee": ("zenar_knee", "Knee"),
    "ankle": ("zenar_ankle", "Ankle"),
    "foot": ("zenar_foot", "Foot"),
    "hand": ("zenar_hand", "Hand"),
}

# Hand was absent for a long time on a false premise: that a donor had to be a
# hand bodypart, and none of the twelve in the masters has a single shape for
# this writer to replace. The donor only supplies the node, the material and the
# texture reference - the bone decides placement - so any single-shape file with
# an identity transform serves, and the vanilla ankle does.

# An armour record names its slots as LeftPauldron, RightUpperArm and so on.
# Strip the side and this is what remains.
SLOT_OF = {
    "chest": "chest", "groin": "groin",
    "pauldron": "clavicle", "clavicle": "clavicle",
    "upperarm": "upperarm", "forearm": "forearm",
    "upperleg": "upperleg", "knee": "knee",
    "ankle": "ankle", "foot": "foot", "hand": "hand", "wrist": "hand",
}

# The armour this replaces. Daedric becomes Zenaric throughout the conversion,
# so these are the records whose shape should change with it.
TARGETS = {
    "daedric_cuirass", "daedric_cuirass_htab", "daedric_greaves",
    "daedric_greaves_htab", "daedric_boots", "daedric_pauldron_left",
    "daedric_pauldron_right", "daedric_gauntlet_left",
    "daedric_gauntlet_right",
}


def slot_of(biped_type):
    """Which of our pieces a slot wants, if any."""
    name = str(biped_type or "").lower()
    for prefix in ("left", "right"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return SLOT_OF.get(name)


def emit(mesh_dir="zenar", built=None):
    """A Bodypart record per piece we actually built.

    `built` is the set of slots with a mesh on disk. A record naming a mesh that
    is not there shows as nothing at all in game, which is a confusing way to
    fail, so only what exists is emitted.
    """
    out = []
    for slot, (rid, part) in PARTS.items():
        if built is not None and slot not in built:
            continue
        out.append({
            "type": "Bodypart", "flags": "", "id": rid, "race": "",
            "mesh": f"{mesh_dir}\\{slot}.nif",
            "data": {"part": part, "vampire": False, "flags": "",
                     "bodypart_type": "Armor"},
        })
    return out


def repoint(record, built=None):
    """Send one armour record's slots at our pieces. Returns how many moved."""
    if str(record.get("id", "")).lower() not in TARGETS:
        return 0
    moved = 0
    for biped in record.get("biped_objects") or []:
        slot = slot_of(biped.get("biped_object_type"))
        if not slot or slot not in PARTS:
            continue
        if built is not None and slot not in built:
            continue
        if not biped.get("male_bodypart"):
            continue          # an empty slot stays empty
        biped["male_bodypart"] = PARTS[slot][0]
        if biped.get("female_bodypart"):
            biped["female_bodypart"] = PARTS[slot][0]
        moved += 1
    return moved


def on_disk(root):
    """Which slots have a mesh built, so nothing points at a missing file."""
    return {slot for slot in PARTS
            if os.path.exists(os.path.join(root, slot + ".nif"))}
