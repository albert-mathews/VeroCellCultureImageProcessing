"""
CPE Detection Script — Claude Opus 4.6
Tiled analysis of Vero E6 cell culture microscopy images.

Pipeline:
  1. Compress images to fit the 5 MB API limit
  2. Split each image into a configurable tile grid (default 3x3)
  3. Analyse each tile with Claude Opus 4.6 using native structured outputs
  4. Aggregate tile results into a per-image verdict
  5. Save results incrementally to JSON + print a summary table

Install dependencies:
    pip install anthropic pydantic pillow numpy pandas python-dotenv

Usage:
    Set ANTHROPIC_API_KEY in a .env file, then:
        python individual_image_claude.py
"""

import os
import io
import re
import json
import time
import base64
import math
from collections import Counter
from typing import Optional

import numpy as np
import pandas as pd
from PIL import Image
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

IMAGE_FOLDER       = "converted_pngs"
RESULTS_FILENAME   = "cpe_detection_results_claude.json"
MODEL              = "claude-opus-4-6"

# Tile grid — 3x3 gives 9 tiles with enough cell context per tile.
# A 4x4 grid on a ~1270x952 px image yields ~317x238 px tiles, which is
# very small for 10x microscopy. Use 2 or 3 for better morphology visibility.
TILE_GRID = 3

# Image is called CPE-positive if this fraction of tiles are positive.
POSITIVE_TILE_THRESHOLD = 0.10   # 10 %  — same as original

# Skip near-blank tiles (background, out-of-field areas).
SKIP_LOW_DETAIL_TILES     = True
LOW_DETAIL_STD_THRESHOLD  = 4.0   # pixel std-dev below this → skip

MAX_RETRIES    = 3
MAX_IMAGE_BYTES = 4_500_000       # stay well under the 5 MB API limit
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

# ---------------------------------------------------------------------------
# Pydantic schema — native structured outputs, zero JSON parsing code needed
# ---------------------------------------------------------------------------

CPE_TYPE_CHOICES = [
    "dying cells", "rounding", "vacuolation", "detachment",
    "granularity", "refractile cells", "syncytium formation",
    "intranuclear inclusion bodies", "pyknosis", "karyorrhexis",
]

class TileAnalysis(BaseModel):
    """Structured response for a single image tile."""
    cpe_detected: bool = Field(
        description="True if any CPE morphology is visible in this tile."
    )
    cpe_types: Optional[list[str]] = Field(
        default=None,
        description=(
            "List of detected CPE morphologies from: "
            + ", ".join(CPE_TYPE_CHOICES)
            + ". Null if none detected."
        )
    )
    viability: float = Field(
        ge=0, le=100,
        description="Estimated percentage of live cells (0=all dead, 100=all alive)."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Your confidence in this assessment (0=uncertain, 1=very confident)."
    )
    full_response_text: str = Field(
        description="Concise summary of morphological findings in this tile."
    )

# ---------------------------------------------------------------------------
# System prompt — cached on every call, sent once per session
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a virology specialist with expertise in light microscopy of Vero E6 cell cultures.

You will receive an image that is either a full microscope field or a tile cropped from one.
Images are of Vero E6 cells in standard growth medium, captured by bright-field or phase-contrast microscopy at 10x or 20x magnification.

PRIMARY TASK — Detect Cytopathic Effect (CPE).
Before deciding, perform this structured visual inspection:

Step 1 — Cell density
Estimate whether the monolayer is sparse, moderate, or dense.

Step 2 — Cell morphology
Look specifically for:
  • Rounding (cells losing their flat, elongated shape)
  • Detachment (rounded or floating cells, empty patches)
  • Vacuolation (clear cytoplasmic vacuoles)
  • Refractile cells (highly phase-bright, indicating dying/stressed cells)
  • Granularity (coarse cytoplasmic texture)
  • Syncytium formation (multinucleated giant cells)
  • Intranuclear inclusion bodies, pyknosis, karyorrhexis

Step 3 — Spatial clustering
Are abnormal cells isolated, clustered, or widespread?

Step 4 — Decision
Only after completing the steps above, decide if CPE is present.
Be conservative — do not overcall weak or ambiguous findings. Reflect uncertainty in the confidence score.

SECONDARY TASK — Estimate viability.
No trypan blue stain is available. Use morphological cues:
  • Healthy live cells: flat, adherent, elongated, clear cytoplasm, visible nucleus
  • Dying/dead cells: rounded, refractile, detached, dark granular cytoplasm, condensed nucleus

