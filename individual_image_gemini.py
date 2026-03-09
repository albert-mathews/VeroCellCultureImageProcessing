import os
import json
import math
import time
from collections import Counter
from typing import Optional, List

import numpy as np
import pandas as pd
from PIL import Image
from dotenv import load_dotenv

# Use the new Google GenAI SDK
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- Configuration ---
load_dotenv()

# Automatically fall back to OPENAI_API_KEY if GEMINI_API_KEY isn't set yet
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

image_folder = "converted_pngs"
results_filename = "cpe_detection_results_gemini.json"

MODEL_NAME = "gemini-3.1-pro-preview"
TILE_GRID = 4                 
CONSENSUS_RUNS = 3            
POSITIVE_TILE_THRESHOLD = 0.10  
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

SKIP_LOW_DETAIL_TILES = False
LOW_DETAIL_STD_THRESHOLD = 4.0

# --- Pydantic Schemas for Strict JSON Output ---
class TileResultModel(BaseModel):
    tile_id: str = Field(description="The exact Tile ID provided, e.g., 'r1c1'")
    visual_reasoning: str = Field(description="Step-by-step visual observations (density, morphology, clustering) before deciding.")
    cpe_detected: bool = Field(description="True if any form of CPE is detected; otherwise false.")
    cpe_types: Optional[List[str]] = Field(description="List of detected morphologies, or null.", default=None)
    viability: Optional[float] = Field(description="Numeric estimate of viability from 0 to 100.", default=None)
    confidence: float = Field(description="Confidence score from 0.0 to 1.0.")
    full_response_text: str = Field(description="Concise summary of the visible findings.")

class BatchTileResponse(BaseModel):
    results: List[TileResultModel]

# --- System Instructions ---
common_prompt = """
You are a virology specialist. Your specialty is analyzing light microscope images of Vero E6 cell cultures.
Analyze the provided image regions of a cell culture. 
The images are of Vero E6 cells, cultivated in typical growth medium, taken using bright field or phase contrast microscopy (10x or 20x).

Your primary task is to detect the presence of CPE (cytopathic effect).
Specific CPE morphologies to look for:
- dying cells, rounding, vacuolation, detached cells / detachment, granularity, refractile cells
Other CPE morphologies:
- syncytium formation, intranuclear inclusion bodies, pyknosis, karyorrhexis

For each tile, perform a structured visual inspection (Cell density, Cell morphology, Spatial clustering, Viability cues).
Document these findings in the 'visual_reasoning' field before determining if CPE is present.

Your secondary task is to estimate viability from morphology only (ratio of live cells divided by total cells).
Be conservative and avoid overcalling weak or ambiguous CPE.
"""

few_shot_examples = [
    {
        "image_path": "converted_pngs/EXP_path1_passage4_401.png",
        "expected_output": {
            "cpe_detected": False,
            "cpe_types": None,
            "viability": None,
            "full_response_text": "Cells are adherent and are growing in clusters that are beginning to merge. Very few bright dividing cells. A mitotic figure close to the bottom left corner of the field.",
            "confidence": 0.90
        }
    },
    {
        "image_path": "converted_pngs/EXP_path2_passage4_402.png",
        "expected_output": {
            "cpe_detected": True,
            "cpe_types": ["rounding", "vacuolation", "refractile cells", "dying cells"],
            "viability": None,
            "full_response_text": "Few small clusters present with some bright spots (vacuoles). There is a pair of dividing cells at 7 o’clock. Multiple single cells with some degree of spreading. Multiple rounded cells. Some cells appear rounded and refractile, which could indicate potentially dying cells.",
            "confidence": 0.86
        }
    }
]

def load_existing_results(path: str) -> dict:
    all_results = {}
    if os.path.exists(path):
        load_choice = input(f"'{path}' found. Do you want to load it? (yes/no): ").strip().lower()
        if load_choice == "yes":
            with open(path, "r", encoding="utf-8") as f:
                all_results = json.load(f)
            print("Loaded previous results. Skipping processed images.")
        else:
            print("Starting fresh. All images will be re-uploaded.")
    return all_results

def split_into_tiles(image_path: str, grid: int = TILE_GRID):
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    tile_width = width // grid
    tile_height = height // grid

    tiles = []
    for row in range(grid):
        for col in range(grid):
            left = col * tile_width
            top = row * tile_height
            right = width if col == grid - 1 else (col + 1) * tile_width
            bottom = height if row == grid - 1 else (row + 1) * tile_height
            tile = img.crop((left, top, right, bottom))
            tiles.append({
                "tile_id": f"r{row + 1}c{col + 1}",
                "row": row + 1,
                "col": col + 1,
                "image": tile
            })
    return tiles

def tile_has_enough_detail(tile_image: Image.Image) -> bool:
    if not SKIP_LOW_DETAIL_TILES:
        return True
    arr = np.asarray(tile_image).astype(np.float32)
    return float(arr.std()) >= LOW_DETAIL_STD_THRESHOLD

