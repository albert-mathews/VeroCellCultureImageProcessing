import os
import io
import json
import math
import time
import base64
from collections import Counter

import numpy as np
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI

# --- Configuration ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

image_folder = "converted_pngs"
results_filename = "cpe_detection_results_chatgpt.json"

MODEL_NAME = "gpt-4o"
TILE_GRID = 4                 # 4x4 grid = 16 tiles per image
CONSENSUS_RUNS = 3            # number of repeated analyses per tile
POSITIVE_TILE_THRESHOLD = 0.10  # image positive if >=10% of tiles are positive
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

# Optional: set to True if you want to skip tiles that are almost blank/background.
SKIP_LOW_DETAIL_TILES = False
LOW_DETAIL_STD_THRESHOLD = 4.0

JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "cpe_detection",
        "schema": {
            "type": "object",
            "properties": {
                "cpe_detected": {"type": "boolean"},
                "cpe_types": {
                    "type": ["array", "null"],
                    "items": {"type": "string"}
                },
                "viability": {
                    "type": ["number", "null"],
                    "minimum": 0,
                    "maximum": 100
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "full_response_text": {"type": "string"}
            },
            "required": [
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


Before determining whether CPE is present, perform a structured visual inspection of the image.

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

Step 5 — Decision
Using the observations above, determine if cytopathic effect (CPE) is present.

Only after performing these inspection steps should you produce the final JSON result.

Your secondary task is to estimate viability of the visible culture region, i.e. the ratio of live cells divided by total cells.
These images do not have trypan blue stain, so estimate viability from morphology only.

If image quality or field content prevents confident detection, reflect that in the confidence score and summary.
Be conservative and avoid overcalling weak or ambiguous CPE.

Return only a JSON object with this structure:
{
    "cpe_detected": boolean,
    "cpe_types": string[] | null,
    "viability": number,
    "confidence": number,
    "full_response_text": string
}

Instructions for each key:
- cpe_detected: true if any form of CPE is detected in the visible region; otherwise false.
- cpe_types: list of detected morphologies, or null if none are present.
- viability: numeric estimate from 0 to 100.
- confidence: numeric confidence from 0.0 to 1.0 for your own assessment.
- full_response_text: concise summary of the visible findings.
""".strip()

few_shot_examples = [
    {
        "image_path": "converted_pngs/EXP_path1_passage4_401.png",
        "expected_output": {
            "cpe_detected": False,
            "cpe_types": None,
            "viability": None,
            "full_response_text": "Cells are adherent and are growing in clusters that are beginning to merge. Very few bright dividing cells. A mitotic figure close to the bottom left corner of the field."
            "confidence": 0.90,
        }
    },
    {
        "image_path": "converted_pngs/EXP_path2_passage4_402.png",
        "expected_output": {
            "cpe_detected": True,
            "cpe_types": ["rounding", "vacuolation", "refractile cells", "dying cells"],
            "viability": None,
            "full_response_text": "Few small clusters present with some bright spots (vacuoles). There is a pair of dividing cells at 7 o’clock. Multiple single cells with some degree of spreading. Multiple rounded cells. Some cells appear rounded and refractile, which could indicate potentially dying cells (6 o’clock)."
            "confidence": 0.86,
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


def image_file_to_b64(path: str) -> str:
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def pil_image_to_b64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def build_messages(target_image_b64: str):
    messages = [
        {
            "role": "developer",
            "content": "You are a virology microscopy expert. Return only valid JSON that matches the provided schema."
        }
    ]

    for example in few_shot_examples:
        image_path = example["image_path"]
        if not os.path.exists(image_path):
            print(f"Warning: few-shot example not found, skipping: {image_path}")
            continue

        example_b64 = image_file_to_b64(image_path)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Example microscopy image and its correct JSON analysis:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{example_b64}"}}
            ]
        })
        messages.append({
            "role": "assistant",
            "content": json.dumps(example["expected_output"])
        })

    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": common_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{target_image_b64}"}}
        ]
    })
    return messages


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
        "dying cells": "dying cells",
        "rounding": "rounding",
        "vacuolation": "vacuolation",
        "detached": "detachment",
        "detachment": "detachment",
        "detached cells": "detachment",
        "lysis": "lysis",
        "granularity": "granularity",
        "refractile": "refractile cells",
        "refractile cells": "refractile cells",
        "syncytium formation": "syncytium formation",
        "intranuclear inclusion bodies": "intranuclear inclusion bodies",
        "pyknosis": "pyknosis",
        "karyorrhexis": "karyorrhexis"
    }

    cleaned = []
    for item in cpe_types:
        if item is None:
            continue
        text = str(item).strip().lower()
        cleaned.append(canonical_map.get(text, text))
    return cleaned


def call_model_with_retries(messages):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0,
                response_format=JSON_SCHEMA,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise last_error


def analyze_tile(tile_image: Image.Image) -> dict:
    tile_b64 = pil_image_to_b64(tile_image)
    pass_results = []

    for _ in range(CONSENSUS_RUNS):
        result = call_model_with_retries(build_messages(tile_b64))
        result["cpe_types"] = normalize_cpe_types(result.get("cpe_types"))
        pass_results.append(result)

    positive_votes = sum(1 for r in pass_results if bool(r.get("cpe_detected")))
    negative_votes = CONSENSUS_RUNS - positive_votes
    is_positive = positive_votes > negative_votes
    majority_votes = max(positive_votes, negative_votes)
    consensus_strength = majority_votes / CONSENSUS_RUNS

    viability_mean = float(np.mean([float(r["viability"]) for r in pass_results]))
    model_confidence_mean = float(np.mean([float(r["confidence"]) for r in pass_results]))

    positive_type_counter = Counter()
    positive_summaries = []
    for r in pass_results:
        if r.get("cpe_detected"):
            positive_type_counter.update(r.get("cpe_types") or [])
            positive_summaries.append(r.get("full_response_text", ""))

    if is_positive and positive_type_counter:
        cpe_types = [
            cpe_type
            for cpe_type, count in positive_type_counter.most_common()
            if count >= math.ceil(CONSENSUS_RUNS / 2)
        ]
        if not cpe_types:
            cpe_types = [positive_type_counter.most_common(1)[0][0]]
    else:
        cpe_types = []

    if is_positive and positive_summaries:
        summary = positive_summaries[0]
    else:
        summary = pass_results[0].get("full_response_text", "")

    return {
        "tile_positive": is_positive,
        "positive_votes": positive_votes,
        "negative_votes": negative_votes,
        "consensus_strength": round(consensus_strength, 4),
        "model_confidence_mean": round(model_confidence_mean, 4),
        "viability_mean": round(viability_mean, 2),
        "cpe_types": cpe_types,
        "summary": summary,
    }


def aggregate_image_result(tile_results: list[dict]) -> dict:
    if not tile_results:
        return {
            "cpe_detected": False,
            "cpe_types": None,
            "viability": 0,
            "confidence": 0,
            "positive_tiles": 0,
            "total_tiles": 0,
            "positive_tile_fraction": 0,
            "full_response_text": "No usable tiles were analyzed.",
            "tile_results": []
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

    if image_positive and positive_type_counter:
        cpe_types = [name for name, _ in positive_type_counter.most_common()]
    else:
        cpe_types = None

    positive_consensus = (
        float(np.mean([t["consensus_strength"] for t in positive_tile_details]))
        if positive_tile_details else 0.0
    )
    positive_model_conf = (
        float(np.mean([t["model_confidence_mean"] for t in positive_tile_details]))
        if positive_tile_details else avg_model_confidence
    )

    if image_positive:
        extent_score = min(positive_fraction / 0.25, 1.0)
        confidence = (
            0.45 * extent_score +
            0.30 * positive_consensus +
            0.25 * positive_model_conf
        )
    else:
        negative_fraction = 1.0 - positive_fraction
        confidence = (
            0.45 * negative_fraction +
            0.30 * avg_consensus_strength +
            0.25 * avg_model_confidence
        )

    confidence = round(float(max(0.0, min(1.0, confidence))), 4)

    if image_positive:
        strongest_tiles = sorted(
            positive_tile_details,
            key=lambda t: (t["consensus_strength"], t["model_confidence_mean"]),
            reverse=True,
        )[:3]
        strongest_tile_ids = [t["tile_id"] for t in strongest_tiles]
        summary = (
            f"CPE detected in {positive_tiles}/{total_tiles} tiles "
            f"({positive_fraction:.1%}). Most supported positive tiles: {', '.join(strongest_tile_ids)}."
        )
    else:
        summary = (
            f"No convincing CPE detected across {total_tiles} analyzed tiles. "
            f"Positive tile fraction was {positive_fraction:.1%}."
        )

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
            "Image Name": image_name,
            "CPE Detected": result.get("cpe_detected"),
            "Confidence": result.get("confidence"),
            "Positive Tiles": result.get("positive_tiles"),
            "Total Tiles": result.get("total_tiles"),
            "Viability": result.get("viability"),
            "CPE Types": ", ".join(result.get("cpe_types") or []) if result.get("cpe_types") else None,
        })

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


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

            for tile in tiles:
                tile_id = tile["tile_id"]
                tile_image = tile["image"]

                if not tile_has_enough_detail(tile_image):
                    print(f"  Skipping low-detail tile {tile_id}")
                    continue

                tile_result = analyze_tile(tile_image)
                tile_result["tile_id"] = tile_id
                tile_result["row"] = tile["row"]
                tile_result["col"] = tile["col"]
                tile_results.append(tile_result)

                print(
                    f"  {tile_id}: positive={tile_result['tile_positive']} | "
                    f"votes={tile_result['positive_votes']}/{CONSENSUS_RUNS} | "
                    f"conf={tile_result['model_confidence_mean']:.2f} | "
                    f"viability={tile_result['viability_mean']:.1f}"
                )

            image_result = aggregate_image_result(tile_results)
            all_results[filename] = image_result

            print(
                f"Finished {filename}. CPE detected: {image_result['cpe_detected']} | "
                f"confidence={image_result['confidence']:.2f} | "
                f"positive tiles={image_result['positive_tiles']}/{image_result['total_tiles']} | "
                f"viability={image_result['viability']:.1f}"
            )

            with open(results_filename, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=4)

        except Exception as exc:
            print(f"An error occurred while processing {filename}: {exc}")
            all_results[filename] = {
                "cpe_detected": False,
                "cpe_types": None,
                "viability": 0,
                "confidence": 0,
                "positive_tiles": 0,
                "total_tiles": 0,
                "positive_tile_fraction": 0,
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
