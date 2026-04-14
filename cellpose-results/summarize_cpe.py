import pandas as pd
import re
import os

# ====================== SETTINGS ======================
CSV_PATH = "cpe_metrics.csv"          # your output file
# Example CPE detection thresholds (adjust after visual check of a few images)
CIRCULARITY_CPE_THRESHOLD = 0.70
CONFLUENCY_DROP_THRESHOLD = 20.0  # % drop relative to the healthier path
# ====================================================

df = pd.read_csv(CSV_PATH)

# Parse filename for Path and Day (works with your naming like "EXP_path1_passage4_101.png" or "day3_path2...")
def parse_filename(name):
    path_match = re.search(r'path([12])', name, re.I)
    path = f"Path {path_match.group(1)}" if path_match else "Unknown"
    day_match = re.search(r'day(\d+)', name, re.I)
    day = f"Day {day_match.group(1)}" if day_match else "Unknown"
    mag_match = re.search(r'(\d+)x', name, re.I)
    mag = f"{mag_match.group(1)}x" if mag_match else "Unknown"
    return path, day, mag

df[['path', 'day', 'magnification']] = df['image'].apply(lambda x: pd.Series(parse_filename(x)))

# Grouped summary statistics
summary = df.groupby(['path', 'day', 'magnification']).agg({
    'cell_count': ['mean', 'std'],
    'confluency_percent': ['mean', 'std'],
    'mean_area_px': ['mean', 'std'],
    'mean_circularity': ['mean', 'std'],
    'mean_eccentricity': ['mean', 'std'],
    'mean_perimeter_px': ['mean', 'std']
}).round(2)

summary.columns = ['_'.join(col) for col in summary.columns]
summary = summary.reset_index()

# Save summary tables
summary.to_csv("cpe_summary_table.csv", index=False)

# Simple CPE detection report
print("\n=== CPE SUMMARY REPORT ===")
for path in summary['path'].unique():
    path_data = summary[summary['path'] == path]
    print(f"\n{path}:")
    for _, row in path_data.iterrows():
        circ = row['mean_circularity_mean']
        confl = row['confluency_percent_mean']
        print(f"  {row['day']} ({row['magnification']}): Circularity = {circ:.2f}, Confluency = {confl:.1f}%")

# Flag potential CPE differences (compares Path 1 vs Path 2)
if len(summary['path'].unique()) == 2:
    p1 = summary[summary['path'] == "Path 1"]
    p2 = summary[summary['path'] == "Path 2"]
    if not p1.empty and not p2.empty:
        diff_circ = p2['mean_circularity_mean'].mean() - p1['mean_circularity_mean'].mean()
        diff_confl = p1['confluency_percent_mean'].mean() - p2['confluency_percent_mean'].mean()
        print("\nCPE Detection Summary (Path 2 vs Path 1):")
        if diff_circ > 0.1 or diff_confl > CONFLUENCY_DROP_THRESHOLD:
            print(f"  → Strong evidence of CPE in Path 2 (higher circularity by {diff_circ:.2f}, lower confluency by {diff_confl:.1f}%)")
        elif diff_circ > 0.05 or diff_confl > 10:
            print(f"  → Possible mild CPE in Path 2")
        else:
            print("  → No clear CPE difference detected")

print(f"\nFull summary saved to results/cpe_summary_table.csv")
print("Open this CSV in Excel/R for further statistical tests (t-test, etc.).")