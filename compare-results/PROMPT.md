# summary
you are a data analysis expert. you are helping me post process json fomatted results produced by AI multi-modal analysis of images.
the images are of Vero cell cultures.
the AI were instructed to analyze the imags, and detect cytopathic effect. 

there is a ground truth for CPE detection encoded in a json file. the ground truth was image analysis and descriptions provided by the contract research organization (CRO) which perform the cell culture experiment.

you get the data from the json files using these python functions:

```python
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
	
```

these are the json files:
```python
JSON_FILES = {
    "Claude": "ai-results/cpe_detection_results_claude.json",
    "ChatGPT": "ai-results/cpe_detection_results_chatgpt.json",
    "Gemini": "ai-results/cpe_detection_results_gemini.json",
    "Grok": "ai-results/cpe_detection_results_grok.json",
    "CRO": "cro-results/cpe_detection_results_cro_gk.json",
}
```
these are the color schemes you use when making graphics and tables so readers can easily visually identify whihc AI results they're looking at:
```python
# AI color scheme based on company logos
AI_COLORS = {
    "ChatGPT": "#10A37F",  # OpenAI green
    "Claude": "#7A4EAB",   # Anthropic purple
    "Gemini": "#4285F4",   # Google blue
    "Grok": "#FF6F00",     # xAI orange (vibrant, inspired by branding)
```