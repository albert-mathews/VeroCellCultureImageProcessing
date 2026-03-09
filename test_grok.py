import os
from dotenv import load_dotenv
from openai import OpenAI

# This line is crucial: it tells Python to find and load your .env file
load_dotenv()

api_key = os.getenv("XAI_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

try:
    # Test the connection with a simple chat completion
    response = client.chat.completions.create(
        model="grok-4-1-fast-reasoning",  # Valid multimodal model (supports vision); alternative: "grok-2-vision-1212"
        messages=[{"role": "user", "content": "Hello! Are you online and ready to analyze some cells?"}],
        temperature=0  # Optional: for consistent responses
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
    print("Tips: Check your API key, billing setup, or try a different model like 'grok-2-vision-1212'. Visit https://docs.x.ai/developers/models for the latest list.")