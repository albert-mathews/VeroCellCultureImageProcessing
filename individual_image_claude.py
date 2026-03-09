import anthropic
import os
import re
import json
import time
import base64
import pandas as pd
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Path to your image folder
image_folder = 'converted_pngs'

# The name of the file to save/load results
results_filename = 'cpe_detection_results_claude.json'

# --- Load existing results ---
all_results = {}
if os.path.exists(results_filename):
    load_choice = input(f"'{results_filename}' found. Do you want to load it? (yes/no): ").lower()
    if load_choice == 'yes':
        with open(results_filename, 'r') as f:
            all_results = json.load(f)
        print("Loaded previous results. Skipping already-processed files.")
    else:
        print("Starting fresh. All images will be re-processed.")

# --- Common prompt (moved to system role for prompt caching) ---
# Caching this saves ~90% of input token cost on the prompt for every image after the first.
SYSTEM_PROMPT = """
You are a virology specialist. Your specialty is analyzing light microscope images of Vero cell cultures.
Analyze the provided image of a cell culture.
The images are of Vero E6 cells, cultivated in typical growth medium.
The images are taken using bright field or phase contrast microscope.
The magnification is either 10x or 20x. Each image has a scale bar. 400um is 10x, and 200um is 20x.
Your primary task is to detect the presence of CPE (Cytopathic Effect).
Specific CPE morphologies you should be looking for:
Dying cells
Rounding
vacuolation
Detached
Granularity
Refractile

Other CPE morphologies you should look for:
Syncytium formation
Intranuclear inclusion bodies
Pyknosis
Karyorrhexis

Your secondary task is to estimate the viability of the culture in the image, i.e. the ratio of live cells divided by total cells.
Normally this is done using a device like a  Invitrogen Countess 3 Automated Cell Counter with trypan blue staining, live cells remain unstained (translucent), while dead cells take up the dye and appear dark.
the images dont have the stain, so you'll have to do your best with what the image has. try to find other features of cell morphology or appearance to determine a probability of dead/alive for each cell, then use the each cell value to compute a total image ratio of dead/alive cells.

Please return your analysis as a JSON object with the following structure:
{
    "cpe_detected": boolean,
    "cpe_quadrant": number | null,
    "cpe_types": string[] | null,
    "viability": number,
    "full_response_text": string
}

Here are the specific instructions for each key:
- "cpe_detected": A boolean. True if any form of CPE is detected, otherwise False.
- "cpe_quadrant": An integer from 1 to 4 representing the quadrant where the most significant CPE is detected. Quadrant 1 is top-left, 2 is top-right, 3 is lower-left, and 4 is lower-right. If no CPE is detected, set this to null.
- "cpe_types": A list of strings. Include 'rounding', 'detachment', or 'lysis' for each type of CPE detected. If no CPE is found, set this to null.
- "viability": 0 to 100% with 0% being all dead cells, and 100% being all living cells, and 50% being half living and half dead cells.
- "full_response_text": A brief textual summary of your overall findings for the image.

Example response for a positive detection:
{
    "cpe_detected": true,
    "cpe_quadrant": 1,
    "cpe_types": ["rounding", "lysis"],
    "viability": 50,
    "full_response_text": "Significant cell rounding and lysis detected in the upper-left quadrant."
}
"""

def call_claude_with_retry(image_b64: str, media_type: str, max_retries: int = 3) -> dict:
    """
    Send one image to Claude Opus 4 with the system prompt cached.
    Retries up to max_retries times on rate-limit or transient API errors.
    """
    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-opus-4-6",   # Best vision model; changed from invalid "claude-4.5-sonnet"
                max_tokens=2048,           # Increased from 1024 to avoid truncated full_response_text
                temperature=0,             # Keep at 0 for reproducibility
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"}  # Cache the long prompt — saves ~90% on repeat calls
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_b64
                                }
                            },
                            {
                                "type": "text",
                                "text": "Analyze this cell culture image and return the JSON object as instructed."
                            }
                        ]
                    }
                ]
            )
            return message

        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"  Rate limit hit. Waiting {wait}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait)

        except anthropic.APIStatusError as e:
            # Retry on 529 (overloaded) or 500 (server error); re-raise on others
            if e.status_code in (500, 529) and attempt < max_retries - 1:
                wait = 30 * (attempt + 1)
                print(f"  API error {e.status_code}. Waiting {wait}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Failed after {max_retries} attempts.")


def parse_json_response(raw_text: str) -> dict:
    """
    Robustly extract JSON from the model response.
    Handles cases where the model accidentally wraps output in markdown fences.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r'```(?:json)?', '', raw_text).strip('` \n')
    # Find the outermost JSON object
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON object found in response:\n{raw_text}")


# --- Processing Loop ---
print("Starting image processing... 🔬")

image_files = [
    f for f in os.listdir(image_folder)
    if f.lower().endswith(('.png', '.jpg', '.jpeg'))
]

if not image_files:
    print(f"No images found in '{image_folder}'. Exiting.")
    exit()

for i, filename in enumerate(image_files, 1):
    print(f"\n[{i}/{len(image_files)}] {filename}")

    if filename in all_results:
        print("  Already processed — skipping.")
        continue

    full_path = os.path.join(image_folder, filename)

    try:
        # Read and base64-encode the image
        with open(full_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        media_type = "image/png" if filename.lower().endswith('.png') else "image/jpeg"

        # Call the API
        message = call_claude_with_retry(image_b64, media_type)

        # Parse the JSON response robustly
        raw_text = message.content[0].text
        response_dict = parse_json_response(raw_text)

        # Store as a list to match original format
        all_results[filename] = [
            response_dict.get('cpe_detected', False),
            response_dict.get('cpe_quadrant'),
            response_dict.get('cpe_types'),
            response_dict.get('viability'),
            response_dict.get('full_response_text', '')
        ]

        print(f"  CPE detected: {response_dict.get('cpe_detected')} | "
              f"Viability: {response_dict.get('viability')}% | "
              f"Types: {response_dict.get('cpe_types')}")

        # Save results after every image so progress isn't lost on crash
        with open(results_filename, 'w') as f:
            json.dump(all_results, f, indent=4)

        # Polite pause between requests to avoid hitting rate limits
        if i < len(image_files):
            time.sleep(2)

    except Exception as e:
        print(f"  ERROR processing {filename}: {e}")
        all_results[filename] = [False, None, None, None, f"Error: {e}"]
        with open(results_filename, 'w') as f:
            json.dump(all_results, f, indent=4)

print("\n\nProcessing complete! 🎉")

# --- Generate and Display Tabulated Results ---
print("\n--- Tabulated CPE Detections ---")
if all_results:
    df = pd.DataFrame({
        'Image Name':   list(all_results.keys()),
        'CPE Detected': [v[0] for v in all_results.values()],
        'Quadrant':     [v[1] for v in all_results.values()],
        'CPE Types':    [v[2] for v in all_results.values()],
        'Viability %':  [v[3] for v in all_results.values()],
        'Summary':      [v[4] for v in all_results.values()],
    })
    print(df.to_string(index=False))
    print(f"\nResults saved to '{results_filename}'")
else:
    print("No results to display.")