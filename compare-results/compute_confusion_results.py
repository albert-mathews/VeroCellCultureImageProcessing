import pandas as pd
import numpy as np

# Load the CSV files (assumes they are in the current working directory)
cpe_df = pd.read_csv('cpe_confusion_table.csv')
airvic_df = pd.read_csv('../airvic-results/airvic-results.csv')

# CPE types / categories from the confusion table
cpe_types = ['Dy', 'Ro', 'V', 'D', 'G', 'Re']

# Model name to column prefix mapping
model_map = {
    'ChatGPT': 'GPT',
    'Grok': 'GRK',
    'Gemini': 'Gem',
    'Claude': 'CLD'
}

def compute_rates_from_confusion(col, df):
    """Compute TP/FP/FN/TN rates from a column where:
       1 = True Positive
       0 = True Negative
      -1 = False Negative
      -2 = False Positive
    """
    values = df[col].values
    tp = np.sum(values == 1)
    fn = np.sum(values == -1)
    fp = np.sum(values == -2)
    tn = np.sum(values == 0)
    
    total_pos = tp + fn
    total_neg = fp + tn
    
    tp_rate = tp / total_pos if total_pos > 0 else np.nan
    fn_rate = fn / total_pos if total_pos > 0 else np.nan
    fp_rate = fp / total_neg if total_neg > 0 else np.nan
    tn_rate = tn / total_neg if total_neg > 0 else np.nan
    
    return {'FP_rate': fp_rate, 'FN_rate': fn_rate, 
            'TP_rate': tp_rate, 'TN_rate': tn_rate}

# Compute macro-averaged rates for each LLM (per CPE type → macro-average)
results = {}
for model_name, prefix in model_map.items():
    type_rates = []
    for t in cpe_types:
        col = f'{prefix}_{t}'
        rates = compute_rates_from_confusion(col, cpe_df)
        type_rates.append(rates)
    
    # Macro-average across the 6 CPE types (standard technique for combining per-category results)
    avg_rates = {}
    for key in ['FP_rate', 'FN_rate', 'TP_rate', 'TN_rate']:
        vals = [r[key] for r in type_rates if not pd.isna(r[key])]
        avg_rates[key] = np.mean(vals) if vals else np.nan
    results[model_name] = avg_rates

# AIRVIC: still uses ground truth (CRO_CPE) vs prediction (Airvic_CPE)
def compute_airvic_rates():
    gt = airvic_df['CRO_CPE']
    pred = airvic_df['Airvic_CPE']
    tp = ((gt == 1) & (pred == 1)).sum()
    fn = ((gt == 1) & (pred == 0)).sum()
    fp = ((gt == 0) & (pred == 1)).sum()
    tn = ((gt == 0) & (pred == 0)).sum()
    
    total_pos = tp + fn
    total_neg = fp + tn
    
    return {
        'FP_rate': fp / total_neg if total_neg > 0 else np.nan,
        'FN_rate': fn / total_pos if total_pos > 0 else np.nan,
        'TP_rate': tp / total_pos if total_pos > 0 else np.nan,
        'TN_rate': tn / total_neg if total_neg > 0 else np.nan
    }

results['AIRVIC'] = compute_airvic_rates()

# Build the exact output DataFrame and print as CSV
out_df = pd.DataFrame({
    'ChatGPT': [
        results['ChatGPT']['FP_rate'],
        results['ChatGPT']['FN_rate'],
        results['ChatGPT']['TP_rate'],
        results['ChatGPT']['TN_rate']
    ],
    'Grok': [
        results['Grok']['FP_rate'],
        results['Grok']['FN_rate'],
        results['Grok']['TP_rate'],
        results['Grok']['TN_rate']
    ],
    'Gemini': [
        results['Gemini']['FP_rate'],
        results['Gemini']['FN_rate'],
        results['Gemini']['TP_rate'],
        results['Gemini']['TN_rate']
    ],
    'Claude': [
        results['Claude']['FP_rate'],
        results['Claude']['FN_rate'],
        results['Claude']['TP_rate'],
        results['Claude']['TN_rate']
    ],
    'AIRVIC': [
        results['AIRVIC']['FP_rate'],
        results['AIRVIC']['FN_rate'],
        results['AIRVIC']['TP_rate'],
        results['AIRVIC']['TN_rate']
    ]
}, index=['FP rate', 'FN rate', 'TP rate', 'TN rate'])

print(out_df.to_csv(index_label='-'))