import os
from dotenv import load_dotenv
from openai import OpenAI  # Use OpenAI-compatible library for xAI

# This line is crucial: it tells Python to find and load your .env file
load_dotenv()

api_key = os.getenv("XAI_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

# Test the connection with a simple chat completion
response = client.chat.completions.create(
    model="grok-4.2",  # Use the latest Grok model; adjust if needed (e.g., 'grok-2-vision-1212' for vision)
    messages=[{"role": "user", "content": "Hello! Are you online and ready to analyze some cells?"}],
    temperature=0  # Optional: for consistent responses
)

print(response.choices[0].message.content)