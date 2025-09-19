import google.generativeai as genai
import os
import json
import pandas as pd
import re
from dotenv import load_dotenv

# Path to the text file with upload logs
upload_log_file = 'upload_pngs_output.txt'
# Name of the JSONL file containing your requests
input_jsonl_file = 'batch_requests.jsonl'

# Your single, consistent prompt for all images
processing_prompt = """
I'm going to give you an image from a scientific experiment. The image is part of a series capturing a temporal process. Please analyze this image and do the following:

1. Identify the main subject and its state.
2. Look for the presence of a specific anomaly, which looks like a small, dark, circular shape.
3. If the anomaly is detected, provide a detailed JSON response in this exact format:
   {
       "filename": "name_of_image.png",
       "anomaly_detected": true,
       "location": "A description of where the anomaly is located in the image (e.g., top-left, center, near a specific feature).",
       "size_estimate": "An estimate of its size relative to other objects in the image.",
       "notes": "Any other pertinent observations about the anomaly or the image."
   }
4. If the anomaly is NOT detected, provide a simple JSON response:
   {
       "filename": "name_of_image.png",
       "anomaly_detected": false,
       "notes": "No anomaly was detected in this image."
   }
"""

prompt = """
The file is a light microscope image of a Vero E6 cell culture.
The image was taken at either 10x and 20x magnification using bright field or phase contrast modes.
The scale bar in the image is either 400 micrometers for 10x, or 200 micrometers for 20x.
The image comes from an experiment in which there were two experimental paths that differed in the culture process.
For the most part, the culture medium follows the cell providers recommended medium formulation.
Both cultures were seeded at the same density on day one, and maintained for five days without medium change.
Over the five days the cultures were maintained in typical conditions of a cell culture incubation device (e.g. temperature, humidity, CO2 levels, etc.)
Please answer these questions providing as many details as possible:
1. Provide your general understanding of the image.
2. Provide the healty cell count, non-healthy cell count, and dead cell count.
3. Estimate the confluency.
4. Search for evidence of any form of CPE. Describe in detail
2. Please list and explain any additional information that you would require or find helpful to provide better feedback about the dataset.
3. Please provide a table that details any presence of CPE detected. The table should have as columns the following headings:
Culture A or B, Day, image number, CPE type, Approximate location of CPE within the image, any comments about this finding.
For example, one line in the table may be:
A, 1, 101, Cell Rounding, 4 o'clock near the edge, There are several cells in the same area exhibiting similar CPE.
4. Please provide your best assessment about what the difference in the culture process was between cultures A and B. Please be as detailed as possible.
"""

# Initialize the Gemini model
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# --- Helper Function to Create the URI -> Filename Dictionary ---
def create_uri_to_filename_dict(log_file_path):
    uri_map = {}
    pattern = re.compile(r"Uploaded '(?P<filename>.*?)' with ID: (?P<file_uri>files/.*)")
    
    with open(log_file_path, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                data = match.groupdict()
                uri_map[data['file_uri']] = data['filename']
                
    return uri_map

# This list will store the JSON objects from successful detections
positive_detections = []

# --- Main Script ---
# Create the URI to filename mapping
print("Parsing upload log to create filename lookup...")
uri_to_filename = create_uri_to_filename_dict(upload_log_file)
print("Filename lookup dictionary created. Total entries:", len(uri_to_filename))

# Start the processing loop
print(f"Starting to process images from '{input_jsonl_file}'...")

with open(input_jsonl_file, 'r') as f:
    for line in f:
        request_data = json.loads(line)
        request_content = request_data['request']['contents']['parts']
        file_uri = request_content[1]['fileData']['uri']
        
        # Get the original filename from our lookup dictionary
        original_filename = uri_to_filename.get(file_uri, "unknown_file")
        print(f"Processing image: {original_filename} (URI: {file_uri})...")
        
        try:
            # Send the API request with the consistent prompt
            response = model.generate_content([
                processing_prompt.replace("name_of_image.png", original_filename),
                genai.get_file(file_uri)
            ])
            
            # Process and parse the JSON response
            response_text = response.text.strip('`').strip('json').strip()
            result_data = json.loads(response_text)
            
            if result_data.get('anomaly_detected', False):
                positive_detections.append(result_data)
                print(f"  - Positive detection found in {original_filename}! ✅")
            else:
                print(f"  - No anomaly detected in {original_filename}. 🟡")
                
        except json.JSONDecodeError as e:
            print(f"  - Error parsing JSON from response for {original_filename}: {e}")
            print(f"  - Full response: {response.text}")
        except Exception as e:
            print(f"  - An error occurred during API call for {original_filename}: {e}")

# --- Tabulated Results with Pandas ---
if positive_detections:
    print("\n--- Creating Tabulated Results ---")
    df = pd.DataFrame(positive_detections)
    
    # Sort the dataframe by filename to maintain the temporal order
    df['image_number'] = df['filename'].str.extract(r'(\d+)').astype(int)
    df = df.sort_values(by='image_number').drop(columns='image_number')
    
    print(df.to_string(index=False))
    df.to_csv('anomaly_detections_summary.csv', index=False)
    print("\nResults saved to 'anomaly_detections_summary.csv'")

else:
    print("\nNo anomalies were found in any of the images. 🔬")