import gspread
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Authenticate using your service account JSON key
gc = gspread.service_account(filename="gen-lang-client-0236223593-7ec1e2e53a1d.json")

# Open your sheet (by name or by key)
sh = gc.open("virus isolation references").worksheet("refs")

# Publication year
values = sh.get("B3:B22")
flat = [float(v[0]) for v in values if v and v[0] != ""]
s = pd.Series(flat)
# Plot histogram
plt.figure()
plt.hist(s, bins=len(flat)*2, edgecolor='black')
plt.xlabel("Publication Year")
plt.ylabel("Count")
plt.title("Histogram of Publication Year")
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Specimen Sample Type
headers = sh.get("AA2:AF2")[0]  # one row, list of header names
values = sh.get("AA27:AF27")[0]  # take the first (and only) row
numeric_values = [float(v) if v != "" else 0 for v in values]
x = np.arange(len(headers))
plt.figure()  # new figure window
plt.bar(x, numeric_values, color='skyblue', edgecolor='black')
plt.xticks(x, headers, rotation=45, ha='right')
plt.ylabel("Incendece (%)")
plt.title("Incedence of Sample Type")
plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Inoculum Prepration Method
headers = sh.get("S2:Z2")[0]  # one row, list of header names
values = sh.get("S27:Z27")[0]  # take the first (and only) row
numeric_values = [float(v) if v != "" else 0 for v in values]
x = np.arange(len(headers))
plt.figure()  # new figure window
plt.bar(x, numeric_values, color='skyblue', edgecolor='black')
plt.xticks(x, headers, rotation=45, ha='right')
plt.ylabel("Incendece (%)")
plt.title("Incedence of Inoculum Prepration Method")
plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.7)


# Centrifuge value
values = sh.get("W3:W20")
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
# values = sh.get("H3:H22")
# flat = [float(v[0]) for v in values if v and v[0] != ""]
# s = pd.Series(flat)
# Plot histogram
# plt.hist(s, bins=len(flat), edgecolor='black')
# plt.xlabel("Cell Name")
# plt.ylabel("Count")
# plt.title("Histogram of Cells Used in Culture")
data = sh.get("G3:G22")
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
headers = sh.get("I2:Q2")[0]  # one row, list of header names
values = sh.get("I27:Q27")[0]  # take the first (and only) row
numeric_values = [float(v) if v != "" else 0 for v in values]
x = np.arange(len(headers))
plt.figure()  # new figure window
plt.bar(x, numeric_values, color='skyblue', edgecolor='black')
plt.xticks(x, headers, rotation=45, ha='right')
plt.ylabel("Incedence (%)")
plt.title("Incedence of Detection Method")
plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.7)


# FBS
values = sh.get("B3:B22")
flat = [float(v[0]) for v in values if v and v[0] != ""]
s = pd.Series(flat)
# Plot histogram
plt.figure()
plt.hist(s, bins=len(flat)*2, edgecolor='black')
plt.xlabel("Publication Year")
plt.ylabel("Count")
plt.title("Histogram of Publication Year")
plt.grid(axis='y', linestyle='--', alpha=0.7)


# show all plots
plt.show()
