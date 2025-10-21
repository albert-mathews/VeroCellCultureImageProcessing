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
plt.hist(s, bins=len(flat), edgecolor='black')
plt.xlabel("Publication Year")
plt.ylabel("Count")
plt.title("Histogram of Publication Year")

# cell line
# values = sh.get("H3:H22")
# flat = [float(v[0]) for v in values if v and v[0] != ""]
# s = pd.Series(flat)
# Plot histogram
# plt.hist(s, bins=len(flat), edgecolor='black')
# plt.xlabel("Cell Name")
# plt.ylabel("Count")
# plt.title("Histogram of Cells Used in Culture")


#incedence of detection methods
headers = sh.get("I2:Q2")[0]  # one row, list of header names
data = sh.get("I3:Q22")
cols = list(zip(*data))  # now each item is a column
y_counts = [sum(1 for v in col if v.strip().lower() == 'y') for col in cols]
x = np.arange(len(headers))
plt.figure()
plt.bar(x, y_counts, color='skyblue', edgecolor='black')
plt.xticks(x, headers, rotation=45, ha='right')
plt.ylabel("Count of 'y'")
plt.title("True counts per data element")
plt.tight_layout()




# show all plots
plt.show()
