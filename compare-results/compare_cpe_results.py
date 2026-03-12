import json
import os
import pandas as pd
from typing import Dict, Any

JSON_FILES = {
    "Claude": "ai-results/cpe_detection_results_claude.json",
    "ChatGPT": "ai-results/cpe_detection_results_chatgpt.json",
    "Gemini": "ai-results/cpe_detection_results_gemini.json",
    "Grok": "ai-results/cpe_detection_results_grok.json",
    "CRO": "cro-results/cpe_detection_results_cro_gk.json",
}

def load_json(filename: str) -> Dict[str, Any]:
    """Load JSON file, return dict of image → results."""
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found. Skipping.")
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def extract_cpe_summary(image_data: Dict[str, Any]) -> tuple[str, str]:
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

def prog():
    all_data = {}
    images = set()

    # Load all JSONs
    for model, filename in JSON_FILES.items():
        print(filename)
        data = load_json(filename)
        all_data[model] = data
        images.update(data.keys())

    if not images:
        print("No images found across JSON files.")
        return

    # Align data by image
    rows = []
    sorted_images = sorted(images)
    for image in sorted_images:
        row = {"Image": image}
        for model in JSON_FILES:
            model_data = all_data.get(model, {}).get(image, {})
            detected, types_str = extract_cpe_summary(model_data)
            row[f"{model}_CPE"] = detected
            row[f"{model}_Types"] = types_str
        rows.append(row)

    # Create and display DataFrame
    df = pd.DataFrame(rows)
    print("\n=== CPE Detection Summary Table ===\n")
    print(df.to_string(index=False))

    # Save outputs
    csv_path = "compare-results/cpe_comparison_table.csv"
    html_path = "compare-results/cpe_comparison_table.html"
    df.to_csv(csv_path, index=False)
    df.to_html(html_path, index=False)
    print(f"\nSaved: {csv_path}, {html_path}")

if __name__ == "__main__":
    print(JSON_FILES)
    prog()