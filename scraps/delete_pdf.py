import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

# Get the API key from the environment variable
os.environ['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

# The file ID of the file you want to delete
# Replace 'your_file_id_here' with the actual ID you got from the upload script
file_id = 'files/l0qy0ln1hzga'

try:
    print(f"Attempting to delete file with ID: {file_id}...")
    genai.delete_file(file_id)
    print(f"File '{file_id}' has been successfully deleted. 👍")
except Exception as e:
    print(f"An error occurred while deleting the file: {e}")