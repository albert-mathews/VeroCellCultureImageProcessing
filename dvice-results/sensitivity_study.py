#!/usr/bin/env python3
"""
sensitivity_study.py

Performs threshold sensitivity analysis + AUC-ROC evaluation for DVICE models.
Outputs:
  - sweep-results.csv   (accuracy vs threshold for each model + average)
  - aucroc-results.csv  (AUC-ROC scores for model1, model2, model3, and average)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score

def main():
    # ====================== PATHS ======================
    dvice_csv = Path('dvice-results.csv')
    cro_csv   = Path('..') / 'cro-results' / 'cro_cpe_detections.csv'
    
    if not dvice_csv.exists():
        raise FileNotFoundError(f"❌ dvice-results.csv not found")
    if not cro_csv.exists():
        raise FileNotFoundError(f"❌ cro_cpe_detections.csv not found at {cro_csv}")

    # ====================== LOAD & PREPARE DATA ======================
    print("Loading DVICE results...")
    dvice_df = pd.read_csv(dvice_csv)
    
    print("Loading CRO ground truth...")
    cro_df = pd.read_csv(cro_csv)

    # Create CRO_CPE (1 if any CRO_* column is 1)
    cro_columns = [col for col in cro_df.columns if col.startswith('CRO_')]
    print(f"Found CRO columns: {cro_columns}")
    cro_df['CRO_CPE'] = (cro_df[cro_columns] == 1).any(axis=1).astype(int)

    # Merge (only images with ground truth)
    merged = pd.merge(
        cro_df[['path', 'id', 'CRO_CPE']], 
        dvice_df, 
        on=['path', 'id'], 
        how='inner'
    )
    print(f"✅ Merged dataset: {len(merged)} images (should be 22)")

    y_true = merged['CRO_CPE']

    # ====================== ACCURACY SWEEP ======================
    thresholds = np.arange(0.0, 1.01, 0.05)
    results = []

    for t in thresholds:
        row = {'threshold': round(t, 2)}
        
        # Individual models
        for m in ['model1', 'model2', 'model3']:
            probs = merged[f'{m}_infected']
            preds = (probs >= t).astype(int)
            correct = (preds == y_true).sum()
            acc = (correct / 22) * 100
            row[f'{m}_acc'] = round(acc, 2)
        
        # Average of three models
        avg_prob = merged[['model1_infected', 'model2_infected', 'model3_infected']].mean(axis=1)
        avg_preds = (avg_prob >= t).astype(int)
        avg_correct = (avg_preds == y_true).sum()
        avg_acc = (avg_correct / 22) * 100
        row['avg_acc'] = round(avg_acc, 2)
        
        results.append(row)

    sweep_df = pd.DataFrame(results)
    sweep_df.to_csv('sweep-results.csv', index=False)
    print(f"✅ sweep-results.csv saved ({len(thresholds)} thresholds)")

    # ====================== AUC-ROC ======================
    auc_data = {}
    
    for m in ['model1', 'model2', 'model3']:
        auc_data[f'{m}_auc'] = round(roc_auc_score(y_true, merged[f'{m}_infected']), 4)
    
    # Average probability
    avg_prob = merged[['model1_infected', 'model2_infected', 'model3_infected']].mean(axis=1)
    auc_data['avg_auc'] = round(roc_auc_score(y_true, avg_prob), 4)

    auc_df = pd.DataFrame([auc_data])
    auc_df.to_csv('aucroc-results.csv', index=False)

    print(f"✅ aucroc-results.csv saved")
    print("\n=== AUC-ROC Results ===")
    for k, v in auc_data.items():
        print(f"   {k:12} = {v:.4f}")

    print("\nAll done! Two files generated:")
    print("   • sweep-results.csv")
    print("   • aucroc-results.csv")

if __name__ == "__main__":
    main()