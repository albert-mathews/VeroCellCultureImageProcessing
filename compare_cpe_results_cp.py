import json
import os
import pandas as pd
from typing import Dict, Any

JSON_FILES = {
    "Claude": "cpe_detection_results_claude.json",
    "ChatGPT": "cpe_detection_results_chatgpt.json",
    "Gemini": "cpe_detection_results_gemini.json",
    "Grok": "cpe_detection_results_grok.json",
    "CRO": "cpe_detection_results_cro.json",
    "OpenAI": "cpe_detection_results_openai.json",
}

def load_json(filename: str)