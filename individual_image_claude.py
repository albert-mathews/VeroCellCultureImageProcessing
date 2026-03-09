import anthropic
import os
import json
import pandas as pd
from dotenv import load_dotenv
import base64

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
        print("Loaded previous results. Skipping image uploads for existing files.")
    else:
        print("Starting fresh. All images will be re-uploaded.")

# Your common prompt for all images
common_prompt = """
Analyze the provided image of a cell culture.
The images are of Vero E6 cells, cultivated in typical growth medium.
The images are taken using bright field or phase contrast microscope.
The magnification is either 10x or 20x. Each image has a scale bar. 400um is 10x, and 200um is 20x.
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

# --- Processing Loop ---
print("Starting image processing... 🔬")
for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        if filename in all_results:
            print(f"Skipping already processed {filename}")
            continue

        full_path = os.path.join(image_folder, filename)

        try:
            # Base64 encode the image and determine media type
            with open(full_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            media_type = "image/png" if filename.lower().endswith('.png') else "image/jpeg"

            # Send the prompt and image to the model
            message = client.messages.create(
                model="claude-4.5-sonnet",  # Update to latest, e.g., 'claude-4.5-sonnet'
                max_tokens=1024,
                temperature=0,  # For consistency
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": base64_image}},
                            {"type": "text", "text": common_prompt}
                        ]
                    }
                ]
            )
            
            # Extract and parse the JSON response (Claude outputs text, so parse)
            response_json_str = message.content[0].text.strip('`').strip('json').strip()
            response_dict = json.loads(response_json_str)

            # Store the structured response
            all_results[filename] = [
                response_dict.get('cpe_detected', False),
                response_dict.get('cpe_quadrant'),
                response_dict.get('cpe_types'),
                response_dict.get('viability'),
                response_dict.get('full_response_text', '')
            ]

            print(f"Processed {filename}. CPE detected: {response_dict.get('cpe_detected')}. Viability: {response_dict.get('viability')}")

        except Exception as e:
            print(f"An error occurred while processing {filename}: {e}")
            all_results[filename] = [False, None, None, 0, f"Error: {e}"]
            
print("\nProcessing complete! 🎉")

# --- Generate and Display the Tabulated Results ---
print("\n--- Tabulated CPE Detections ---")
if all_results:
    data_for_table = {
        'Image Name': list(all_results.keys()),
        'CPE Detected': [v[0] for v in all_results.values()],
        'Quadrant': [v[1] for v in all_results.values()],
        'CPE Types': [v[2] for v in all_results.values()]
    }
    df = pd.DataFrame(data_for_table)
    print(df.to_string(index=False))

    # --- Save the Dictionary to a JSON file ---
    with open(results_filename, 'w') as f:
        json.dump(all_results, f, indent=4)
    
    print(f"\nDictionary of results saved to '{results_filename}'")
else:
    print("No results to display.")