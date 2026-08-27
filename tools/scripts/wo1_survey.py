import json
import csv
import re
import os
import time

TARGET_KEYWORDS = ['daedra', 'daedric', 'daedroth', 'aedra']

def stream_records(filepath):
    """
    Yields parsed JSON objects one by one from the tes3conv JSON array.
    Relies on tes3conv's strict indentation: top-level objects start with '  {' and end with '  }' or '  },'.
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        buffer = []
        for line in f:
            if line.startswith('  }') and buffer:
                buffer.append('}') # close the object properly ignoring trailing commas
                try:
                    yield json.loads(''.join(buffer))
                except json.JSONDecodeError:
                    pass
                buffer = []
            elif line.startswith('  {') and not buffer:
                buffer.append('{')
            elif buffer:
                buffer.append(line)

def count_words(text):
    if not text:
        return 0
    return len(re.findall(r'\b\w+\b', text))

def has_keyword(text):
    if not text:
        return False
    text = str(text).lower()
    return any(k in text for k in TARGET_KEYWORDS)

def run_survey(json_files, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    
    # Report 1: Cast List
    # actor_id -> {"actor_name": str, "unique_info_count": int, "total_words": int}
    cast_list = {}
    
    # Report 2: Keyword Occurrences
    # (keyword, record_type, field) -> count
    occurrences = {}
    
    # Report 3: Topic Inventory
    # topic_id -> {"dialogue_type": str, "info_count": int, "contains_target_keyword": bool}
    topics = {}
    
    # Report 4: Cell Report
    # cell_id -> {"is_interior": bool, "contains_target_keyword": bool, "referenced_by_script_count": int}
    cells = {}
    
    # To look up actor names for cast list
    actor_names = {}
    
    # To associate INFOs with their parent DIAL
    current_topic_id = None
    
    # To count script references to cells
    scripts_text = []

    print("Parsing records...")
    
    for filepath in json_files:
        print(f"Processing {filepath}...")
        if not os.path.exists(filepath):
            print(f"  File not found, skipping: {filepath}")
            continue
            
        for rec in stream_records(filepath):
            rtype = rec.get("type")
            rid = str(rec.get("id", "")).lower()
            
            # --- Gather Actor Names ---
            if rtype in ("Npc", "Creature"):
                name = rec.get("name", "")
                if rid:
                    actor_names[rid] = name
                    
            # --- Gather Script Texts (for Cell report) ---
            if rtype == "Script":
                text = rec.get("text", "")
                if text:
                    scripts_text.append(text.lower())
                    
            # --- Topic Inventory & Parent Tracking ---
            if rtype == "Dialogue":
                original_id = rec.get("id", "")
                current_topic_id = original_id
                dial_type = rec.get("dialogue_type", "Topic")
                if isinstance(dial_type, dict): # tes3conv sometimes formats enums
                    dial_type = dial_type.get("data", dial_type)
                
                # Check keyword in topic ID itself
                has_kw = has_keyword(original_id)
                topics[original_id] = {
                    "dialogue_type": str(dial_type),
                    "info_count": 0,
                    "contains_target_keyword": has_kw
                }
                
                # Check keyword occurrence in DIAL id
                for kw in TARGET_KEYWORDS:
                    if kw in original_id.lower():
                        occurrences[(kw, "DIAL", "id")] = occurrences.get((kw, "DIAL", "id"), 0) + 1
                        
            # --- INFO Records (Cast List & Topic child count) ---
            if rtype == "DialogueInfo":
                if current_topic_id and current_topic_id in topics:
                    topics[current_topic_id]["info_count"] += 1
                
                text = rec.get("text", "")
                speaker = rec.get("speaker_id", "")
                
                # Check for keyword occurrences in INFO
                has_kw = False
                for kw in TARGET_KEYWORDS:
                    if kw in str(text).lower():
                        occurrences[(kw, "INFO", "text")] = occurrences.get((kw, "INFO", "text"), 0) + 1
                        has_kw = True
                        
                if speaker and has_kw:
                    speaker_key = speaker.lower()
                    words = count_words(text)
                    if speaker_key not in cast_list:
                        cast_list[speaker_key] = {"unique_info_count": 0, "total_words": 0}
                    cast_list[speaker_key]["unique_info_count"] += 1
                    cast_list[speaker_key]["total_words"] += words
            
            # --- Keyword Occurrences ---
            check_fields = ["name", "text", "description"]
            if rtype in ["Book", "Npc", "Creature", "Spell", "Alchemy", "Ingredient", 
                         "Armor", "Weapon", "Clothing", "MiscItem", "Cell", "GameSetting", 
                         "Faction", "Class", "Birthsign"]:
                for field in check_fields:
                    val = rec.get(field)
                    if val:
                        val_lower = str(val).lower()
                        for kw in TARGET_KEYWORDS:
                            # Count total occurrences in the string or just 1 per record? 
                            # The spec says "occurrence_count". Counting 1 per record field is safer.
                            if kw in val_lower:
                                occurrences[(kw, rtype.upper(), field)] = occurrences.get((kw, rtype.upper(), field), 0) + 1

            # --- Cell Report ---
            if rtype == "Cell":
                original_id = rec.get("id", "")
                flags = rec.get("flags", 0)
                # In Morrowind, an interior cell has flag 0x01 (Is Interior)
                # tes3conv might output flags as int or dict/list, checking if 'Interior' in string representation
                is_interior = False
                if isinstance(flags, int):
                    is_interior = bool(flags & 1)
                elif isinstance(flags, list):
                    is_interior = "Interior" in flags
                elif isinstance(flags, str):
                    is_interior = "Interior" in flags
                
                has_kw = has_keyword(original_id)
                cells[original_id] = {
                    "is_interior": is_interior,
                    "contains_target_keyword": has_kw,
                    "referenced_by_script_count": 0
                }

    print("Post-processing cell scripts...")
    for cell_id in cells:
        cid_lower = cell_id.lower()
        # Find cell id as a standalone word (roughly) in script text
        # e.g., "cell_id" or cell_id
        # Simple substring match for now, could use regex boundary if needed, but cell IDs have spaces.
        count = sum(1 for stext in scripts_text if cid_lower in stext)
        cells[cell_id]["referenced_by_script_count"] = count

    # Write Cast List
    cast_file = os.path.join(out_dir, "wo1-cast-list.csv")
    with open(cast_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["actor_id", "actor_name", "unique_info_count", "total_words"])
        # sort by total_words descending
        sorted_cast = sorted(cast_list.items(), key=lambda x: x[1]["total_words"], reverse=True)
        for actor_id, data in sorted_cast:
            name = actor_names.get(actor_id, "")
            writer.writerow([actor_id, name, data["unique_info_count"], data["total_words"]])

    # Write Keyword Occurrences
    occ_file = os.path.join(out_dir, "wo1-keyword-occurrences.csv")
    with open(occ_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["keyword", "record_type", "field", "occurrence_count"])
        # sort by count descending
        for (kw, rtype, field), count in sorted(occurrences.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([kw, rtype, field, count])

    # Write Topic Inventory
    topic_file = os.path.join(out_dir, "wo1-topic-inventory.csv")
    with open(topic_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["topic_id", "dialogue_type", "info_count", "contains_target_keyword"])
        for tid, data in sorted(topics.items()):
            writer.writerow([tid, data["dialogue_type"], data["info_count"], data["contains_target_keyword"]])

    # Write Cell Report
    cell_file = os.path.join(out_dir, "wo1-cell-report.csv")
    with open(cell_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cell_id", "is_interior", "contains_target_keyword", "referenced_by_script_count"])
        for cid, data in sorted(cells.items()):
            writer.writerow([cid, data["is_interior"], data["contains_target_keyword"], data["referenced_by_script_count"]])

    print("Reports generated successfully in:", out_dir)

if __name__ == "__main__":
    scratch_dir = r"C:\Users\faig3\.gemini\antigravity-ide\brain\a7068993-16bc-45df-b202-056fe56bf50b\scratch"
    master_files = [
        os.path.join(scratch_dir, "Morrowind.json"),
        os.path.join(scratch_dir, "Tribunal.json"),
        os.path.join(scratch_dir, "Bloodmoon.json"),
    ]
    
    # Wait for the background processes (task-117, task-118) if they are still running, by just checking if files exist and are populated
    # In practice, we just assume they are done by the time this runs.
    
    out_dir = r"d:\Work\Morrowind reborn\tools\reports"
    run_survey(master_files, out_dir)