Return a single JSON object matching the provided schema. Do not add any text outside the JSON."""

# ---------------------------------------------------------------------------
# CPE type normalisation
# ---------------------------------------------------------------------------

_CANONICAL = {
    "dying cells": "dying cells",
    "rounding": "rounding",
    "vacuolation": "vacuolation",
    "vacuolisation": "vacuolation",
    "detached": "detachment",
    "detachment": "detachment",
    "detached cells": "detachment",
    "lysis": "detachment",
    "granularity": "granularity",
    "refractile": "refractile cells",
    "refractile cells": "refractile cells",
    "syncytium": "syncytium formation",
    "syncytium formation": "syncytium formation",
    "intranuclear inclusion bodies": "intranuclear inclusion bodies",
    "intranuclear inclusions": "intranuclear inclusion bodies",
    "pyknosis": "pyknosis",
    "karyorrhexis": "karyorrhexis",
}

def normalise_cpe_types(raw: Optional[list]) -> list[str]:
    if not raw:
        return []
    seen, out = set(), []
    for item in raw:
        if item is None:
            continue
        key = str(item).strip().lower()
        canonical = _CANONICAL.get(key, key)
        if canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return out

# ---------------------------------------------------------------------------
# Image utilities
# ---------------------------------------------------------------------------

def compress_image(path: str, max_bytes: int = MAX_IMAGE_BYTES) -> tuple[str, str]:
    """
    Resize and/or compress an image to fit under the API's 5 MB limit.
    Returns (base64_string, media_type).

    Strategy:
      1. Resize so the longest edge ≤ 1568 px (Claude's internal cap — sending
         larger images wastes bandwidth with no quality gain).
      2. Try lossless PNG — use it if it fits.
      3. Fall back to JPEG at decreasing quality until it fits.
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size
    max_dim = 1568
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    if buf.tell() <= max_bytes:
        return base64.b64encode(buf.getvalue()).decode(), "image/png"

    for quality in (95, 85, 75, 60):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= max_bytes:
            print(f"    Compressed → JPEG q={quality} ({buf.tell()/1e6:.1f} MB)")
            return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"

    raise ValueError(f"Cannot compress '{path}' below {max_bytes/1e6:.1f} MB")


def pil_to_b64(img: Image.Image) -> tuple[str, str]:
    """Convert an in-memory PIL image to (base64, media_type), compressing if needed."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    if buf.tell() <= MAX_IMAGE_BYTES:
        return base64.b64encode(buf.getvalue()).decode(), "image/png"
    for quality in (95, 85, 75, 60):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= MAX_IMAGE_BYTES:
            return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"
    raise ValueError("Tile cannot be compressed below 4.5 MB")


def tile_has_detail(tile: Image.Image) -> bool:
    if not SKIP_LOW_DETAIL_TILES:
        return True
    arr = np.asarray(tile).astype(np.float32)
    return float(arr.std()) >= LOW_DETAIL_STD_THRESHOLD


def split_into_tiles(path: str, grid: int = TILE_GRID) -> list[dict]:
    img = Image.open(path).convert("RGB")
    W, H = img.size
    tw, th = W // grid, H // grid
    tiles = []
    for row in range(grid):
        for col in range(grid):
            l = col * tw
            t = row * th
            r = W if col == grid - 1 else (col + 1) * tw
            b = H if row == grid - 1 else (row + 1) * th
            tiles.append({
                "tile_id": f"r{row+1}c{col+1}",
                "row": row + 1,
                "col": col + 1,
                "image": img.crop((l, t, r, b)),
            })
    return tiles

# ---------------------------------------------------------------------------
# API call — uses native structured outputs via client.messages.parse()
# ---------------------------------------------------------------------------

def call_claude(image_b64: str, media_type: str) -> TileAnalysis:
    """
    Analyse one tile. Uses:
      • client.messages.parse()  — native structured outputs (Pydantic), no regex
      • system prompt caching    — the long prompt is cached after the first call
      • temperature=0            — deterministic; consensus runs not needed
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.messages.parse(
                model=MODEL,
                max_tokens=1024,
                temperature=0,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},  # cache the long prompt
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    "Analyse this microscopy tile and return the JSON object "
                                    "as specified in the schema."
                                ),
                            },
                        ],
                    }
                ],
                output_format=TileAnalysis,   # native structured output — guaranteed schema
            )
            result: TileAnalysis = response.parsed_output
            result.cpe_types = normalise_cpe_types(result.cpe_types)
            return result

        except anthropic.RateLimitError:
            wait = 60 * attempt
            print(f"    Rate limit. Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})…")
            time.sleep(wait)

        except anthropic.APIStatusError as e:
            if e.status_code in (500, 529) and attempt < MAX_RETRIES:
                wait = 30 * attempt
                print(f"    API {e.status_code}. Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})…")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"API call failed after {MAX_RETRIES} attempts.")

