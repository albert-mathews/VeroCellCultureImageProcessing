import json
import os
import pandas as pd
from typing import Dict, Any
import matplotlib.pyplot as plt
import numpy as np
from math import pi
import seaborn as sns

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
    presence = {typ: False for typ in CPE_MATCH_TYPES}
    if types_list is None:
        types_list = []  # Handle None
    for t in types_list:
        for full_typ in CPE_MATCH_TYPES:
            if full_typ.lower() in t.lower():  # Fuzzy match
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

    # 1: Tabular plot of CPE type per image
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
    detailed_latex = "paper/cpe_type_tabular.tex"
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

    # 2: AI accuracy bar chart
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
    
    # <Grok here> New 2.1: AI accuracy bar chart for path1 images
    # <Grok here> New 2.2: AI accuracy bar chart for path2 images

    # the spider chart did not look good. skip it. 
    # 3: AI accuracy spider chart
    # categories = CPE_TYPES
    # N = len(categories)
    # angles = [n / float(N) * 2 * pi for n in range(N)]
    # angles += angles[:1]  # Close the plot

    # fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    # ax.set_theta_offset(pi / 2)
    # ax.set_theta_direction(-1)
    # ax.set_rlabel_position(0)
    # plt.xticks(angles[:-1], categories, color='grey', size=8)
    # plt.yticks([20,40,60,80,100], ["20","40","60","80","100"], color="grey", size=7)
    # plt.ylim(0,100)

    # for ai in ai_order:
        # values = [accuracy_data[ai][typ] for typ in categories]
        # values += values[:1]  # Close
        # ax.plot(angles, values, linewidth=1, linestyle='solid', label=ai, color=AI_COLORS[ai])
        # ax.fill(angles, values, alpha=0.1, color=AI_COLORS[ai])

    # plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    # spider_path = "ai_accuracy_spider.png"
    # plt.savefig(spider_path)
    # print(f"Saved spider chart: {spider_path}")
    # plt.close()

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
    
    


if __name__ == "__main__":
    print(JSON_FILES)
    prog()