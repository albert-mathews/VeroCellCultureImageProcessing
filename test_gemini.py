import os
from dotenv import load_dotenv
from google import genai

# This line is crucial: it tells Python to find and load your .env file
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)
# client.ListModels()
response = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents="Hello! Are you online and ready to analyze some cells?"
)

print(response.text)