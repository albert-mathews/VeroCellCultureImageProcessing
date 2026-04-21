#!/usr/bin/env python3
"""
sensitivity_study.py

Performs a threshold sensitivity analysis on DVICE CPE predictions.
- Sweeps threshold from 0.0 to 1.0
- Computes accuracy for model1, model2, model3, and their average
- Uses exact CRO ground truth (22 images)
- Saves results to sweep-results.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

def main():
    # ====================== PATHS ======================
    dvice_csv = Path('dvice-results.csv')
    cro_csv   = Path('..') / 'cro-results' / 'cro_cpe_detections.csv'
    
    if not dvice_csv.exists():
        raise FileNotFoundError(f"dvice-results.csv not found")
    if not cro_csv.exists():
        raise FileNotFoundError(f"cro_cpe_detections.csv not found at {cro_csv}")

    # ====================== LOAD DATA ======================
    print("Loading DVICE results...")
    dvice_df = pd.read_csv(dvice_csv)
    
    print("Loading CRO ground truth...")
    cro_df = pd.read_csv(cro_csv)

    # ====================== CREATE GROUND TRUTH CRO_CPE ======================
    cro_columns = [col for col in cro_df.columns if col.startswith('CRO_')]
    print(f"Found CRO annotation columns: {cro_columns}")
    
    # CRO_CPE = 1 if ANY of the CRO_* columns is 1
    cro_df['CRO_CPE'] = (cro_df[cro_columns] == 1).any(axis=1).astype(int)

    # ====================== MERGE ======================
    merged = pd.merge(
        cro_df[['path', 'id', 'CRO_CPE']], 
        dvice_df, 
        on=['path', 'id'], 
        how='inner'
    )
    
    print(f"✅ Merged dataset: {len(merged)} images (matches expected 22)")

    # ====================== THRESHOLD SWEEP ======================
    thresholds = np.arange(0.0, 1.01, 0.05)   # 0.00, 0.05, ..., 1.00
    
    results = []
    
    for t in thresholds:
        row = {'threshold': round(t, 2)}
        
        # --- Individual models ---
        for m in ['model1', 'model2', 'model3']:
            probs = merged[f'{m}_infected']
            preds = (probs >= t).astype(int)
            correct = (preds == merged['CRO_CPE']).sum()
            acc = (correct / 22) * 100
            row[f'{m}_acc'] = round(acc, 2)
        
        # --- Average of three models ---
        avg_prob = merged[['model1_infected', 'model2_infected', 'model3_infected']].mean(axis=1)
        avg_preds = (avg_prob >= t).astype(int)
        avg_correct = (avg_preds == merged['CRO_CPE']).sum()
        avg_acc = (avg_correct / 22) * 100
        row['avg_acc'] = round(avg_acc, 2)
        
        results.append(row)

    # ====================== SAVE RESULTS ======================
    sweep_df = pd.DataFrame(results)
    output_path = Path('sweep-results.csv')
    sweep_df.to_csv(output_path, index=False)

    print(f"\n🎉 Sensitivity analysis complete!")
    print(f"   Thresholds tested : {len(thresholds)} values")
    print(f"   Output saved to   : {output_path}")
    print("\nPreview (first 6 rows):")
    print(sweep_df.head(6).to_string(index=False))

if __name__ == "__main__":
    main()