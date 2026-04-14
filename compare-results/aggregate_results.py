import pandas as pd
import numpy as np

# ====================== LOAD DATA ======================
# Update paths if your files are in different locations
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
    """For LLMs: compute TP/FP/FN/TN + accuracy PER CPE TYPE
       Accuracy per type = (num_TP + num_TN) / num_predictions
       where num_predictions = number of rows in cpe_df (62)"""
    values = df[col].values
    tp = np.sum(values == 1)
    fn = np.sum(values == -1)
    fp = np.sum(values == -2)
    tn = np.sum(values == 0)
    
    total_pos = tp + fn
    total_neg = fp + tn
    total = len(values)          # this is the num_predictions for this CPE type
    
    return {
        'FP_rate': fp / total_neg if total_neg > 0 else np.nan,
        'FN_rate': fn / total_pos if total_pos > 0 else np.nan,
        'TP_rate': tp / total_pos if total_pos > 0 else np.nan,
        'TN_rate': tn / total_neg if total_neg > 0 else np.nan,
        'Accuracy': (tp + tn) / total if total > 0 else np.nan
    }


def compute_binary_rates(gt, pred):
    """For AIRVIC, CellPose, Always True, Always False:
       Accuracy = (num_TP + num_TN) / num_predictions
       where num_predictions = 22 (number of images)"""
    tp = ((gt == 1) & (pred == 1)).sum()
    fn = ((gt == 1) & (pred == 0)).sum()
    fp = ((gt == 0) & (pred == 1)).sum()
    tn = ((gt == 0) & (pred == 0)).sum()
    
    total_pos = tp + fn
    total_neg = fp + tn
    total = len(gt)              # this is 22 for the binary data
    
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
    
    # Macro-average across the 6 CPE types (as requested)
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
# CellPose returns a probability; we binarize with the standard threshold of 0.5
gt_cell = cellpose_df['CRO_CPE']
prob_cell = cellpose_df['CellPose CPE Probability']
pred_cell = (prob_cell >= 0.5).astype(int)

results['Cellpose'] = compute_binary_rates(gt_cell, pred_cell)


# ====================== COMPUTE TRIVIAL BASELINES (on the 22-image binary task) ======================
gt_binary = airvic_df['CRO_CPE']

# Always True = predicts CPE detected in EVERY image
pred_always_true = pd.Series(1, index=gt_binary.index)
results['Always True'] = compute_binary_rates(gt_binary, pred_always_true)

# Always False = predicts no CPE in EVERY image
pred_always_false = pd.Series(0, index=gt_binary.index)
results['Always False'] = compute_binary_rates(gt_binary, pred_always_false)


# ====================== BUILD FINAL TABLE ======================
model_order = ['AIRVIC', 'Cellpose', 'ChatGPT', 'Claude', 'Gemini', 'Grok', 
               'Always True', 'Always False']

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