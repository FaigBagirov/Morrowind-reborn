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
# Our pieces. The Morrowind part name has to match what the slot expects, and
# the mesh path is relative to a data directory's Meshes/.
#
# **Both sides, one record each.** The vanilla armour records fill only the
# right slots and let the engine mirror into the left. Mirroring negates an axis
# of the local coordinates, which is harmless for a vanilla part sitting on its
# own bone and ruinous for one carrying an offset: Faig's left leg vanished
# outright and his forearms were pushed towards the middle. Filling both slots
# takes the mirror out of the question.
# **One record per slot, both side slots filled with it.** This is the vanilla
# pauldron pattern: both Daedric pauldron records reference the same `_cl`
# bodypart and the engine mirrors it for the right slot natively. Building the
# right side myself through the rest pose put both pauldrons on the left - the
# game hangs parts on animated bones, and the rest pose is not what plays.
PARTS = {k: (f"zenar_{k}", v) for k, v in {
    "chest": "Chest", "groin": "Groin", "head": "Head",
    "clavicle": "Clavicle", "upperarm": "UpperArm", "forearm": "Forearm",
    "upperleg": "UpperLeg", "knee": "Knee", "ankle": "Ankle",
    "foot": "Foot", "hand": "Hand"}.items()}

# An armour record names its slots as LeftPauldron, RightUpperArm and so on.
# This turns one of those into the key above, side and all.
SLOT_OF = {
    "chest": "chest", "groin": "groin", "head": "head",
    "pauldron": "clavicle", "clavicle": "clavicle",
    "upperarm": "upperarm", "forearm": "forearm",
    "upperleg": "upperleg", "knee": "knee",
    "ankle": "ankle", "foot": "foot", "hand": "hand",
    # No wrist: it would draw the hand a second time on the wrist bone. The
    # vanilla records leave that slot empty and it stays empty.
}

# The armour this replaces. Daedric becomes Zenaric throughout the conversion,
# so these are the records whose shape should change with it.
TARGETS = {
    "daedric_cuirass", "daedric_cuirass_htab", "daedric_greaves",
    "daedric_greaves_htab", "daedric_boots", "daedric_pauldron_left",
    "daedric_pauldron_right", "daedric_gauntlet_left",
    "daedric_gauntlet_right",
    # All four helms. Faig asked for the fountain one by name, but the whole
    # Daedric set becomes Zenaric, so a player in any of them gets the set.
    "daedric_fountain_helm", "daedric_terrifying_helm", "daedric_god_helm",
    "daedric_helm_clavicusvile",
}


EXTRA_SLOTS = {
    "daedric_greaves": ("LeftKnee", "RightKnee"),
    "daedric_greaves_htab": ("LeftKnee", "RightKnee"),
    "daedric_gauntlet_left": ("LeftForearm",),
    "daedric_gauntlet_right": ("RightForearm",),
}


def slot_of(biped_type):
    """Which of our pieces a slot wants, if any. Sides share one piece."""
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
        # A `<slot>_l` mesh is the same piece in a left-side dress - the
        # diagnostic paint of `fit_suit.py --paint` - and gets its own record.
        for key, ident in ((slot, rid), (slot + "_l", rid + "_l")):
            if (key not in built) if built is not None else key != slot:
                continue
            out.append({
                "type": "Bodypart", "flags": "", "id": ident, "race": "",
                "mesh": f"{mesh_dir}\\{key}.nif",
                "data": {"part": part, "vampire": False, "flags": "",
                         "bodypart_type": "Armor"},
            })
    return out


def repoint(record, built=None):
    """Send one armour record's slots at our pieces. Returns how many moved."""
    ident = str(record.get("id", "")).lower()
    if ident not in TARGETS:
        return 0
    # Slots the vanilla record never had. Without them the naked body's knee
    # and forearm are drawn between our pieces - seen on screen as bare brown
    # knees above the boots - and our knee and forearm meshes are never worn.
    bipeds = record.setdefault("biped_objects", [])
    have = {str(b.get("biped_object_type")) for b in bipeds}
    for extra in EXTRA_SLOTS.get(ident, ()):
        if extra not in have:
            bipeds.append({"biped_object_type": extra,
                           "male_bodypart": "", "female_bodypart": ""})
    moved = 0
    for biped in bipeds:
        slot = slot_of(biped.get("biped_object_type"))
        if not slot or slot not in PARTS:
            continue
        if built is not None and slot not in built:
            continue
        # An empty slot is filled with the same piece. The engine mirrors
        # anything hung on a `Left` node, and `fit_suit.py` authors every
        # piece for exactly that. A `_l` mesh, when built, is the diagnostic
        # left-side dress of the same geometry.
        rid = PARTS[slot][0]
        left = str(biped.get("biped_object_type") or "").lower()
        if left.startswith("left") and built is not None \
                and slot + "_l" in built:
            rid += "_l"
        biped["male_bodypart"] = rid
        biped["female_bodypart"] = rid
        moved += 1
    return moved


def on_disk(root):
    """Which slots have a mesh built, so nothing points at a missing file."""
    return {key for slot in PARTS for key in (slot, slot + "_l")
            if os.path.exists(os.path.join(root, key + ".nif"))}
