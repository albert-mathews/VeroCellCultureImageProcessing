import pandas as pd
import numpy as np
import os

# ====================== SETTINGS ======================
AIRVIC_CSV = "../airvic-results/airvic-results.csv"
METRICS_CSV = "cpe_metrics.csv"
OUTPUT_CSV = "cellpose-results.csv"
# ====================================================

# Step 1: Load airvic-results.csv
airvic = pd.read_csv(AIRVIC_CSV)

# Step 2: Generate exact filenames and keep original path/id/CRO_CPE
airvic['image'] = airvic.apply(
    lambda r: f"EXP_path{int(r['path'])}_passage4_{int(r['id'])}.png", axis=1
)

# Step 3: Load cpe_metrics.csv and filter to the 22 images
metrics = pd.read_csv(METRICS_CSV)
filtered = metrics[metrics['image'].isin(airvic['image'])].copy()

if len(filtered) == 0:
    print("No matching images found in cpe_metrics.csv.")
    exit()

print(f"Found {len(filtered)} matching images.")

# Step 4: Compute CPE probability using ONLY circularity + eccentricity
def cpe_probability(row):
    circ = row['mean_circularity']
    ecc = row['mean_eccentricity']
    
    circ_score = max(0, min(1, (circ - 0.40) / 0.60))
    ecc_score = ecc
    
    score = 0.57 * circ_score + 0.43 * ecc_score
    prob = 1 / (1 + np.exp(-8 * (score - 0.55)))
    return round(prob, 4)

filtered['CellPose CPE Probability'] = filtered.apply(cpe_probability, axis=1)

# Step 4b: Add binary CPE Detection column (1 if probability > 0.5, else 0)
filtered['CPE Detection'] = (filtered['CellPose CPE Probability'] > 0.5).astype(int)

# Step 5: Merge with airvic to get path, id, CRO_CPE
final = airvic[['path', 'id', 'CRO_CPE', 'image']].merge(
    filtered[['image', 'CellPose CPE Probability', 'CPE Detection']],
    on='image',
    how='left'
)

# Step 6: Minimal output with exactly the five requested columns
final = final[['path', 'id', 'CRO_CPE', 'CellPose CPE Probability', 'CPE Detection']].copy()
final.to_csv(OUTPUT_CSV, index=False)

print(f"\nDone! Minimal report saved to {OUTPUT_CSV}")
print(final.head())