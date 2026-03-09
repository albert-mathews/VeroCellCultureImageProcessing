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
from openai import OpenAI

# --- Configuration ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

image_folder = "converted_pngs"
results_filename = "cpe_detection_results_chatgpt.json"

MODEL_NAME = "gpt-4o"
TILE_GRID = 4                       # 4x4 grid = 16 tiles per image
CONSENSUS_RUNS = 2                  # repeated analyses per tile
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
Only after performing the inspection above should you produce the final JSON result.

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
- full_response_text: concise summary of the visible findings.
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


def normalize_culture_state(value):
    if value is None:
        return "healthy"
    text = str(value).strip().lower()
    if text in {"clear_cpe", "cpe", "positive", "clear cpe"}:
        return "clear_cpe"
    if text in {"early_stress", "early stress", "stressed", "stress"}:
        return "early_stress"
    return "healthy"


def sanitize_model_result(result: dict) -> dict:
    result = dict(result)

    result["culture_state"] = normalize_culture_state(result.get("culture_state"))
    result["cpe_detected"] = bool(result.get("cpe_detected"))
    result["cpe_types"] = normalize_cpe_types(result.get("cpe_types"))

    viability = result.get("viability")
    if viability is None:
        result["viability"] = None
    else:
        try:
            viability = float(viability)
            viability = max(0.0, min(100.0, viability))
            result["viability"] = viability
        except Exception:
            result["viability"] = None

    confidence = result.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0
    result["confidence"] = max(0.0, min(1.0, confidence))

    result["full_response_text"] = str(result.get("full_response_text", "")).strip()

    if result["culture_state"] != "clear_cpe":
        result["cpe_detected"] = False

    if result["culture_state"] == "healthy":
        result["cpe_types"] = []

    return result


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
            parsed = json.loads(response.choices[0].message.content)
            return sanitize_model_result(parsed)
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
        pass_results.append(result)

    state_votes = Counter(r["culture_state"] for r in pass_results)
    majority_state, majority_count = state_votes.most_common(1)[0]

    positive_votes = sum(1 for r in pass_results if r["culture_state"] == "clear_cpe")
    early_stress_votes = sum(1 for r in pass_results if r["culture_state"] == "early_stress")
    healthy_votes = sum(1 for r in pass_results if r["culture_state"] == "healthy")

    consensus_strength = majority_count / CONSENSUS_RUNS

    valid_viabilities = [float(r["viability"]) for r in pass_results if r["viability"] is not None]
    viability_mean = float(np.mean(valid_viabilities)) if valid_viabilities else None

    model_confidence_mean = float(np.mean([float(r["confidence"]) for r in pass_results]))

    positive_type_counter = Counter()
    early_stress_type_counter = Counter()
    summaries = []

    for r in pass_results:
        summaries.append(r.get("full_response_text", ""))

        if r["culture_state"] == "clear_cpe":
            positive_type_counter.update(r.get("cpe_types") or [])
        elif r["culture_state"] == "early_stress":
            early_stress_type_counter.update(r.get("cpe_types") or [])

    threshold = math.ceil(CONSENSUS_RUNS / 2)

    if majority_state == "clear_cpe" and positive_type_counter:
        cpe_types = [
            cpe_type
            for cpe_type, count in positive_type_counter.most_common()
            if count >= threshold
        ]
        if not cpe_types:
            cpe_types = [positive_type_counter.most_common(1)[0][0]]
    elif majority_state == "early_stress" and early_stress_type_counter:
        cpe_types = [
            cpe_type
            for cpe_type, count in early_stress_type_counter.most_common()
            if count >= threshold
        ]
        if not cpe_types:
            cpe_types = [early_stress_type_counter.most_common(1)[0][0]]
    else:
        cpe_types = []

    summary = next((s for s in summaries if s), "")

    return {
        "tile_state": majority_state,
        "tile_positive": majority_state == "clear_cpe",
        "tile_early_stress": majority_state == "early_stress",
        "positive_votes": positive_votes,
        "early_stress_votes": early_stress_votes,
        "healthy_votes": healthy_votes,
        "consensus_strength": round(consensus_strength, 4),
        "model_confidence_mean": round(model_confidence_mean, 4),
        "viability_mean": round(viability_mean, 2) if viability_mean is not None else None,
        "cpe_types": cpe_types,
        "summary": summary,
    }


