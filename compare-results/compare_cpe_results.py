import json
import os
import pandas as pd
from typing import Dict, Any
import matplotlib.pyplot as plt
import numpy as np
from math import pi
import seaborn as sns
from mpl_toolkits.mplot3d import Axes3D

JSON_FILES = {
    "Claude": "ai-results/cpe_detection_results_claude.json",
    "ChatGPT": "ai-results/cpe_detection_results_chatgpt.json",
    "Gemini": "ai-results/cpe_detection_results_gemini.json",
    "Grok": "ai-results/cpe_detection_results_grok.json",
    "CRO": "cro-results/cpe_detection_results_cro_gk.json",
}

# AI color scheme based on company logos
AI_COLORS = {
    "ChatGPT": "#10A37F",  # OpenAI green
    "Claude": "#7A4EAB",   # Anthropic purple
    "Gemini": "#4285F4",   # Google blue
    "Grok": "#FF6F00",     # xAI orange (vibrant, inspired by branding)
}

CPE_TYPES = ["Dying Cells", "Rounding", "Vacuolation", "Detached", "Granularity", "Refractile"]
CPE_MATCH_TYPES = ["Dying", "Rounding", "Vacuo", "Detached", "Granu", "Refrac"]
CPE_SHORT = ["C", "Ro", "V", "D", "G", "Re"]

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

