import os
import numpy as np
import pandas as pd
from cellpose import models
from skimage import io as skio
from skimage.measure import regionprops_table
import warnings
warnings.filterwarnings("ignore")

# ====================== SETTINGS ======================
IMAGE_DIR = "../converted_pngs"          # folder with your 101 PNGs
OUTPUT_DIR = "results"             # will be created if missing
MODEL_TYPE = "cyto"               # stable model for Vero brightfield/phase
DIAMETER = 30                      # Vero cell diameter in pixels (None = auto)
GPU = True                         # set False if no GPU
SAVE_MASKS = True                  # set False to skip saving mask images
# ====================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load model (Cellpose 4.x)
model = models.CellposeModel(gpu=GPU, pretrained_model=MODEL_TYPE)

# Get list of PNG files
image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith('.png')]
image_files.sort()

print(f"Found {len(image_files)} images. Starting batch analysis...")

results = []

for idx, filename in enumerate(image_files):
    print(f"Processing {idx+1}/{len(image_files)}: {filename}")
    img_path = os.path.join(IMAGE_DIR, filename)
    
    # Load as 2D grayscale (no 3-channel stacking needed in v4+)
    img = skio.imread(img_path, as_gray=True)
    if img.ndim == 3:
        img = np.mean(img, axis=2)
    img = img.astype(np.float32)
    
    # Segment (channels parameter removed - deprecated in v4+)
    masks, flows, styles, diams = model.eval(
        img,                    # now 2D grayscale
        diameter=DIAMETER,
        normalize=True,
        resample=True,
        batch_size=8,
        min_size=15
    )
    
    # Save mask (optional)
    if SAVE_MASKS:
        mask_path = os.path.join(OUTPUT_DIR, filename.replace('.png', '_mask.png'))
        skio.imsave(mask_path, masks.astype(np.uint16))
    
    # Compute CPE proxy metrics
    if np.max(masks) == 0:
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
        props = regionprops_table(masks, properties=('area', 'perimeter', 'eccentricity'))
        areas = props['area']
        perimeters = props['perimeter']
        eccentricities = props['eccentricity']
        circularities = 4 * np.pi * areas / (perimeters ** 2)
        
        total_area = np.sum(areas)
        image_area = img.shape[0] * img.shape[1]
        
        metrics = {
            'image': filename,
            'cell_count': len(areas),
            'confluency_percent': (total_area / image_area) * 100,
            'mean_area_px': float(np.mean(areas)),
            'mean_circularity': float(np.mean(circularities)),
            'mean_eccentricity': float(np.mean(eccentricities)),
            'mean_perimeter_px': float(np.mean(perimeters))
        }
    
    results.append(metrics)

# Save master CSV
df = pd.DataFrame(results)
csv_path = os.path.join(OUTPUT_DIR, "cpe_metrics.csv")
df.to_csv(csv_path, index=False)

print(f"\nDone! Results saved to {csv_path}")
print(df.head())