def aggregate_image_result(tile_results: list[dict]) -> dict:
    if not tile_results:
        return {
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
            "full_response_text": "No usable tiles were analyzed.",
            "tile_results": []
        }

    total_tiles = len(tile_results)
    positive_tiles = sum(1 for t in tile_results if t["tile_positive"])
    early_stress_tiles = sum(1 for t in tile_results if t["tile_early_stress"])

    positive_fraction = positive_tiles / total_tiles
    early_stress_fraction = early_stress_tiles / total_tiles

    valid_tile_viabilities = [t["viability_mean"] for t in tile_results if t["viability_mean"] is not None]
    avg_viability = float(np.mean(valid_tile_viabilities)) if valid_tile_viabilities else None

    avg_model_confidence = float(np.mean([t["model_confidence_mean"] for t in tile_results]))
    avg_consensus_strength = float(np.mean([t["consensus_strength"] for t in tile_results]))

    image_positive = positive_fraction >= POSITIVE_TILE_THRESHOLD
    image_early_stress = (not image_positive) and (early_stress_fraction >= EARLY_STRESS_TILE_THRESHOLD)

    positive_type_counter = Counter()
    early_stress_type_counter = Counter()
    positive_tile_details = []
    early_stress_tile_details = []

    for tile in tile_results:
        if tile["tile_positive"]:
            positive_type_counter.update(tile["cpe_types"])
            positive_tile_details.append(tile)
        elif tile["tile_early_stress"]:
            early_stress_type_counter.update(tile["cpe_types"])
            early_stress_tile_details.append(tile)

    if image_positive:
        culture_state = "clear_cpe"
        cpe_detected = True
        cpe_types = [name for name, _ in positive_type_counter.most_common()] if positive_type_counter else None
    elif image_early_stress:
        culture_state = "early_stress"
        cpe_detected = False
        cpe_types = [name for name, _ in early_stress_type_counter.most_common()] if early_stress_type_counter else None
    else:
        culture_state = "healthy"
        cpe_detected = False
        cpe_types = None

    positive_consensus = (
        float(np.mean([t["consensus_strength"] for t in positive_tile_details]))
        if positive_tile_details else 0.0
    )
    positive_model_conf = (
        float(np.mean([t["model_confidence_mean"] for t in positive_tile_details]))
        if positive_tile_details else avg_model_confidence
    )

    early_consensus = (
        float(np.mean([t["consensus_strength"] for t in early_stress_tile_details]))
        if early_stress_tile_details else 0.0
    )
    early_model_conf = (
        float(np.mean([t["model_confidence_mean"] for t in early_stress_tile_details]))
        if early_stress_tile_details else avg_model_confidence
    )

    if image_positive:
        extent_score = min(positive_fraction / 0.25, 1.0)
        confidence = (
            0.45 * extent_score +
            0.30 * positive_consensus +
            0.25 * positive_model_conf
        )
    elif image_early_stress:
        extent_score = min(early_stress_fraction / 0.35, 1.0)
        confidence = (
            0.40 * extent_score +
            0.30 * early_consensus +
            0.30 * early_model_conf
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
            f"Clear CPE detected in {positive_tiles}/{total_tiles} tiles "
            f"({positive_fraction:.1%}). Most supported positive tiles: {', '.join(strongest_tile_ids)}."
        )
    elif image_early_stress:
        strongest_tiles = sorted(
            early_stress_tile_details,
            key=lambda t: (t["consensus_strength"], t["model_confidence_mean"]),
            reverse=True,
        )[:3]
        strongest_tile_ids = [t["tile_id"] for t in strongest_tiles]
        summary = (
            f"Early stress pattern detected in {early_stress_tiles}/{total_tiles} tiles "
            f"({early_stress_fraction:.1%}) without enough evidence for clear CPE. "
            f"Most supported stress tiles: {', '.join(strongest_tile_ids)}."
        )
    else:
        summary = (
            f"No convincing CPE detected across {total_tiles} analyzed tiles. "
            f"Positive tile fraction was {positive_fraction:.1%} and early-stress tile fraction was {early_stress_fraction:.1%}."
        )

    return {
        "culture_state": culture_state,
        "cpe_detected": cpe_detected,
        "cpe_types": cpe_types,
        "viability": round(avg_viability, 2) if avg_viability is not None else None,
        "confidence": confidence,
        "positive_tiles": positive_tiles,
        "early_stress_tiles": early_stress_tiles,
        "total_tiles": total_tiles,
        "positive_tile_fraction": round(positive_fraction, 4),
        "early_stress_tile_fraction": round(early_stress_fraction, 4),
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
            "State": result.get("culture_state"),
            "CPE Detected": result.get("cpe_detected"),
            "Confidence": result.get("confidence"),
            "Positive Tiles": result.get("positive_tiles"),
            "Stress Tiles": result.get("early_stress_tiles"),
            "Total Tiles": result.get("total_tiles"),
            "Viability": result.get("viability"),
            "CPE Types": ", ".join(result.get("cpe_types") or []) if result.get("cpe_types") else None,
        })

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


def process_single_tile(tile: dict) -> dict | None:
    tile_id = tile["tile_id"]
    tile_image = tile["image"]

    if not tile_has_enough_detail(tile_image):
        return {
            "tile_id": tile_id,
            "row": tile["row"],
            "col": tile["col"],
            "skipped": True,
            "reason": "low_detail",
        }

    tile_result = analyze_tile(tile_image)
    tile_result["tile_id"] = tile_id
    tile_result["row"] = tile["row"]
    tile_result["col"] = tile["col"]
    tile_result["skipped"] = False
    return tile_result


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
