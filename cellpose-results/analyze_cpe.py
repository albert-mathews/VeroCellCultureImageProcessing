import os
import numpy as np
import pandas as pd
from cellpose import models, io
from skimage import measure, io as skio
from skimage.measure import regionprops_table
import warnings
warnings.filterwarnings("ignore")

# ====================== SETTINGS ======================
IMAGE_DIR = ".../converted_pngs"          # folder with your 101 PNGs
OUTPUT_DIR = "results"             # will be created if missing
MODEL_TYPE = "cyto"                # or "cyto3" for better brightfield/phase
DIAMETER = 30                      # approximate Vero cell diameter in pixels at your magnification; adjust once on a test image if needed (None = auto)
GPU = True                         # set False if no GPU
SAVE_MASKS = True                  # set False to skip saving mask images
# ====================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load model once (efficient for batch)
model = models.Cellpose(gpu=GPU, model_type=MODEL_TYPE)

# Get list of PNG files
image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith('.png')]
image_files.sort()  # optional: process in filename order

print(f"Found {len(image_files)} images. Starting batch analysis...")

results = []

for idx, filename in enumerate(image_files):
    print(f"Processing {idx+1}/{len(image_files)}: {filename}")
    img_path = os.path.join(IMAGE_DIR, filename)
    
    # Load as grayscale (shape: H x W)
    img = skio.imread(img_path, as_gray=True)
    if img.ndim == 3:  # if accidentally RGB
        img = np.mean(img, axis=2)
    img = img.astype(np.float32)
    
    # Convert to 3-channel for Cellpose (required for grayscale input)
    img_3ch = np.stack([img, img, img], axis=0)  # shape (3, H, W)
    
    # Segment
    masks, flows, styles, diams = model.eval(
        img_3ch,
        diameter=DIAMETER,
        channels=[0, 0],      # grayscale mode
        normalize=True,
        resample=True,
        batch_size=8,         # adjust if GPU memory issues
        min_size=15
    )
    
    # Save mask (optional)
    if SAVE_MASKS:
        mask_path = os.path.join(OUTPUT_DIR, filename.replace('.png', '_mask.png'))
        skio.imsave(mask_path, masks.astype(np.uint16))
    
    # Compute CPE proxy metrics using regionprops
    if np.max(masks) == 0:  # no cells detected
        metrics = {
            'image': filename,
            'cell_count': 0,
            'confluency_percent': 0.0,
            'mean_area_px': 0.0,
            'mean_circularity': 0.0,
            'mean_eccentricity': 0.0,
            'mean_perimeter_px': 0.0
        }
    else:
        props = regionprops_table(masks, properties=('area', 'perimeter', 'eccentricity', 'circularities'))
        areas = props['area']
        perimeters = props['perimeter']
        eccentricities = props['eccentricity']
        circularities = 4 * np.pi * areas / (perimeters ** 2)  # standard formula
        
        total_area = np.sum(areas)
        image_area = img.shape[0] * img.shape[1]
        
        metrics = {
            'image': filename,
            'cell_count': len(areas),
            'confluency_percent': (total_area / image_area) * 100,
            'mean_area_px': np.mean(areas),
            'mean_circularity': np.mean(circularities),
            'mean_eccentricity': np.mean(eccentricities),
            'mean_perimeter_px': np.mean(perimeters)
        }
    
    results.append(metrics)

# Save master CSV
df = pd.DataFrame(results)
csv_path = os.path.join(OUTPUT_DIR, "cpe_metrics.csv")
df.to_csv(csv_path, index=False)

print(f"\nDone! Results saved to {csv_path}")
print(df.head())