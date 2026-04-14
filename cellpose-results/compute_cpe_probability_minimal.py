import pandas as pd
import numpy as np
import os

# ====================== SETTINGS ======================
AIRVIC_CSV = "../airvic-results/airvic-results.csv"
METRICS_CSV = "cpe_metrics.csv"
OUTPUT_CSV = "cpe_probability_report.csv"
# ====================================================

# Step 1: Load airvic-results.csv and generate exact filenames
airvic = pd.read_csv(AIRVIC_CSV)
filenames = [f"EXP_path{int(row['path'])}_passage4_{int(row['id'])}.png" 
             for _, row in airvic.iterrows()]

print(f"Generated {len(filenames)} target filenames from airvic-results.csv")

# Step 2: Load cpe_metrics.csv and filter to the images of interest
metrics = pd.read_csv(METRICS_CSV)
filtered = metrics[metrics['image'].isin(filenames)].copy()

if len(filtered) == 0:
    print("No matching images found in cpe_metrics.csv.")
    exit()

print(f"Found {len(filtered)} matching images.")

# Step 3: Compute CPE detection probability (0–1) for each image
def cpe_probability(row):
    circ = row['mean_circularity']
    ecc = row['mean_eccentricity']
    confl = row['confluency_percent'] / 100.0
    count = row['cell_count']
    
    circ_score = max(0, min(1, (circ - 0.40) / 0.60))
    ecc_score = ecc
    confl_score = max(0, min(1, (0.80 - confl) / 0.60))
    count_score = max(0, min(1, (500 - count) / 400))
    
    score = 0.40 * circ_score + 0.30 * ecc_score + 0.20 * confl_score + 0.10 * count_score
    prob = 1 / (1 + np.exp(-8 * (score - 0.55)))
    return round(prob, 4)

filtered['cpe_probability'] = filtered.apply(cpe_probability, axis=1)

# Step 4: Minimal output — ONLY image and probability
minimal_df = filtered[['image', 'cpe_probability']].copy()
minimal_df.to_csv(OUTPUT_CSV, index=False)

print(f"\nDone! Minimal report saved to {OUTPUT_CSV}")
print(minimal_df.head())