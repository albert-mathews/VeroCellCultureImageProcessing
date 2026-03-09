import openai
import os
import json
import pandas as pd
from dotenv import load_dotenv
import base64

# --- Configuration ---
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Path to your image folder
image_folder = 'converted_pngs'

# The name of the file to save/load results
results_filename = 'cpe_detection_results_chatgpt.json'

# --- Load existing results ---
all_results = {}
if os.path.exists(results_filename):
    load_choice = input(f"'{results_filename}' found. Do you want to load it? (yes/no): ").lower()
    if load_choice == 'yes':
        with open(results_filename, 'r') as f:
            all_results = json.load(f)
        print("Loaded previous results. Skipping processed images.")
    else:
        print("Starting fresh. All images will be re-uploaded.")

# Your common prompt for all images
common_prompt = """
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

If the image quality prevents confident detection, state uncertainty and estimate probability.

Your secondary task is to estimate the viability of the culture in the image, i.e. the ratio of live cells divided by total cells.
Normally this is done using a device like a  Invitrogen Countess 3 Automated Cell Counter with trypan blue staining, live cells remain unstained (translucent), while dead cells take up the dye and appear dark.
the images dont have the stain, so you'll have to do your best with what the image has. try to find other features of cell morphology or appearance to determine a probability of dead/alive for each cell, then use the each cell value to compute a total image ratio of dead/alive cells.

If the image quality prevents confident detection, state uncertainty and estimate probability.

Please return your analysis as a JSON object with the following structure:
{
    "cpe_detected": boolean,
    "cpe_types": string[] | null,
    "viability": number,
    "full_response_text": string
}

Here are the specific instructions for each key:
- "cpe_detected": A boolean. True if any form of CPE is detected, otherwise False.
- "cpe_types": A list of strings. Include 'rounding', 'detachment', or 'lysis' for each type of CPE detected. If no CPE is found, set this to null.
- "viability": 0 to 100% with 0% being all dead cells, and 100% being all living cells, and 50% being half living and half dead cells.
- "full_response_text": A brief textual summary of your overall findings for the image.

Example response for a positive detection:
{
    "cpe_detected": true,
    "cpe_types": ["rounding", "lysis"],
    "viability": 50,
    "full_response_text": "Significant cell rounding and lysis detected."
}
"""

# Initialize the client
client = openai.OpenAI()

few_shot_examples = [
    {
        "image_path": "converted_pngs/EXP_path1_passage4_401.png",
        "expected_output": {
            "cpe_detected": False,
            "cpe_types": None,
            "viability": 95,
            "full_response_text": "Cells are adherent and are growing in clusters that are beginning to merge. Very few bright dividing cells. A mitotic figure close to the bottom left corner of the field."
        }
    },
    {
        "image_path": "converted_pngs/EXP_path2_passage4_402.png",
        "expected_output": {
            "cpe_detected": True,
            "cpe_types": ["Dying cells", "Rounding","vacuolation","Refractile"],
            "viability": 40,
            "full_response_text": "Few small clusters present with some bright spots (vacuoles). There is a pair of dividing cells at 7 o’clock. Multiple single cells with some degree of spreading. Multiple rounded cells. Some cells appear rounded and refractile, which could indicate potentially dying cells (6 o’clock)."
        }
    }
]

messages = [
    {"role": "system", "content": "You are a virology microscopy expert that returns JSON only."}
]

# Add few-shot examples
for example in few_shot_examples:

    with open(example["image_path"], "rb") as img:
        example_b64 = base64.b64encode(img.read()).decode("utf-8")

    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": "Example analysis:"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{example_b64}"}}
        ]
    })

    messages.append({
        "role": "assistant",
        "content": json.dumps(example["expected_output"])
    })

# Actual image
messages.append({
    "role": "user",
    "content": [
        {"type": "text", "text": common_prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
    ]
})

# --- Processing Loop ---
print("Starting image processing... 🔬")
for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        if filename in all_results:
            print(f"Skipping already processed {filename}")
            continue

        full_path = os.path.join(image_folder, filename)

        try:
            # Base64 encode the image
            with open(full_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Send the prompt and image to the model
            response = client.chat.completions.create(
                model="gpt-4o",  # Update to latest vision model, e.g., 'gpt-5.2' or 'gpt-4o'
                messages=messages,
                temperature=0,  # For consistency
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "cpe_detection",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "cpe_detected": {"type": "boolean"},
                                "cpe_types": {
                                    "type": ["array", "null"],
                                    "items": {"type": "string"}
                                },
                                "viability": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 100
                                },
                                "full_response_text": {"type": "string"}
                            },
                            "required": [
                                "cpe_detected",
                                "cpe_types",
                                "viability",
                                "full_response_text"
                            ]
                        }
                    }
                }
            )
            
            # Extract and parse the JSON response
            response_dict = json.loads(response.choices[0].message.content)

            # Store the structured response (no file_id needed for OpenAI)
            all_results[filename] = [
                response_dict.get('cpe_detected', False),
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