# ---------------------------------------------------------------------------
# Per-tile analysis
# ---------------------------------------------------------------------------

def analyse_tile(tile_meta: dict) -> dict:
    tile_image = tile_meta["image"]
    tile_id    = tile_meta["tile_id"]

    if not tile_has_detail(tile_image):
        return None  # caller will skip

    b64, media_type = pil_to_b64(tile_image)
    result = call_claude(b64, media_type)

    return {
        "tile_id":           tile_id,
        "row":               tile_meta["row"],
        "col":               tile_meta["col"],
        "tile_positive":     result.cpe_detected,
        "cpe_types":         result.cpe_types or [],
        "viability_mean":    result.viability,
        "model_confidence":  result.confidence,
        "summary":           result.full_response_text,
    }

# ---------------------------------------------------------------------------
# Image-level aggregation  (mirrors original logic)
# ---------------------------------------------------------------------------

def aggregate_image_result(tile_results: list[dict]) -> dict:
    if not tile_results:
        return {
            "cpe_detected": False, "cpe_types": None, "viability": 0,
            "confidence": 0, "positive_tiles": 0, "total_tiles": 0,
            "positive_tile_fraction": 0,
            "full_response_text": "No usable tiles were analysed.",
            "tile_results": [],
        }

    total     = len(tile_results)
    positives = [t for t in tile_results if t["tile_positive"]]
    pos_count = len(positives)
    pos_frac  = pos_count / total

    avg_viability   = float(np.mean([t["viability_mean"]   for t in tile_results]))
    avg_confidence  = float(np.mean([t["model_confidence"] for t in tile_results]))

    image_positive = pos_frac >= POSITIVE_TILE_THRESHOLD

    # Aggregate CPE types from positive tiles
    type_counter = Counter()
    for t in positives:
        type_counter.update(t["cpe_types"])
    cpe_types = [name for name, _ in type_counter.most_common()] if image_positive else None

    # Derive the most-affected quadrant from tile positions
    cpe_quadrant = None
    if positives:
        # Map tile row/col to image quadrant
        mid_row = math.ceil(TILE_GRID / 2)
        mid_col = math.ceil(TILE_GRID / 2)
        quad_counts = Counter()
        for t in positives:
            q_row = 1 if t["row"] <= mid_row else 2
            q_col = 1 if t["col"] <= mid_col else 2
            quad = q_row * 2 + q_col - 2   # 1=TL, 2=TR, 3=BL, 4=BR
            quad_counts[quad] += 1
        cpe_quadrant = quad_counts.most_common(1)[0][0] if quad_counts else None

    # Composite confidence score
    pos_conf = float(np.mean([t["model_confidence"] for t in positives])) if positives else avg_confidence
    if image_positive:
        extent = min(pos_frac / 0.25, 1.0)
        confidence = round(0.45 * extent + 0.55 * pos_conf, 4)
    else:
        confidence = round(0.45 * (1.0 - pos_frac) + 0.55 * avg_confidence, 4)
    confidence = float(max(0.0, min(1.0, confidence)))

    if image_positive:
        top_tiles = sorted(positives, key=lambda t: t["model_confidence"], reverse=True)[:3]
        summary = (
            f"CPE detected in {pos_count}/{total} tiles ({pos_frac:.0%}). "
            f"Strongest signal in: {', '.join(t['tile_id'] for t in top_tiles)}."
        )
    else:
        summary = (
            f"No convincing CPE across {total} tiles. "
            f"Positive fraction: {pos_frac:.0%}."
        )

    return {
        "cpe_detected":           image_positive,
        "cpe_types":              cpe_types,
        "cpe_quadrant":           cpe_quadrant,
        "viability":              round(avg_viability, 2),
        "confidence":             confidence,
        "positive_tiles":         pos_count,
        "total_tiles":            total,
        "positive_tile_fraction": round(pos_frac, 4),
        "full_response_text":     summary,
        "tile_results":           tile_results,
    }

