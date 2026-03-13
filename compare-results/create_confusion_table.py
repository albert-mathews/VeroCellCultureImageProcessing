import json
import os
import csv
from typing import Dict, Any, Tuple

# Define constants
JSON_FILES = {
    "Claude": "ai-results/cpe_detection_results_claude.json",
    "ChatGPT": "ai-results/cpe_detection_results_chatgpt.json",
    "Gemini": "ai-results/cpe_detection_results_gemini.json",
    "Grok": "ai-results/cpe_detection_results_grok.json",
    "CRO": "cro-results/cpe_detection_results_cro.json",
}

CPE_TYPES = ["Dying cells", "Rounding", "Vacuolation", "Detached", "Granularity", "Refractile"]
CPE_MATCH_TYPES = ["dying", "round", "vacuol", "detach", "granul", "refract"]
CPETYPE_CODES = ["Dy", "Ro", "V", "D", "G", "Re"]
CPETYPE_NAMES = CPE_TYPES  # Alias for clarity

AI_ABBRS = ["GPT", "CLD", "Gem", "GRK"]
AI_FULLNAMES = ["ChatGPT", "Claude", "Gemini", "Grok"]

# Provided functions
def load_json(filename: str) -> Dict[str, Any]:
    """Load JSON file, return dict of image → results."""
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found. Skipping.")
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def extract_cpe_summary(image_data: Dict[str, Any]) -> Tuple[str, str]:
    """Extract CPE detected (Yes/No/N/A) and types (str). Handles different formats."""
    # For models like ChatGPT/Claude/Grok/Gemini
    if "culture_state" in image_data:
        culture_state = image_data.get("culture_state")
        detected = "Yes" if culture_state == "clear_cpe" else "No" if culture_state in ["healthy", "early_stress"] else "N/A"
        types_list = image_data.get("cpe_types", [])
    # For CRO or simple formats
    else:
        detected_val = image_data.get("cpe_detected")
        if detected_val is None:
            # Fallback to parse full_response_text if available
            text = image_data.get("full_response_text", "")
            if "false" in text.lower():
                detected = "No"
            elif "true" in text.lower():
                detected = "Yes"
            else:
                detected = "N/A"
        else:
            detected = "Yes" if detected_val else "No"
        types_list = image_data.get("cpe_types", [])

    types_str = ", ".join(types_list) if types_list else "None"
    return detected, types_str

def parse_image_name(image_name: str) -> Tuple[int, str]:
    """Parse path number and ID from filename, e.g., EXP_path1_passage4_101.png -> (1, '101')"""
    parts = image_name.split('_')
    if len(parts) >= 3:
        path_num = int(parts[1].replace('path', ''))
        id_part = parts[-1].split('.')[0]  # Remove .png
        return path_num, id_part
    return 0, image_name  # Fallback

def get_cpe_presence(types_list: list) -> Dict[str, bool]:
    """Map CPE types to presence dict for tabular."""
    presence = {typ: False for typ in CPE_TYPES}  # Use full CPE_TYPES as keys
    if types_list is None:
        types_list = []  # Handle None
    for t in types_list:
        for full_typ in CPE_TYPES:
            if full_typ.lower() in t.lower() or any(match.lower() in t.lower() for match in CPE_MATCH_TYPES if match in full_typ.lower()):  # Enhanced fuzzy match
                presence[full_typ] = True
    return presence

# Load all data
datas = {}
for key, path in JSON_FILES.items():
    datas[key] = load_json(path)

cro_data = datas["CRO"]

# Get sorted images from CRO (ground truth)
images = sorted(cro_data.keys(), key=lambda x: (parse_image_name(x)[0], int(parse_image_name(x)[1]) if parse_image_name(x)[1].isdigit() else parse_image_name(x)[1]))

# Prepare CSV
output_dir = "compare-results"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "cpe_confusion_table_short.csv")

with open(output_path, 'w', newline='') as csvfile:
    fieldnames = ['path', 'id'] + [f"CRO_{code}" for code in CPETYPE_CODES] + sum([[f"{abbr}_{code}" for code in CPETYPE_CODES] for abbr in AI_ABBRS], [])
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for image_name in images:
        path_num, id_part = parse_image_name(image_name)

        # CRO presence
        _, types_str = extract_cpe_summary(cro_data[image_name])
        types_list = [] if types_str == "None" else types_str.split(", ")
        cro_presence = get_cpe_presence(types_list)

        row = {'path': path_num, 'id': id_part}

        # CRO columns: 1 if present, 0 else
        for i, code in enumerate(CPETYPE_CODES):
            name = CPETYPE_NAMES[i]
            row[f"CRO_{code}"] = 1 if cro_presence.get(name, False) else 0

        # AI columns
        for abbr, full in zip(AI_ABBRS, AI_FULLNAMES):
            ai_data = datas.get(full, {})
            if image_name in ai_data:
                _, types_str = extract_cpe_summary(ai_data[image_name])
                types_list = [] if types_str == "None" else types_str.split(", ")
                ai_presence = get_cpe_presence(types_list)
            else:
                ai_presence = {name: False for name in CPETYPE_NAMES}

            for i, code in enumerate(CPETYPE_CODES):
                name = CPETYPE_NAMES[i]
                ai_yes = ai_presence.get(name, False)
                cro_yes = cro_presence.get(name, False)
                if ai_yes and cro_yes:
                    val = 1  # True Positive
                elif ai_yes and not cro_yes:
                    val = -2  # False Positive
                elif not ai_yes and cro_yes:
                    val = -1  # False Negative
                else:
                    val = 0  # True Negative
                row[f"{abbr}_{code}"] = val

        writer.writerow(row)

print(f"CSV file created at: {output_path}")