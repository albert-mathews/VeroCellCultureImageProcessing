import pandas as pd
import numpy as np
import os

# ====================== SETTINGS ======================
AIRVIC_CSV = "../airvic-results/airvic-results.csv"
METRICS_CSV = "cpe_metrics.csv"
OUTPUT_CSV = "cpe_probability_report.csv"
# ====================================================

# Step 1: Generate exact filenames from airvic-results.csv
airvic = pd.read_csv(AIRVIC_CSV)
filenames = [f"EXP_path{int(row['path'])}_passage4_{int(row['id'])}.png" 
             for _, row in airvic.iterrows()]

print(f"Generated {len(filenames)} target filenames")

# Step 2: Load metrics and filter to the 22 images of interest
metrics = pd.read_csv(METRICS_CSV)
filtered = metrics[metrics['image'].isin(filenames)].copy()

if len(filtered) == 0:
    print("No matching images found.")
    exit()

print(f"Found {len(filtered)} matching images.")

# Step 3: Compute CPE probability using ONLY circularity + eccentricity
def cpe_probability(row):
    circ = row['mean_circularity']
    ecc = row['mean_eccentricity']
    
    # Normalised scores (1.0 = strongest CPE-like rounding)
    circ_score = max(0, min(1, (circ - 0.40) / 0.60))
    ecc_score = ecc
    
    # Weighted score (only morphology metrics)
    score = 0.57 * circ_score + 0.43 * ecc_score
    
    # Sigmoid → smooth probability 0–1
    prob = 1 / (1 + np.exp(-8 * (score - 0.55)))
    return round(prob, 4)

filtered['cpe_probability'] = filtered.apply(cpe_probability, axis=1)

# Step 4: Minimal output — ONLY image and probability
minimal_df = filtered[['image', 'cpe_probability']].copy()
minimal_df.to_csv(OUTPUT_CSV, index=False)

print(f"\nDone! Minimal report saved to {OUTPUT_CSV}")
print(minimal_df.head())