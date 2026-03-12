import json

import os

import pandas as pd

from typing import Dict, Any



JSON_FILES = {

    "Claude": "cpe_detection_results_claude.json",

    "ChatGPT": "cpe_detection_results_chatgpt.json",

    "Gemini": "cpe_detection_results_gemini.json",

    "Grok": "cpe_detection_results_grok.json",

    "CRO": "cpe_detection_results_cro.json",

}



def load_json(filename: str) -> Dict[str, Any]:

    """Load JSON file, return dict of image → results."""

    if not os.path.exists(filename):

        print(f"Warning: {filename} not found. Skipping.")

        return {}

    with open(filename, "r", encoding="utf-8") as f:

        data = json.load(f)

    return data



def extract_cpe_summary(image_data: Dict[str, Any]) -> tuple[bool | None, str]:

    """Extract CPE detected (bool/None) and types (str)."""

    detected = image_data.get("cpe_detected")

    types_list = image_data.get("cpe_types", [])

    types_str = ", ".join(types_list) if types_list else "None"

    return ("Yes" if detected else "No" if detected is False else "N/A"), types_str



def main():

    all_data = {}

    images = set()



    # Load all JSONs

    for model, filename in JSON_FILES.items():

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

    csv_path = "cpe_comparison_table.csv"

    html_path = "cpe_comparison_table.html"

    df.to_csv(csv_path, index=False)

    df.to_html(html_path, index=False)

    print(f"\nSaved: {csv_path}, {html_path}")



if __name__ == "__main__":

    main()