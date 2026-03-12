# individual_image_grok.py

import os
import io
import json
import math
import time
import base64
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI  # Using OpenAI lib for xAI compatibility

# Import shared functions from the original script (assuming same folder)
from individual_image_chatgpt import (
    load_existing_results,
    image_file_to_b64,
    pil_image_to_b64,
    build_messages,
    split_into_tiles,
    tile_has_enough_detail,
    normalize_cpe_types,
    normalize_culture_state,
    sanitize_model_result,
    analyze_tile,
    aggregate_image_result,
    print_summary_table,
    process_single_tile,
)

# --- Configuration ---
load_dotenv()
client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")  # xAI endpoint

image_folder = "converted_pngs"
results_filename = "cpe_detection_results_grok.json"

MODEL_NAME = "grok-4.2"  # Latest with vision; fallback to 'grok-2-vision-1212' if needed
TILE_GRID = 4                       # 4x4 grid = 16 tiles per image
CONSENSUS_RUNS = 1                  # Reduced for Grok's consistency; increase if needed
POSITIVE_TILE_THRESHOLD = 0.10      # image positive if >=10% of tiles are clear CPE
EARLY_STRESS_TILE_THRESHOLD = 0.20  # image flagged early stress if >=20% tiles are early_stress and not CPE+
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
MAX_TILE_WORKERS = 8                # parallel tile workers per image; lower if you hit rate limits

# Optional: skip tiles that are nearly blank/background
SKIP_LOW_DETAIL_TILES = False
LOW_DETAIL_STD_THRESHOLD = 4.0

JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "cpe_detection",
        "schema": {
            "type": "object",
            "properties": {
                "culture_state": {
                    "type": "string",
                    "enum": ["healthy", "early_stress", "clear_cpe"]
                },
                "cpe_detected": {"type": "boolean"},
                "cpe_types": {
                    "type": ["array", "null"],
                    "items": {"type": "string"}
                },
                "viability": {
                    "type": ["number", "null"]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "full_response_text": {"type": "string"}
            },
            "required": [
                "culture_state",
                "cpe_detected",
                "cpe_types",
                "viability",
                "confidence",
                "full_response_text"
            ],
            "additionalProperties": False
        }
    }
}

common_prompt = """
You are a virology specialist. Your specialty is analyzing light microscope images of Vero E6 cell cultures.

Analyze the provided image region of a cell culture. This image may be either a full microscope field or a tile cropped from a larger field.
The images are of Vero E6 cells, cultivated in typical growth medium.
The images are taken using bright field or phase contrast microscopy.
The magnification is either 10x or 20x.

Your primary task is to detect the presence of CPE (cytopathic effect).

Specific CPE morphologies you should be looking for:
- dying cells
- rounding
- vacuolation
- detached cells / detachment
- granularity
- refractile cells

Other CPE morphologies you should look for:
- syncytium formation
- intranuclear inclusion bodies
- pyknosis
- karyorrhexis

Before determining whether CPE is present, reason step-by-step through a structured visual inspection of the image. Explain your reasoning briefly in the full_response_text, but only output the final JSON.

Step 1 — Cell density
Estimate whether the monolayer is sparse, moderate, or dense.

Step 2 — Cell morphology
Look for:
- rounding
- detachment
- vacuolation
- refractile cells
- syncytium formation
- nuclear fragmentation
- irregular cell borders
- micro-gaps in the monolayer
- uneven local cell density

Step 3 — Spatial clustering
Determine if abnormal cells appear:
- isolated
- clustered
- widespread

Step 4 — Cell viability cues
Look for signs of dying or stressed cells such as:
- refractility
- irregular cell borders
- shrinking or swelling
- partial loss of adherence
- thinning of the monolayer

Step 5 — Early stress assessment
Before labeling clear CPE, evaluate whether the image instead shows early cytopathic stress patterns.
Early stress patterns may include:
- increased refractile cells
- slight rounding without full detachment
- irregular cell borders
- micro-gaps forming in an otherwise confluent monolayer
- uneven cell density
- small clusters of abnormal cells

Classify the visible region into one of:
- "healthy" = no convincing abnormal morphology
- "early_stress" = abnormal/stressed morphology is present, but not enough for clear CPE
- "clear_cpe" = convincing cytopathic effect is present

When unsure between healthy and early_stress, choose early_stress if abnormal morphology is present.
Be conservative and avoid overcalling weak or ambiguous clear CPE.

Step 6 — Final decision
Only after reasoning through the steps above should you produce the final JSON result.

Your secondary task is to estimate viability of the visible culture region, i.e. the ratio of live cells divided by total cells.
These images do not have trypan blue stain, so estimate viability from morphology only.
If viability cannot be estimated reliably from the visible region, set viability to null.

If image quality or field content prevents confident detection, reflect that in the confidence score and summary.

Return only a JSON object with this structure:
{
    "culture_state": "healthy" | "early_stress" | "clear_cpe",
    "cpe_detected": boolean,
    "cpe_types": string[] | null,
    "viability": number | null,
    "confidence": number,
    "full_response_text": string
}

Instructions for each key:
- culture_state: healthy, early_stress, or clear_cpe.
- cpe_detected: true only if clear CPE is present in the visible region; false otherwise.
- cpe_types: list of detected morphologies, or null if none are present.
- viability: numeric estimate from 0 to 100, or null if not reliably inferable.
- confidence: numeric confidence from 0.0 to 1.0 for your own assessment.
- full_response_text: concise summary of the visible findings, including brief reasoning.
""".strip()

