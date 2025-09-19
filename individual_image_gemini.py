import google.generativeai as genai
import os
import json
import pandas as pd
from dotenv import load_dotenv
import time

# --- Configuration ---
load_dotenv()
os.environ['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

# Path to your image folder
image_folder = 'converted_pngs'

# The name of the file to save/load results
results_filename = 'cpe_detection_results_gemini.json'

# --- Add this new section to load existing results ---
all_results = {}
if os.path.exists(results_filename):
    load_choice = input(f"'{results_filename}' found. Do you want to load it and use existing file IDs to skip re-uploading images? (yes/no): ").lower()
    if load_choice == 'yes':
        with open(results_filename, 'r') as f:
            all_results = json.load(f)
        print("Loaded previous results. Skipping image uploads for existing files.")
    else:
        print("Starting fresh. All images will be re-uploaded.")

# Your common prompt for all images
common_prompt = """
Analyze the provided image of a cell culture.
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

# Initialize the Gemini model
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# --- Processing Loop ---
print("Starting image processing... 🔬")
for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        full_path = os.path.join(image_folder, filename)
        file_id = None

        # Check if the file already has an ID from a previous run
        if filename in all_results and len(all_results[filename]) > 4:
            # The fourth element is the file ID (index 3)
            file_id = all_results[filename][4] 
            print(f"Using pre-existing file ID for {filename}: {file_id}")
            uploaded_file = genai.get_file(file_id)
        else:
            try:
                # Upload the image file for processing
                uploaded_file = genai.upload_file(path=full_path)
                file_id = uploaded_file.name
                print(f"Uploaded {filename}. File ID: {file_id}")
                
                # Wait for the file to be active before processing
                while uploaded_file.state.name != 'ACTIVE':
                    print(f"Waiting for {filename} to be processed...")
                    time.sleep(5)
                    uploaded_file = genai.get_file(uploaded_file.name)
            
            except Exception as e:
                print(f"An error occurred while uploading {filename}: {e}")
                all_results[filename] = [False, None, None, f"Error: {e}", None]
                continue # Skip to the next image on upload error

        try:
            # Send the prompt and the uploaded file to the model
            response = model.generate_content([
                common_prompt, 
                uploaded_file
            ])
            
            # Extract and parse the JSON response from the model
            response_json_str = response.text.strip('`').strip('json').strip()
            response_dict = json.loads(response_json_str)

            # Store the structured response in our dictionary, including the file ID
            all_results[filename] = [
                response_dict.get('cpe_detected', False),
                response_dict.get('cpe_quadrant'),
                response_dict.get('cpe_types'),
                response_dict.get('confluency'),
                response_dict.get('full_response_text', ''),
                file_id  # Add the file ID to the list
            ]

            print(f"Processed {filename}. CPE detected: {response_dict.get('cpe_detected')}. Confluency: {response_dict.get('confluency')}")
            
            # Clean up the temporary uploaded file
            genai.delete_file(uploaded_file.name)

        except Exception as e:
            print(f"An error occurred while processing {filename}: {e}")
            all_results[filename] = [False, None, None, f"Error: {e}", file_id]
            
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

    # --- Step 4: Save the Dictionary to a JSON file ---
    with open(results_filename, 'w') as f:
        json.dump(all_results, f, indent=4)
    
    print(f"\nDictionary of results saved to '{results_filename}'")
else:
    print("No results to display.")