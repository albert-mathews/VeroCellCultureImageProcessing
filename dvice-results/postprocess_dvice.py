#!/usr/bin/env python3
"""
postprocess_dvice.py

Combines DVICE model results with CRO ground truth for publication-ready table.
- Loads CRO annotations from ..\cro-results\cro_cpe_detections.csv
- Creates CRO_CPE = 1 if ANY CRO_* column is 1
- Keeps ONLY images that exist in the CRO file
- Adds DVICE probabilities, average, and final binary decision
"""

import pandas as pd
from pathlib import Path
DVICE_CPE_THRESHOLD = 0.5

def main():
    # ====================== PATHS ======================
    dvice_csv = Path('dvice-results.csv')
    cro_csv = Path('..') / 'cro-results' / 'cro_cpe_detections.csv'
    
    if not dvice_csv.exists():
        raise FileNotFoundError(f"❌ dvice-results.csv not found in current folder")
    if not cro_csv.exists():
        raise FileNotFoundError(f"❌ cro_cpe_detections.csv not found at {cro_csv}")

    # ====================== LOAD DATA ======================
    print("Loading DVICE results...")
    dvice_df = pd.read_csv(dvice_csv)
    
    print(f"Loading CRO ground truth from {cro_csv}...")
    cro_df = pd.read_csv(cro_csv)

    # ====================== CREATE CRO_CPE ======================
    # Identify all CRO_* columns
    cro_columns = [col for col in cro_df.columns if col.startswith('CRO_')]
    print(f"Found CRO columns: {cro_columns}")
    
    # CRO_CPE = 1 if ANY CRO annotation is positive
    cro_df['CRO_CPE'] = (cro_df[cro_columns] == 1).any(axis=1).astype(int)

    # Keep only needed columns from CRO
    cro_clean = cro_df[['path', 'id', 'CRO_CPE']].copy()

    # ====================== MERGE & FILTER ======================
    # Only keep images that have CRO annotations (inner join)
    merged = pd.merge(cro_clean, dvice_df, on=['path', 'id'], how='inner')
    print(f"✅ Merged: {len(merged)} images (only those with CRO ground truth)")

    # ====================== BUILD FINAL PUBLICATION TABLE ======================
    final_df = pd.DataFrame({
        'path': merged['path'],
        'id': merged['id'],
        'CRO_CPE': merged['CRO_CPE'],
        'model1_prob': merged['model1_infected'].round(4),
        'model2_prob': merged['model2_infected'].round(4),
        'model3_prob': merged['model3_infected'].round(4),
    })

    # Average DVICE probability (very useful for publication)
    final_df['avg_dvice_prob'] = final_df[['model1_prob', 'model2_prob', 'model3_prob']].mean(axis=1).round(4)

    # Final DVICE binary decision (same threshold logic as CellPose)
    final_df['DVICE_CPE'] = (final_df['avg_dvice_prob'] >= DVICE_CPE_THRESHOLD).astype(int)

    # Final column order (matches your CellPose table style)
    final_df = final_df[['path', 'id', 'CRO_CPE',
                         'model1_prob', 'model2_prob', 'model3_prob',
                         'avg_dvice_prob', 'DVICE_CPE']]

    # ====================== SAVE ======================
    output_path = Path('dvice-final-results.csv')
    final_df.to_csv(output_path, index=False)

    print(f"\n🎉 Post-processing complete!")
    print(f"   Output saved to: {output_path}")
    print(f"   Total rows in final table: {len(final_df)}")
    print("\nPreview of first 8 rows:")
    print(final_df.head(8).to_string(index=False))

if __name__ == "__main__":
    main()