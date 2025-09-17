import google.generativeai as genai
import os
import json
import time
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

# Get the API key from the environment variable
os.environ['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

# Path to the folder containing your images
image_folder = 'converted_pngs'
# Name of the output JSONL file
output_jsonl = 'batch_requests.jsonl'

# --- The Script ---
print(f"Starting file upload and JSONL creation for images in '{image_folder}'...")

# Initialize a list to hold all the request objects
requests = []

# Open the JSONL file in write mode
with open(output_jsonl, 'w') as f:
    # Iterate through all files in the specified folder
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            full_path = os.path.join(image_folder, filename)
            
            # --- A. Upload the file to the Gemini API ---
            try:
                print(f"Uploading '{filename}'...")
                uploaded_file = genai.upload_file(path=full_path)
                print(f"Uploaded '{filename}' with ID: {uploaded_file.name}")
                
                # Wait for the file to become 'ACTIVE'
                while uploaded_file.state.name == 'PROCESSING':
                    print("  - Waiting for file to be processed...")
                    time.sleep(5)  # Wait 5 seconds before checking again
                    uploaded_file = genai.get_file(uploaded_file.name)
                
                # --- B. Create the request dictionary for the JSONL file ---
                # This dictionary contains the prompt and a reference to the uploaded file
                request_dict = {
                    "request": {
                        "contents": {
                            "role": "user",
                            "parts": [
                                # Your prompt for each image goes here
                                {"text": "Describe the subject of this image in detail."}, 
                                # The reference to the uploaded file's URI
                                {"fileData": {"mimeType": uploaded_file.mime_type, "uri": uploaded_file.uri}}
                            ]
                        }
                    }
                }
                
                # --- C. Write the request as a single line in the JSONL file ---
                json.dump(request_dict, f)
                f.write('\n')
                
            except Exception as e:
                print(f"An error occurred while processing '{filename}': {e}")
                # Continue to the next file even if one fails
                continue

print(f"Finished processing all images. JSONL file created at '{output_jsonl}'.")