def parse_image_name(image_name: str) -> tuple[int, str]:
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
            if full_typ.lower() in t.lower() or any(match.lower() in t.lower() for match in CPE_MATCH_TYPES if match in full_typ):  # Enhanced fuzzy match
                presence[full_typ] = True
    return presence

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

    # Existing functionality: Align data by image for summary table
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
    df_summary = pd.DataFrame(rows)
    print("\n=== CPE Detection Summary Table ===\n")
    print(df_summary.to_string(index=False))

    # Save outputs
    csv_path = "compare-results/cpe_comparison_table.csv"
    html_path = "compare-results/cpe_comparison_table.html"
    df_summary.to_csv(csv_path, index=False)
    df_summary.to_html(html_path, index=False)
    print(f"\nSaved: {csv_path}, {html_path}")

    # New 1: Tabular plot of CPE type per image
    # Prepare data with parsed path and ID
    detailed_rows = []
    for image in sorted_images:
        path_num, img_id = parse_image_name(image)
        row = {"Path": path_num, "ID": img_id}
        
        # Get presence for each model
        for model in JSON_FILES:
            model_data = all_data.get(model, {}).get(image, {})
            types_list = model_data.get("cpe_types", [])
            presence = get_cpe_presence(types_list)
            for short, full in zip(CPE_SHORT, CPE_TYPES):
                row[f"{model}_{short}"] = "✔️" if presence[full] else ""  # Placeholder; will style in HTML/LaTeX

        detailed_rows.append(row)

    df_detailed = pd.DataFrame(detailed_rows)
    df_detailed.sort_values(by=['Path', 'ID'], inplace=True)

    # Group by Path (multi-index)
    df_grouped = df_detailed.set_index(['Path', 'ID'])

    # CSV without coloring
    detailed_csv = "compare-results/cpe_type_tabular.csv"
    df_grouped.to_csv(detailed_csv)
    print(f"Saved detailed CSV: {detailed_csv}")

    # HTML with coloring
    def style_html(df):
        # Style function
        def apply_style(val, model_color=None):
            if val == "✔️":
                return 'background-color: lightblue; color: darkblue;'  # BCM
            elif val == "X":
                return 'background-color: red; color: white;'
            return ''

        styled = df.style
        # Apply colors to headers/AI columns
        for model in ['CRO', 'ChatGPT', 'Claude', 'Gemini', 'Grok']:
            for short in CPE_SHORT:
                col = f"{model}_{short}"
                if model != 'CRO' and model in AI_COLORS:
                    styled = styled.map(lambda v: f'background-color: {AI_COLORS[model]};' if v else '', subset=[col])
                else:
                    styled = styled.map(lambda v: apply_style(v), subset=[col])
        return styled

    detailed_html = "compare-results/cpe_type_tabular.html"
    style_html(df_grouped.reset_index()).to_html(detailed_html)
    print(f"Saved detailed HTML: {detailed_html}")
    
    # <Grok here> New 1.1: let's make a very dense image like this:
    # "" means put that string exactly.
    # |...,X| means this cell span X cells below: e.g.
    # |...,2|..............,6 |       
    # |..|..|..|..|..|..|..|..|
    #
    # |.r.| this means put the 6 data values for the result group for the row
    #
    # |"Images",2|"CRO",6|"ChatGPT",6|"Claude",6|"Gemini",6|"Grok",6|
    # |<path>|<id>|.r.   | .r.       |   .r.    |   .r.    |  .r.   |

    # LaTeX with coloring (using colortbl package)
    latex_code = df_grouped.to_latex(
        escape=False,
        multirow=True,
        multicolumn=True,
        column_format='ll' + 'c' * len(CPE_SHORT) * len(JSON_FILES)
    )
    # Add colors manually (requires \usepackage{colortbl} in preamble)
    # For simplicity, print raw LaTeX; user can add \cellcolor{blue!20} for BCM, \cellcolor{red} for X
    detailed_latex = "compare-results/cpe_type_tabular.tex"
    with open(detailed_latex, 'w', encoding='utf-8') as f:
        f.write(latex_code)
    print(f"Saved detailed LaTeX: {detailed_latex}")

    # Prepare accuracy data for plots
    # Compute accuracy per AI per CPE type (using Jaccard or simple match vs CRO)
    accuracy_data = {ai: {typ: 0 for typ in CPE_TYPES} for ai in JSON_FILES if ai != "CRO"}
    counts = {typ: 0 for typ in CPE_TYPES}

    for image in sorted_images:
        cro_data = all_data.get("CRO", {}).get(image, {})
        cro_presence = get_cpe_presence(cro_data.get("cpe_types", []))
        
        for ai in accuracy_data:
            ai_data = all_data.get(ai, {}).get(image, {})
            ai_presence = get_cpe_presence(ai_data.get("cpe_types", []))
            
            for typ in CPE_TYPES:
                if cro_presence[typ] or ai_presence[typ]:  # Only count if relevant
                    counts[typ] += 1
                    if cro_presence[typ] == ai_presence[typ]:
                        accuracy_data[ai][typ] += 1

    # Normalize to %
    for ai in accuracy_data:
        for typ in CPE_TYPES:
            if counts[typ] > 0:
                accuracy_data[ai][typ] = (accuracy_data[ai][typ] / counts[typ]) * 100
            else:
                accuracy_data[ai][typ] = 0

    # New 2: AI accuracy bar chart
    ai_order = sorted(accuracy_data.keys())  # Alpha: ChatGPT, Claude, Gemini, Grok
    x = np.arange(len(CPE_TYPES))  # the label locations
    width = 0.2  # the width of the bars

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, ai in enumerate(ai_order):
        vals = [accuracy_data[ai][typ] for typ in CPE_TYPES]
        ax.bar(x + i*width, vals, width, label=ai, color=AI_COLORS[ai])

    ax.set_ylabel('Accuracy (%)')
    ax.set_title('AI Accuracy by CPE Type')
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(CPE_TYPES, rotation=45)
    ax.legend()
    plt.tight_layout()
    bar_chart_path = "compare-results/ai_accuracy_bar.png"
    plt.savefig(bar_chart_path)
    print(f"Saved bar chart: {bar_chart_path}")
    plt.close()

    # New 2.1: AI accuracy bar chart for path1 images
    # Filter images for path1
    path1_images = [img for img in sorted_images if parse_image_name(img)[0] == 1]
    accuracy_data_path1 = {ai: {typ: 0 for typ in CPE_TYPES} for ai in JSON_FILES if ai != "CRO"}
    counts_path1 = {typ: 0 for typ in CPE_TYPES}

    for image in path1_images:
        cro_data = all_data.get("CRO", {}).get(image, {})
        cro_presence = get_cpe_presence(cro_data.get("cpe_types", []))

        for ai in accuracy_data_path1:
            ai_data = all_data.get(ai, {}).get(image, {})
            ai_presence = get_cpe_presence(ai_data.get("cpe_types", []))
            
            for typ in CPE_TYPES:
                if cro_presence[typ] or ai_presence[typ]:
                    counts_path1[typ] += 1
                    if cro_presence[typ] == ai_presence[typ]:
                        accuracy_data_path1[ai][typ] += 1

    for ai in accuracy_data_path1:
        for typ in CPE_TYPES:
            if counts_path1[typ] > 0:
                accuracy_data_path1[ai][typ] = (accuracy_data_path1[ai][typ] / counts_path1[typ]) * 100
            else:
                accuracy_data_path1[ai][typ] = 0

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, ai in enumerate(ai_order):
        vals = [accuracy_data_path1[ai][typ] for typ in CPE_TYPES]
        ax.bar(x + i*width, vals, width, label=ai, color=AI_COLORS[ai])

    ax.set_ylabel('Accuracy (%)')
    ax.set_title('AI Accuracy by CPE Type (Path 1 Images)')
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(CPE_TYPES, rotation=45)
    ax.legend()
    plt.tight_layout()
    bar_chart_path1 = "compare-results/path1_ai_accuracy_bar.png"
    plt.savefig(bar_chart_path1)
    print(f"Saved Path 1 bar chart: {bar_chart_path1}")
    plt.close()

    # New 2.2: AI accuracy bar chart for path2 images
    # Filter images for path2
    path2_images = [img for img in sorted_images if parse_image_name(img)[0] == 2]
    accuracy_data_path2 = {ai: {typ: 0 for typ in CPE_TYPES} for ai in JSON_FILES if ai != "CRO"}
    counts_path2 = {typ: 0 for typ in CPE_TYPES}

    for image in path2_images:
        cro_data = all_data.get("CRO", {}).get(image, {})
        cro_presence = get_cpe_presence(cro_data.get("cpe_types", []))

        for ai in accuracy_data_path2:
            ai_data = all_data.get(ai, {}).get(image, {})
            ai_presence = get_cpe_presence(ai_data.get("cpe_types", []))
            
            for typ in CPE_TYPES:
                if cro_presence[typ] or ai_presence[typ]:
                    counts_path2[typ] += 1
                    if cro_presence[typ] == ai_presence[typ]:
                        accuracy_data_path2[ai][typ] += 1

    for ai in accuracy_data_path2:
        for typ in CPE_TYPES:
            if counts_path2[typ] > 0:
                accuracy_data_path2[ai][typ] = (accuracy_data_path2[ai][typ] / counts_path2[typ]) * 100
            else:
                accuracy_data_path2[ai][typ] = 0

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, ai in enumerate(ai_order):
        vals = [accuracy_data_path2[ai][typ] for typ in CPE_TYPES]
        ax.bar(x + i*width, vals, width, label=ai, color=AI_COLORS[ai])

    ax.set_ylabel('Accuracy (%)')
    ax.set_title('AI Accuracy by CPE Type (Path 2 Images)')
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(CPE_TYPES, rotation=45)
    ax.legend()
    plt.tight_layout()
    bar_chart_path2 = "compare-results/path2_ai_accuracy_bar.png"
    plt.savefig(bar_chart_path2)
    print(f"Saved Path 2 bar chart: {bar_chart_path2}")
    plt.close()

    # the spider chart did not look good. skip it. 
    # 3: AI accuracy spider chart
    # ...

    # 4: Confusion matrix graphics (proposals)
    # For each AI, create a heatmap confusion matrix for binary CPE detection (Yes/No vs CRO)
    # Assuming binary for simplicity; extend to multi-label if needed
    for ai in ai_order:
        cm = np.zeros((2, 2))  # [[TN, FP], [FN, TP]]
        for image in sorted_images:
            cro_detected = extract_cpe_summary(all_data.get("CRO", {}).get(image, {}))[0] == "Yes"
            ai_detected = extract_cpe_summary(all_data.get(ai, {}).get(image, {}))[0] == "Yes"
            cm[int(not cro_detected), int(ai_detected)] += 1

        fig, ax = plt.subplots(figsize=(6, 4))
        sns.heatmap(cm, annot=True, fmt="g", cmap="RdYlGn", ax=ax,
                    xticklabels=["Predicted No", "Predicted Yes"],
                    yticklabels=["Actual No", "Actual Yes"])
        ax.set_title(f"Confusion Matrix for {ai} (CPE Detection)")
        # Use AI color for accents if desired
        plt.tight_layout()
        cm_path = f"compare-results/{ai}_confusion_matrix.png"
        plt.savefig(cm_path)
        print(f"Saved confusion matrix for {ai}: {cm_path}")
        plt.close()

    # <Grok here>: New 4.1: combine the 4 confusion matrices into a single plot
    # in each quadrant of the confusion matrix, break it up into 4 quadrants, e.g
    # so the main quad for Actual NO,Predicted NO, will have four sub-quads like
    # |ChatGPT| Claude|
    # |Gemini | Grok  |
    # and each sub-quad has the score for that AI model, and the heat map color.
    # repeat for all four main quads.
    
    # <Grok here>: New 4.2: simmilar to 4.1, but instead of numerical value and heat map, make a 3D bar chart with same main-quad->sub-quad layout.
    # New 4.1: Combined 2D confusion matrix heatmap
    # Create a 4x4 grid where each main 2x2 quadrant is subdivided into 2x2 for AIs
    # But since CM is 2x2 main, overall grid is 4x4 (2 main rows/cols x 2 sub per AI row/col)
    # Actually for 4 AIs, sub is 2x2 per main quadrant
    fig, ax = plt.subplots(figsize=(12, 12))
    cm_combined = np.zeros((4, 4))  # 2 main rows x 2 sub-rows, etc.
    ai_sub_order = ['ChatGPT', 'Claude', 'Gemini', 'Grok']  # 2x2: top-left ChatGPT, top-right Claude, etc.

    # Compute individual CMs again for placement
    cms = {}
    for ai in ai_sub_order:
        cm = np.zeros((2, 2))
        for image in sorted_images:
            cro_detected = extract_cpe_summary(all_data.get("CRO", {}).get(image, {}))[0] == "Yes"
            ai_detected = extract_cpe_summary(all_data.get(ai, {}).get(image, {}))[0] == "Yes"
            cm[int(not cro_detected), int(ai_detected)] += 1
        cms[ai] = cm

    # Fill the large grid
    for main_row in range(2):  # Actual No/Yes
        for main_col in range(2):  # Predicted No/Yes
            for sub_row in range(2):  # AI sub-grid rows
                for sub_col in range(2):  # AI sub-grid cols
                    ai_idx = sub_row * 2 + sub_col
                    ai = ai_sub_order[ai_idx]
                    val = cms[ai][main_row, main_col]
                    row_idx = main_row * 2 + sub_row
                    col_idx = main_col * 2 + sub_col
                    cm_combined[row_idx, col_idx] = val

    # Heatmap with custom annotations (add AI labels inside sub-quads)
    sns.heatmap(cm_combined, annot=False, cmap="RdYlGn", ax=ax)  # Base heatmap without annot

    # Add annotations manually
    for main_row in range(2):
        for main_col in range(2):
            for sub_row in range(2):
                for sub_col in range(2):
                    ai_idx = sub_row * 2 + sub_col
                    ai = ai_sub_order[ai_idx]
                    val = cms[ai][main_row, main_col]
                    row_idx = main_row * 2 + sub_row + 0.5
                    col_idx = main_col * 2 + sub_col + 0.5
                    ax.text(col_idx, row_idx, f"{int(val)}\n{ai[:3]}", ha="center", va="center", color="black", fontsize=8)

    # Labels for main quadrants
    ax.set_xticks([1, 3])
    ax.set_xticklabels(["Predicted No", "Predicted Yes"], fontsize=12)
    ax.set_yticks([1, 3])
    ax.set_yticklabels(["Actual No", "Actual Yes"], fontsize=12)

    # Draw lines for sub-quads
    for i in range(0, 5, 2):
        ax.axhline(i, color='white', lw=2)
        ax.axvline(i, color='white', lw=2)

    ax.set_title("Combined Confusion Matrix (Subdivided by AI)")
    plt.tight_layout()
    combined_cm_path = "compare-results/combined_confusion_heatmap.png"
    plt.savefig(combined_cm_path)
    print(f"Saved combined confusion heatmap: {combined_cm_path}")
    plt.close()

    # New 4.2: Combined 3D bar chart
    fig = plt.figure(figsize=(12, 12))
    ax = fig.add_subplot(111, projection='3d')

    # Positions for bars
    _x = np.arange(4)  # X for sub-cols (AIs horizontal)
    _y = np.arange(4)  # Y for sub-rows (AIs vertical, but flipped for layout)
    _xx, _yy = np.meshgrid(_x, _y)
    x, y = _xx.ravel(), _yy.ravel()

    # Heights (z) from CM values, grouped by main quad
    z = np.zeros(16)
    colors = np.empty(16, dtype=object)
    ai_labels = ['ChatGPT', 'Claude', 'Gemini', 'Grok']

    idx = 0
    for main_row in range(2):
        for main_col in range(2):
            base_x = main_col * 2
            base_y = main_row * 2
            for sub_row in range(2):
                for sub_col in range(2):
                    ai_idx = sub_row * 2 + sub_col
                    ai = ai_sub_order[ai_idx]
                    val = cms[ai][main_row, main_col]
                    z[idx] = val
                    colors[idx] = AI_COLORS[ai]
                    idx += 1

    # 3D bars
    ax.bar3d(x, y, np.zeros_like(z), 0.8, 0.8, z, color=colors)

    # Labels
    ax.set_xticks([1, 3])
    ax.set_xticklabels(["Predicted No", "Predicted Yes"])
    ax.set_yticks([1, 3])
    ax.set_yticklabels(["Actual No", "Actual Yes"])
    ax.set_zlabel('Count')
    ax.set_title("Combined 3D Confusion Matrix (Subdivided by AI)")

    # Add AI labels on bars or legend
    ax.legend([plt.Rectangle((0,0),1,1,fc=AI_COLORS[ai]) for ai in ai_sub_order], ai_sub_order, loc='upper right')

    plt.tight_layout()
    combined_3d_path = "compare-results/combined_confusion_3d.png"
    plt.savefig(combined_3d_path)
    print(f"Saved combined 3D confusion bar chart: {combined_3d_path}")
    plt.close()

if __name__ == "__main__":
    print(JSON_FILES)
    prog()