def normalize_cpe_types(cpe_types):
    if not cpe_types:
        return []
    canonical_map = {
        "dying cells": "dying cells", "rounding": "rounding", "vacuolation": "vacuolation",
        "detached": "detachment", "detachment": "detachment", "detached cells": "detachment",
        "lysis": "lysis", "granularity": "granularity", "refractile": "refractile cells",
        "refractile cells": "refractile cells", "syncytium formation": "syncytium formation",
        "intranuclear inclusion bodies": "intranuclear inclusion bodies",
        "pyknosis": "pyknosis", "karyorrhexis": "karyorrhexis"
    }
    cleaned = []
    for item in cpe_types:
        if item is None: continue
        text = str(item).strip().lower()
        cleaned.append(canonical_map.get(text, text))
    return cleaned

def build_batch_contents(tiles: list[dict]):
    """Constructs a multimodal payload of interleaved text and PIL Images."""
    contents = [
        "You are analyzing a batch of tiles cropped from a larger cell culture image. "
        "For each tile provided below, perform your analysis and return the results in the requested JSON array."
    ]
    
    for example in few_shot_examples:
        image_path = example["image_path"]
        if os.path.exists(image_path):
            img = Image.open(image_path).convert("RGB")
            contents.extend(["Example Tile:", img, "Correct JSON Output for this Example Tile:"])
            
            example_out = example["expected_output"].copy()
            example_out["tile_id"] = "example_1"
            example_out["visual_reasoning"] = "Observed specific cellular structures matching the final output."
            contents.append(json.dumps([example_out]))

    contents.append("Now, perform the analysis on the following target tiles:")
    
    for tile in tiles:
        contents.extend([f"Tile ID: {tile['tile_id']}", tile["image"]])
        
    return contents