few_shot_examples = [
    {
        "image_path": "converted_pngs/EXP_path1_passage4_401.png",
        "expected_output": {
            "culture_state": "healthy",
            "cpe_detected": False,
            "cpe_types": None,
            "viability": None,
            "confidence": 0.90,
            "full_response_text": "Cells are adherent and growing in clusters that are beginning to merge. Very few bright dividing cells are present. No convincing cytopathic effect is visible."
        }
    },
    {
        "image_path": "converted_pngs/EXP_path2_passage4_402.png",
        "expected_output": {
            "culture_state": "clear_cpe",
            "cpe_detected": True,
            "cpe_types": ["rounding", "vacuolation", "refractile cells", "dying cells"],
            "viability": None,
            "confidence": 0.86,
            "full_response_text": "Few small clusters are present with bright vacuolar features. Multiple rounded and refractile cells are visible, including cells suggestive of dying morphology. Findings are consistent with clear cytopathic effect."
        }
    }
]

def call_model_with_retries(messages):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0,  # For Grok consistency
                response_format=JSON_SCHEMA,
            )
            parsed = json.loads(response.choices[0].message.content)
            return sanitize_model_result(parsed)
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise last_error

def main():
    all_results = load_existing_results(results_filename)

    print("Starting image processing... 🔬")
    for filename in sorted(os.listdir(image_folder)):
        if not filename.lower().endswith(IMAGE_EXTENSIONS):
            continue
        if filename in all_results:
            print(f"Skipping already processed {filename}")
            continue

        full_path = os.path.join(image_folder, filename)
        print(f"\nProcessing {filename}...")

        try:
            tiles = split_into_tiles(full_path, grid=TILE_GRID)
            tile_results = []
            worker_count = min(MAX_TILE_WORKERS, len(tiles)) or 1

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_to_tile = {
                    executor.submit(process_single_tile, tile): tile
                    for tile in tiles
                }

                for future in as_completed(future_to_tile):
                    tile = future_to_tile[future]
                    tile_id = tile["tile_id"]
                    try:
                        tile_result = future.result()
                        if tile_result is None:
                            continue
                        if tile_result.get("skipped"):
                            print(f"  Skipping low-detail tile {tile_id}")
                            continue

                        tile_results.append(tile_result)
                        print(
                            f"  {tile_id}: state={tile_result['tile_state']} | "
                            f"clear_cpe_votes={tile_result['positive_votes']}/{CONSENSUS_RUNS} | "
                            f"stress_votes={tile_result['early_stress_votes']}/{CONSENSUS_RUNS} | "
                            f"conf={tile_result['model_confidence_mean']:.2f} | "
                            f"viability={tile_result['viability_mean'] if tile_result['viability_mean'] is not None else 'null'}"
                        )
                    except Exception as exc:
                        print(f"  Tile {tile_id} failed: {exc}")

            tile_results.sort(key=lambda x: (x["row"], x["col"]))
            image_result = aggregate_image_result(tile_results)
            all_results[filename] = image_result

            print(
                f"Finished {filename}. State: {image_result['culture_state']} | "
                f"CPE detected: {image_result['cpe_detected']} | "
                f"confidence={image_result['confidence']:.2f} | "
                f"positive tiles={image_result['positive_tiles']}/{image_result['total_tiles']} | "
                f"stress tiles={image_result['early_stress_tiles']}/{image_result['total_tiles']} | "
                f"viability={image_result['viability'] if image_result['viability'] is not None else 'null'}"
            )

            with open(results_filename, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=4)

        except Exception as exc:
            print(f"An error occurred while processing {filename}: {exc}")
            all_results[filename] = {
                "culture_state": "healthy",
                "cpe_detected": False,
                "cpe_types": None,
                "viability": None,
                "confidence": 0,
                "positive_tiles": 0,
                "early_stress_tiles": 0,
                "total_tiles": 0,
                "positive_tile_fraction": 0,
                "early_stress_tile_fraction": 0,
                "full_response_text": f"Error: {exc}",
                "tile_results": []
            }
            with open(results_filename, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=4)

    print("\nProcessing complete! 🎉")
    print("\n--- Tabulated CPE Detections ---")
    print_summary_table(all_results)
    print(f"\nDictionary of results saved to '{results_filename}'")

if __name__ == "__main__":
    main()