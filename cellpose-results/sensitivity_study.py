#!/usr/bin/env python3
"""
sensitivity_study.py (CellPose adaptation)

Performs threshold sensitivity analysis + AUC-ROC evaluation for CellPose CPE probability.
Outputs:
  - sweep-results.csv   (accuracy vs threshold)
  - aucroc-results.csv  (AUC-ROC score for CellPose)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score

def main():
    # ====================== PATHS ======================
    cellpose_csv = Path('cellpose-results.csv')
    
    if not cellpose_csv.exists():
        raise FileNotFoundError(f"❌ cellpose-results.csv not found")

    # ====================== LOAD DATA ======================
    print("Loading CellPose results...")
    df = pd.read_csv(cellpose_csv)
    
    y_true = df['CRO_CPE']
    probs = df['CellPose CPE Probability']
    
    print(f"✅ Loaded {len(df)} images with CellPose CPE Probability and CRO_CPE")

    # ====================== ACCURACY SWEEP ======================
    thresholds = np.arange(0.0, 1.01, 0.05)
    results = []

    for t in thresholds:
        preds = (probs >= t).astype(int)
        correct = (preds == y_true).sum()
        acc = (correct / len(df)) * 100
        row = {'threshold': round(t, 2), 'cellpose_acc': round(acc, 2)}
        results.append(row)

    sweep_df = pd.DataFrame(results)
    sweep_df.to_csv('sweep-results.csv', index=False)
    print(f"✅ sweep-results.csv saved ({len(thresholds)} thresholds)")

    # ====================== AUC-ROC ======================
    auc = roc_auc_score(y_true, probs)
    auc_df = pd.DataFrame([{'cellpose_auc': round(auc, 4)}])
    auc_df.to_csv('aucroc-results.csv', index=False)

    print(f"✅ aucroc-results.csv saved")
    print("\n=== AUC-ROC Results ===")
    print(f"   cellpose_auc = {auc:.4f}")

    print("\nAll done! Two files generated:")
    print("   • sweep-results.csv")
    print("   • aucroc-results.csv")

if __name__ == "__main__":
    main()