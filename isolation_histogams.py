import gspread
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Authenticate using your service account JSON key
gc = gspread.service_account(filename="gen-lang-client-0236223593-7ec1e2e53a1d.json")

# Open your sheet (by name or by key)
sh = gc.open("virus isolation references").worksheet("refs")

# Publication year
values1 = sh.get("C3:C22")
values2 = sh.get("C30:C42")

flat1 = [float(v[0]) for v in values1 if v and v[0] != ""]
flat2 = [float(v[0]) for v in values2 if v and v[0] != ""]
flat = flat1+flat2
s = pd.Series(flat)
# Plot histogram
plt.figure()
plt.hist(s, bins=len(flat)*2, edgecolor='black')
plt.xlabel("Publication Year")
plt.ylabel("Count")
plt.title("Histogram of Publication Year")
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Specimen Sample Type
headers = sh.get("AC2:AI2")[0]  # one row, list of header names
values = sh.get("AC28:AI28")[0]  # take the first (and only) row
incidence_set1 = [float(v) if v != "" else 0 for v in values]
values = sh.get("AC48:AI48")[0]  # take the first (and only) row
incidence_set2 = [float(v) if v != "" else 0 for v in values]
x = np.arange(len(headers))
plt.figure()  # new figure window
plt.bar(x, incidence_set1, color='skyblue', edgecolor='black', label='Virus Isolation')
plt.bar(x, incidence_set2, bottom=incidence_set1, color='orange', edgecolor='black', label='SPT')
plt.xticks(x, headers, rotation=45, ha='right')
plt.ylabel("Incendece (%)")
plt.title("Incedence of Sample Type")
plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.legend()


# Inoculum Prepration Method
headers = sh.get("T2:AB2")[0]  # one row, list of header names
values = sh.get("T28:AB28")[0]  # take the first (and only) row
incidence_set1 = [float(v) if v != "" else 0 for v in values]
values = sh.get("T48:AB48")[0]  # take the first (and only) row
incidence_set2 = [float(v) if v != "" else 0 for v in values]
x = np.arange(len(headers))
plt.figure()  # new figure window
plt.bar(x, incidence_set1, color='skyblue', edgecolor='black', label='Virus Isolation')
plt.bar(x, incidence_set2, bottom=incidence_set1, color='orange', edgecolor='black', label='SPT')
plt.xticks(x, headers, rotation=45, ha='right')
plt.ylabel("Incendece (%)")
plt.title("Incedence of Inoculum Prepration Method")
plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.legend()

# Centrifuge value
values = sh.get("X3:X20")
flat = [float(v[0]) for v in values if v and v[0] != ""]
s = pd.Series(flat)
# Plot histogram
plt.figure()
plt.hist(s, bins=max(len(flat),40), edgecolor='black')
plt.xlabel("Centrifuge x g")
plt.ylabel("Count ")
plt.title("Histogram of Centrifuge Spin")
plt.grid(axis='y', linestyle='--', alpha=0.7)

# cell line
data = sh.get("H3:H22")
flat_data = [row[0] for row in data if row and row[0].strip() != ""]  # flatten and skip blanks
s = pd.Series(flat_data)
counts = s.value_counts()  # sorted by frequency
plt.figure()
plt.bar(counts.index, counts.values, color='skyblue', edgecolor='black')
plt.xticks(rotation=45, ha='right')
plt.ylabel("Count")
plt.title("Histogram of Cell Line Occurrences")
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()


#incedence of detection methods
headers = sh.get("J2:Q2")[0]  # one row, list of header names
values = sh.get("J28:Q28")[0]  # take the first (and only) row
incidence_set1 = [float(v) if v != "" else 0 for v in values]
values = sh.get("J48:Q48")[0]  # take the first (and only) row
incidence_set2 = [float(v) if v != "" else 0 for v in values]
x = np.arange(len(headers))
plt.figure()  # new figure window
plt.bar(x, incidence_set1, color='skyblue', edgecolor='black', label='Virus Isolation')
plt.bar(x, incidence_set2, bottom=incidence_set1, color='orange', edgecolor='black', label='SPT')
plt.xticks(x, headers, rotation=45, ha='right')
plt.ylabel("Incendece (%)")
plt.title("Incedence of Detection Method")
plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.legend()


# FBS
values = sh.get("AK3:AK44")
vector1 = [float(v[0]) for v in values if v and v[0] != ""]
values = sh.get("AL3:AL44")
vector2 = [float(v[0]) for v in values if v and v[0] != ""]

unique_values = np.unique(np.concatenate((vector1, vector2)))

min_val = min(min(vector1), min(vector2))
max_val = max(max(vector1), max(vector2))
bins = np.linspace(min_val, max_val, 30)  # 30 bins

hist1 = np.array([np.sum(vector1 == value) for value in unique_values])
hist2 = np.array([np.sum(vector2 == value) for value in unique_values])

# Calculate the x coordinates for the bars
x = np.arange(len(unique_values))
bar_width = 0.4
x1 = x - bar_width / 2
x2 = x + bar_width / 2

plt.figure()
plt.bar(x1, hist1, width=bar_width, alpha=0.7, label='Pre-Inoculation', color='skyblue', edgecolor='black')
plt.bar(x2, hist2, width=bar_width, alpha=0.7, label='Post-Inculation', color='orange', edgecolor='black')

# Add labels and title
plt.xticks(x, unique_values*100)
plt.xlabel('FBS Concentration (%)')
plt.ylabel('Count')
plt.title('Histogram of FBS Concentration')
plt.legend()


# show all plots
plt.show()
