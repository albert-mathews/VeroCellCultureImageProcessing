import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
import base64

# -------------------------------
# USER CONFIGURATION
# -------------------------------
IMAGES_DIR = "converted_pngs"
OUTPUT_JSON = "cpe_detection_results_chatgpt.json"

PROMPT = """
You are an expert cell biologist looking at microscope images of Vero E6 cell cultures.
Your task is to analyze the image and respond with:
- Whether cytopathic effect (CPE) is present (true/false).
- If present, which quadrant of the image shows the strongest CPE (1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right).
- If present, list all types of CPE observed (e.g., rounding, detachment, syncytia).
- Estimate the overall confluency as a percentage (0-100).

The imags are of Vero E6 cells, cultivated in typical growth medium.
The images are taken using bright field or phase constrast miscropscope.
The maginification is either 10x or 20x. Each image as a scale bar. 400um is 10x, and 200um is 20x.
Your primary task is to detect the presence of CPE (Cytopathic Effect).
CPE can be identified by signs such as:
Cell rounding
Cell shrinkage
Cell lysis (cytolysis)
Pyknosis
Karyorrhexis
Intranuclear inclusion bodies
Intracytoplasmic inclusion bodies
Nuclear and cytoplasmic inclusions
Syncytium formation (multinucleated giant cells)
Cytoplasmic vacuolization
Cytomegaly (cell enlargement)
Cell detachment
Plaque formation
Focus formation (loss of contact inhibition)
Immortalization
Malignant transformation
Hemadsorption
Chromosomal abnormalities
Cytoskeletal changes

your seconday task is to estimate the confluency of the culture in the image. estimate with precision or 5% or 10% if possible.
this is roughly the area of the image taken up by cells. 

Please return your analysis as a JSON object with the following structure:
{
    "cpe_detected": boolean,
    "cpe_quadrant": number | null,
    "cpe_types": string[] | null,
    "confluency": number,
    "full_response_text": string
}

Here are the specific instructions for each key:
- "cpe_detected": A boolean. True if any form of CPE is detected, otherwise False.
- "cpe_quadrant": An integer from 1 to 4 representing the quadrant where the most significant CPE is detected. Quadrant 1 is top-left, 2 is top-right, 3 is lower-left, and 4 is lower-right. If no CPE is detected, set this to null.
- "cpe_types": A list of strings. Include 'rounding', 'detachment', or 'lysis' for each type of CPE detected. If no CPE is found, set this to null.
- "confluency": 0 to 100% with 0% being no cells, and 100% being ful of cells, and 50% being half full of cells.
- "full_response_text": A brief textual summary of your overall findings for the image.

Example response for a positive detection:
{
    "cpe_detected": true,
    "cpe_quadrant": 1,
    "cpe_types": ["rounding", "lysis"],
    "confluency": 50,
    "full_response_text": "Significant cell rounding and lysis detected in the upper-left quadrant."
}
"""

# -------------------------------
# INITIALIZATION
# -------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load existing results if available
if os.path.exists(OUTPUT_JSON):
    with open(OUTPUT_JSON, "r") as f:
        results = json.load(f)
else:
    results = {}

# Ensure every image has an entry
image_files = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(".png")])
for img_file in image_files:
    if img_file not in results:
        results[img_file] = {
            "cpe_detected": None,
            "cpe_quadrant": None,
            "cpe_types": None,
            "confluency": None,
            "full_response_text": None,
            "image_id": None,
        }

# -------------------------------
# MAIN LOOP
# -------------------------------
for img_file in tqdm(image_files, desc="Processing images"):
    entry = results[img_file]

    # Skip if we already have results
    if entry["full_response_text"] is not None:
        continue

    # Encode image to base64 instead of uploading
    img_path = os.path.join(IMAGES_DIR, img_file)
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    img_data_url = f"data:image/png;base64,{img_b64}"

    # Call GPT with the image + prompt
    response = client.chat.completions.create(
        model="gpt-4o",  # or gpt-4o-mini if you want cheaper/faster
        messages=[
            {"role": "system", "content": "You are a helpful assistant for cell culture analysis."},
            {"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": img_data_url}},
            ]}
        ],
        temperature=0
    )


    full_text = response.choices[0].message.content
    entry["full_response_text"] = full_text

    # --- Optional: attempt parsing for structured output ---
    # Expecting GPT to return something like:
    # CPE detected: true
    # Quadrant: 2
    # CPE types: rounding, detachment
    # Confluency: 85%
    try:
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        for line in lines:
            lower = line.lower()
            if "cpe detected" in lower:
                entry["cpe_detected"] = "true" in lower
            elif "quadrant" in lower:
                parts = [int(s) for s in line.split() if s.isdigit()]
                entry["cpe_quadrant"] = parts[0] if parts else None
            elif "cpe types" in lower:
                types = line.split(":")[-1].strip()
                entry["cpe_types"] = [t.strip() for t in types.split(",")] if types else None
            elif "confluency" in lower:
                nums = [s for s in line if s.isdigit()]
                num_str = "".join(nums)
                entry["confluency"] = int(num_str) if num_str else None
    except Exception as e:
        print(f"Warning: failed to parse {img_file}: {e}")

    # Save progress after each image (important for long runs)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)

print("✅ Processing complete. Results saved to", OUTPUT_JSON)
