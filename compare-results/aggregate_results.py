import pandas as pd
import numpy as np

# ====================== LOAD DATA ======================
cpe_df = pd.read_csv('cpe_confusion_table.csv')
airvic_df = pd.read_csv('../airvic-results/airvic-results.csv')
cellpose_df = pd.read_csv('../cellpose-results/cellpose-results.csv')

# CPE types for macro-averaging (LLMs only)
cpe_types = ['Dy', 'Ro', 'V', 'D', 'G', 'Re']

model_map = {
    'ChatGPT': 'GPT',
    'Grok': 'GRK',
    'Gemini': 'Gem',
    'Claude': 'CLD'
}

# ====================== HELPER FUNCTIONS ======================
def compute_rates_from_confusion(col, df):
    """LLM per-CPE-type rates (macro-averaged later)"""
    values = df[col].values
    tp = np.sum(values == 1)
    fn = np.sum(values == -1)
    fp = np.sum(values == -2)
    tn = np.sum(values == 0)
    
    total_pos = tp + fn
    total_neg = fp + tn
    total = len(values)
    
    return {
        'FP_rate': fp / total_neg if total_neg > 0 else np.nan,
        'FN_rate': fn / total_pos if total_pos > 0 else np.nan,
        'TP_rate': tp / total_pos if total_pos > 0 else np.nan,
        'TN_rate': tn / total_neg if total_neg > 0 else np.nan,
        'Accuracy': (tp + tn) / total if total > 0 else np.nan
    }


def compute_binary_rates(gt, pred):
    """Binary rates + accuracy = (TP + TN) / total_predictions"""
    tp = ((gt == 1) & (pred == 1)).sum()
    fn = ((gt == 1) & (pred == 0)).sum()
    fp = ((gt == 0) & (pred == 1)).sum()
    tn = ((gt == 0) & (pred == 0)).sum()
    
    total_pos = tp + fn
    total_neg = fp + tn
    total = len(gt)
    
    return {
        'FP_rate': fp / total_neg if total_neg > 0 else np.nan,
        'FN_rate': fn / total_pos if total_pos > 0 else np.nan,
        'TP_rate': tp / total_pos if total_pos > 0 else np.nan,
        'TN_rate': tn / total_neg if total_neg > 0 else np.nan,
        'Accuracy': (tp + tn) / total if total > 0 else np.nan
    }


# ====================== COMPUTE FOR LLMs (macro-average) ======================
results = {}
for model_name, prefix in model_map.items():
    type_rates = []
    for t in cpe_types:
        col = f'{prefix}_{t}'
        rates = compute_rates_from_confusion(col, cpe_df)
        type_rates.append(rates)
    
    avg_rates = {}
    for key in ['FP_rate', 'FN_rate', 'TP_rate', 'TN_rate', 'Accuracy']:
        vals = [r[key] for r in type_rates if not pd.isna(r[key])]
        avg_rates[key] = np.mean(vals) if vals else np.nan
    results[model_name] = avg_rates


# ====================== COMPUTE FOR AIRVIC ======================
results['AIRVIC'] = compute_binary_rates(
    airvic_df['CRO_CPE'], 
    airvic_df['Airvic_CPE']
)


# ====================== COMPUTE FOR CELLPOSE ======================
gt_cell = cellpose_df['CRO_CPE']
pred_cell = (cellpose_df['CellPose CPE Probability'] >= 0.5).astype(int)
results['Cellpose'] = compute_binary_rates(gt_cell, pred_cell)


# ====================== COMPUTE BINARY BASELINES (22-image scale) ======================
gt_binary = airvic_df['CRO_CPE']

# Always_true_binary = predict CPE in EVERY image (22 predictions)
pred_true_bin = pd.Series(1, index=gt_binary.index)
results['Always_true_binary'] = compute_binary_rates(gt_binary, pred_true_bin)

# Always_false_binary = predict no CPE in EVERY image (22 predictions)
pred_false_bin = pd.Series(0, index=gt_binary.index)
results['Always_false_binary'] = compute_binary_rates(gt_binary, pred_false_bin)


# ====================== COMPUTE LLM-SCALE BASELINES (612 predictions) ======================
# Flatten all 102 samples × 6 CPE types = 612 ground-truth labels
all_gt = pd.concat([cpe_df[f'CRO_{t}'] for t in cpe_types], ignore_index=True).values

# Always_true = predict 1 for every single cell (612 predictions)
pred_always_true = np.ones(len(all_gt), dtype=int)
results['Always_true'] = compute_binary_rates(all_gt, pred_always_true)

# Always_false = predict 0 for every single cell (612 predictions)
pred_always_false = np.zeros(len(all_gt), dtype=int)
results['Always_false'] = compute_binary_rates(all_gt, pred_always_false)


# ====================== BUILD FINAL TABLE (exact order requested) ======================
model_order = [
    'AIRVIC',
    'Cellpose',
    'Always_true_binary',
    'Always_false_binary',
    'ChatGPT',
    'Claude',
    'Gemini',
    'Grok',
    'Always_true',
    'Always_false'
]

final_data = []
for model in model_order:
    r = results[model]
    final_data.append({
        'model': model,
        'FP rate': round(r['FP_rate'], 4),
        'FN rate': round(r['FN_rate'], 4),
        'TP rate': round(r['TP_rate'], 4),
        'TN rate': round(r['TN_rate'], 4),
        'Overall Accuracy': round(r['Accuracy'], 4)
    })

final_df = pd.DataFrame(final_data)

csv_path = "aggregate-results.csv"
final_df.to_csv(csv_path, index=False)

print(f"✅ Table saved to {csv_path}")
print(final_df.to_string(index=False))