def call_model_with_retries(contents):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=common_prompt,
                    response_mime_type="application/json",
                    response_schema=BatchTileResponse,
                    temperature=0.0,
                )
            )
            return json.loads(response.text)
        except Exception as exc:
            last_error = exc
            print(f"      Attempt {attempt} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise last_error

def analyze_tiles_batch(valid_tiles: list[dict]) -> list[dict]:
    pass_results_by_tile = {t["tile_id"]: [] for t in valid_tiles}
    
    for run in range(CONSENSUS_RUNS):
        print(f"    Consensus Run {run + 1}/{CONSENSUS_RUNS}...")
        contents = build_batch_contents(valid_tiles)
        batch_result = call_model_with_retries(contents)
        
        for res in batch_result.get("results", []):
            tile_id = res.get("tile_id")
            if tile_id in pass_results_by_tile:
                pass_results_by_tile[tile_id].append(res)
                
    final_tile_results = []
    for tile in valid_tiles:
        tile_id = tile["tile_id"]
        pass_results = pass_results_by_tile[tile_id]
        
        if not pass_results:
             continue
             
        for r in pass_results:
            r["cpe_types"] = normalize_cpe_types(r.get("cpe_types"))
            
        positive_votes = sum(1 for r in pass_results if bool(r.get("cpe_detected")))
        negative_votes = len(pass_results) - positive_votes
        is_positive = positive_votes > negative_votes
        majority_votes = max(positive_votes, negative_votes)
        consensus_strength = majority_votes / len(pass_results)

        viabilities = [float(r["viability"]) for r in pass_results if r.get("viability") is not None]
        viability_mean = float(np.mean(viabilities)) if viabilities else 0.0
        
        confidences = [float(r["confidence"]) for r in pass_results if r.get("confidence") is not None]
        model_confidence_mean = float(np.mean(confidences)) if confidences else 0.0

        positive_type_counter = Counter()
        positive_summaries = []
        for r in pass_results:
            if r.get("cpe_detected"):
                positive_type_counter.update(r.get("cpe_types") or [])
                positive_summaries.append(r.get("full_response_text", ""))

        if is_positive and positive_type_counter:
            cpe_types = [
                cpe_type for cpe_type, count in positive_type_counter.most_common()
                if count >= math.ceil(len(pass_results) / 2)
            ]
            if not cpe_types:
                cpe_types = [positive_type_counter.most_common(1)[0][0]]
        else:
            cpe_types = []

        summary = positive_summaries[0] if (is_positive and positive_summaries) else pass_results[0].get("full_response_text", "")

        final_tile_results.append({
            "tile_id": tile_id,
            "row": tile["row"],
            "col": tile["col"],
            "tile_positive": is_positive,
            "positive_votes": positive_votes,
            "negative_votes": negative_votes,
            "consensus_strength": round(consensus_strength, 4),
            "model_confidence_mean": round(model_confidence_mean, 4),
            "viability_mean": round(viability_mean, 2),
            "cpe_types": cpe_types,
            "summary": summary,
        })
        
    return final_tile_results

def aggregate_image_result(tile_results: list[dict]) -> dict:
    if not tile_results:
        return {
            "cpe_detected": False, "cpe_types": None, "viability": 0, "confidence": 0,
            "positive_tiles": 0, "total_tiles": 0, "positive_tile_fraction": 0,
            "full_response_text": "No usable tiles were analyzed.", "tile_results": []
        }

    total_tiles = len(tile_results)
    positive_tiles = sum(1 for t in tile_results if t["tile_positive"])
    positive_fraction = positive_tiles / total_tiles
    avg_viability = float(np.mean([t["viability_mean"] for t in tile_results]))
    avg_model_confidence = float(np.mean([t["model_confidence_mean"] for t in tile_results]))
    avg_consensus_strength = float(np.mean([t["consensus_strength"] for t in tile_results]))

    image_positive = positive_fraction >= POSITIVE_TILE_THRESHOLD

    positive_type_counter = Counter()
    positive_tile_details = []
    for tile in tile_results:
        if tile["tile_positive"]:
            positive_type_counter.update(tile["cpe_types"])
            positive_tile_details.append(tile)

    cpe_types = [name for name, _ in positive_type_counter.most_common()] if (image_positive and positive_type_counter) else None

    positive_consensus = float(np.mean([t["consensus_strength"] for t in positive_tile_details])) if positive_tile_details else 0.0
    positive_model_conf = float(np.mean([t["model_confidence_mean"] for t in positive_tile_details])) if positive_tile_details else avg_model_confidence

    if image_positive:
        extent_score = min(positive_fraction / 0.25, 1.0)
        confidence = 0.45 * extent_score + 0.30 * positive_consensus + 0.25 * positive_model_conf
    else:
        negative_fraction = 1.0 - positive_fraction
        confidence = 0.45 * negative_fraction + 0.30 * avg_consensus_strength + 0.25 * avg_model_confidence

    confidence = round(float(max(0.0, min(1.0, confidence))), 4)

    if image_positive:
        strongest_tiles = sorted(positive_tile_details, key=lambda t: (t["consensus_strength"], t["model_confidence_mean"]), reverse=True)[:3]
        strongest_tile_ids = [t["tile_id"] for t in strongest_tiles]
        summary = f"CPE detected in {positive_tiles}/{total_tiles} tiles ({positive_fraction:.1%}). Most supported positive tiles: {', '.join(strongest_tile_ids)}."
    else:
        summary = f"No convincing CPE detected across {total_tiles} analyzed tiles. Positive tile fraction was {positive_fraction:.1%}."

    return {
        "cpe_detected": image_positive,
        "cpe_types": cpe_types,
        "viability": round(avg_viability, 2),
        "confidence": confidence,
        "positive_tiles": positive_tiles,
        "total_tiles": total_tiles,
        "positive_tile_fraction": round(positive_fraction, 4),
        "full_response_text": summary,
        "tile_results": tile_results,
    }

def print_summary_table(all_results: dict):
    if not all_results:
        print("No results to display.")
        return
    rows = []
    for image_name, result in all_results.items():
        rows.append({
            "Image Name": image_name, "CPE Detected": result.get("cpe_detected"),
            "Confidence": result.get("confidence"), "Positive Tiles": result.get("positive_tiles"),
            "Total Tiles": result.get("total_tiles"), "Viability": result.get("viability"),
            "CPE Types": ", ".join(result.get("cpe_types") or []) if result.get("cpe_types") else None,
        })
    print(pd.DataFrame(rows).to_string(index=False))

def main():
    all_results = load_existing_results(results_filename)

    print("Starting image processing... 🔬")
    for filename in sorted(os.listdir(image_folder)):
        if not filename.lower().endswith(IMAGE_EXTENSIONS): continue
        if filename in all_results:
            print(f"Skipping already processed {filename}")
            continue

        full_path = os.path.join(image_folder, filename)
        print(f"\nProcessing {filename}...")

        try:
            tiles = split_into_tiles(full_path, grid=TILE_GRID)
            valid_tiles = [t for t in tiles if tile_has_enough_detail(t["image"])]
            
            if not valid_tiles:
                print(f"  Skipping {filename} - no high-detail tiles found.")
                continue

            tile_results = analyze_tiles_batch(valid_tiles)
            
            for t_res in tile_results:
                print(f"  {t_res['tile_id']}: positive={t_res['tile_positive']} | "
                      f"votes={t_res['positive_votes']}/{CONSENSUS_RUNS} | "
                      f"conf={t_res['model_confidence_mean']:.2f} | "
                      f"viability={t_res['viability_mean']:.1f}")

            image_result = aggregate_image_result(tile_results)
            all_results[filename] = image_result

            print(f"Finished {filename}. CPE detected: {image_result['cpe_detected']} | "
                  f"confidence={image_result['confidence']:.2f} | "
                  f"positive tiles={image_result['positive_tiles']}/{image_result['total_tiles']} | "
                  f"viability={image_result['viability']:.1f}")

            with open(results_filename, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=4)

        except Exception as exc:
            print(f"An error occurred while processing {filename}: {exc}")
            all_results[filename] = {
                "cpe_detected": False, "cpe_types": None, "viability": 0, "confidence": 0,
                "positive_tiles": 0, "total_tiles": 0, "positive_tile_fraction": 0,
                "full_response_text": f"Error: {exc}", "tile_results": []
            }
            with open(results_filename, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=4)

    print("\nProcessing complete! 🎉\n--- Tabulated CPE Detections ---")
    print_summary_table(all_results)
    print(f"\nDictionary of results saved to '{results_filename}'")

if __name__ == "__main__":
    main()