# ---------------------------------------------------------------------------
# Results I/O
# ---------------------------------------------------------------------------

def load_existing_results() -> dict:
    if not os.path.exists(RESULTS_FILENAME):
        return {}
    choice = input(f"'{RESULTS_FILENAME}' found. Load it? (yes/no): ").strip().lower()
    if choice == "yes":
        with open(RESULTS_FILENAME, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded {len(data)} previous results.")
        return data
    print("Starting fresh.")
    return {}


def save_results(results: dict):
    with open(RESULTS_FILENAME, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)


def print_summary_table(results: dict):
    if not results:
        print("No results.")
        return
    rows = []
    for name, r in results.items():
        rows.append({
            "Image":          name,
            "CPE":            r.get("cpe_detected"),
            "Quadrant":       r.get("cpe_quadrant"),
            "Confidence":     r.get("confidence"),
            "+Tiles":         f"{r.get('positive_tiles')}/{r.get('total_tiles')}",
            "Viability %":    r.get("viability"),
            "CPE Types":      ", ".join(r.get("cpe_types") or []) or "—",
        })
    print(pd.DataFrame(rows).to_string(index=False))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    all_results = load_existing_results()

    image_files = sorted(
        f for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith(IMAGE_EXTENSIONS)
    )
    if not image_files:
        print(f"No images found in '{IMAGE_FOLDER}'. Exiting.")
        return

    print(f"\nStarting image processing… 🔬  ({len(image_files)} images, {TILE_GRID}×{TILE_GRID} grid)\n")

    for idx, filename in enumerate(image_files, 1):
        print(f"[{idx}/{len(image_files)}] {filename}")

        if filename in all_results:
            print("  Already processed — skipping.\n")
            continue

        full_path = os.path.join(IMAGE_FOLDER, filename)

        try:
            tiles = split_into_tiles(full_path, grid=TILE_GRID)
            tile_results = []

            for tile_meta in tiles:
                tile_id = tile_meta["tile_id"]

                if not tile_has_detail(tile_meta["image"]):
                    print(f"  {tile_id}: skipped (low detail)")
                    continue

                b64, media_type = pil_to_b64(tile_meta["image"])
                result_raw = call_claude(b64, media_type)

                tile_result = {
                    "tile_id":          tile_id,
                    "row":              tile_meta["row"],
                    "col":              tile_meta["col"],
                    "tile_positive":    result_raw.cpe_detected,
                    "cpe_types":        result_raw.cpe_types or [],
                    "viability_mean":   result_raw.viability,
                    "model_confidence": result_raw.confidence,
                    "summary":          result_raw.full_response_text,
                }
                tile_results.append(tile_result)

                print(
                    f"  {tile_id}: CPE={tile_result['tile_positive']} | "
                    f"conf={tile_result['model_confidence']:.2f} | "
                    f"viability={tile_result['viability_mean']:.0f}% | "
                    f"types={tile_result['cpe_types'] or '—'}"
                )

                # Small polite pause between tile calls
                time.sleep(1)

            image_result = aggregate_image_result(tile_results)
            all_results[filename] = image_result
            save_results(all_results)

            print(
                f"  ✓ Image result: CPE={image_result['cpe_detected']} | "
                f"quadrant={image_result['cpe_quadrant']} | "
                f"conf={image_result['confidence']:.2f} | "
                f"+tiles={image_result['positive_tiles']}/{image_result['total_tiles']} | "
                f"viability={image_result['viability']:.0f}%\n"
            )

        except Exception as exc:
            print(f"  ERROR: {exc}\n")
            all_results[filename] = {
                "cpe_detected": False, "cpe_types": None, "cpe_quadrant": None,
                "viability": 0, "confidence": 0,
                "positive_tiles": 0, "total_tiles": 0, "positive_tile_fraction": 0,
                "full_response_text": f"Error: {exc}",
                "tile_results": [],
            }
            save_results(all_results)

    print("\nProcessing complete! 🎉\n")
    print("--- Summary ---")
    print_summary_table(all_results)
    print(f"\nResults saved to '{RESULTS_FILENAME}'")


if __name__ == "__main__":
    main()
