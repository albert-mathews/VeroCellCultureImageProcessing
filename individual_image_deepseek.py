import openai
import os
import json
import pandas as pd
from dotenv import load_dotenv
import base64
import requests

# --- Configuration ---
load_dotenv()
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Path to your image folder
image_folder = 'converted_pngs'

# Your common prompt for all images
# NOTE: The prompt is crucial. It must instruct the model to return a structured JSON response.
common_prompt = """
Analyze the provided image of a cell culture.
The images are of Vero E6 cells, cultivated in typical growth medium.
The images are taken using bright field or phase constrast microscope.
The magnification is either 10x or 20x. Each image as a scale bar. 400um is 10x, and 200um is 20x.
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

Based on your analysis, provide a structured JSON response with the following keys:
"cpe_detected": boolean (true if CPE is detected, false otherwise)
"cpe_quadrant": string ("top-left", "top-right", "bottom-left", "bottom-right", or "none" if CPE is not detected in a specific quadrant)
"cpe_types": list of strings (e.g., ["cell rounding", "syncytium formation"])
"full_response_text": string (a detailed description of your findings)

You MUST provide a valid JSON response as your entire output.
"""

def encode_image(image_path):
    """Encodes a single image file to a Base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# --- Step 1: Initialize the DeepSeek API client ---
# The DeepSeek API is compatible with the OpenAI SDK
client = openai.OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

# --- Step 2: Iterate through images and send requests ---
all_results = {}
image_paths = [os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

print(f"Found {len(image_paths)} image(s) to process.")

for image_path in image_paths:
    filename = os.path.basename(image_path)
    print(f"Processing {filename}...")
    try:
        # Encode the image to Base64
        base64_image = encode_image(image_path)
        
        # Build the message content with both text and image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": common_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]

        # Call the DeepSeek API (using the deepseek-vl model for vision)
        response = client.chat.completions.create(
            model="deepseek-vl",
            messages=messages,
            stream=False,
            max_tokens=4096
        )

        response_content = response.choices[0].message.content
        response_dict = json.loads(response_content)

        all_results[filename] = [
            response_dict.get('cpe_detected', False),
            response_dict.get('cpe_quadrant'),
            response_dict.get('cpe_types'),
            response_dict.get('full_response_text', '')
        ]

        print(f"Processed {filename}. CPE detected: {response_dict.get('cpe_detected')}")
            
    except Exception as e:
        print(f"An error occurred while processing {filename}: {e}")
        all_results[filename] = [False, None, None, f"Error: {e}"]
            
print("\nProcessing complete! 🎉")

# --- Step 3: Generate and Display the Tabulated Results ---
print("\n--- Tabulated CPE Detections ---")
if all_results:
    # Convert the dictionary to a pandas DataFrame
    data_for_table = {
        'Image Name': list(all_results.keys()),
        'CPE Detected': [v[0] for v in all_results.values()],
        'Quadrant': [v[1] for v in all_results.values()],
        'CPE Types': [v[2] for v in all_results.values()]
    }
    df = pd.DataFrame(data_for_table)
    print(df.to_string(index=False))