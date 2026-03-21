import os
import csv

# ====================== CONFIG ======================
output_dir = "compare-results"
csv_path = os.path.join(output_dir, "cpe_confusion_table_short.csv")
tex_path = os.path.join(output_dir, "cpe_confusion_table.tex")

# Colors (LaTeX \cellcolor commands)
COLOR_MAP = {
    1: r"\cellcolor[HTML]{98FB98}",   # light green = TP / CRO asserted
    0: r"\cellcolor[HTML]{FFFFFF}",   # white = TN
    -1: r"\cellcolor[HTML]{FFFACD}",  # light yellow = FN
    -2: r"\cellcolor[HTML]{FFB6C1}"   # light pink = FP
}

cpe_labels = ["Dy", "Ro", "V", "D", "G", "Re"]
group_names = ["CRO", "ChatGPT", "Claude", "Gemini", "Grok"]

# Column indices for thick borders (0-based in the data part)
group_starts = [2, 8, 14, 20, 26]
group_ends   = [7, 13, 19, 25, 31]

# ====================== READ CSV ======================
rows = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    for row in reader:
        rows.append(row)

# ====================== BUILD LaTeX ======================
latex = r"""\begin{table}[p]
\centering
\caption{CPE Detection Confusion Table: AI Models vs CRO Ground Truth}
\label{tab:cpe_confusion}
\begin{tabular}{cc *{30}{>{\centering\arraybackslash}p{0.95cm}}}
\toprule
\multicolumn{2}{c}{\multirow{2}{*}{\textbf{Image}}} 
& \multicolumn{6}{c}{\textbf{CRO}} 
& \multicolumn{6}{c}{\textbf{ChatGPT}} 
& \multicolumn{6}{c}{\textbf{Claude}} 
& \multicolumn{6}{c}{\textbf{Gemini}} 
& \multicolumn{6}{c}{\textbf{Grok}} \\
\cmidrule(lr){3-8}\cmidrule(lr){9-14}\cmidrule(lr){15-20}\cmidrule(lr){21-26}\cmidrule(lr){27-32}
& & Dy & Ro & V & D & G & Re 
& Dy & Ro & V & D & G & Re 
& Dy & Ro & V & D & G & Re 
& Dy & Ro & V & D & G & Re 
& Dy & Ro & V & D & G & Re \\
\midrule
"""

for row in rows:
    path = row[0]
    img_id = row[1]
    latex_row = f"{path} & {img_id}"
    
    for i, val_str in enumerate(row[2:], start=2):
        try:
            val = int(val_str)
        except ValueError:
            val = 0
        color_cmd = COLOR_MAP.get(val, "")
        cell = f"{color_cmd}"   # empty cell → only color
        # Add thick vertical borders where needed
        if i in group_starts:
            cell = r"\vrule width 1.5pt " + cell
        if i in group_ends:
            cell += r" \vrule width 1.5pt"
        latex_row += f" & {cell}"
    
    latex_row += r" \\"
    latex += latex_row + "\n"

latex += r"""\bottomrule
\end{tabular}
\end{table}

% ====================== LEGEND ======================
\begin{table}[p]
\centering
\caption*{Legend}
\begin{tabular}{>{\centering\arraybackslash}p{18pt} l}
\toprule
\cellcolor[HTML]{98FB98} & CRO asserted or AI True Positive (1) \\
\cellcolor[HTML]{FFFFFF} & AI True Negative (0) \\
\cellcolor[HTML]{FFFACD} & AI False Negative (−1) \\
\cellcolor[HTML]{FFB6C1} & AI False Positive (−2) \\
\bottomrule
\end{tabular}
\end{table}
"""

# ====================== WRAP IN LANDSCAPE + OWN PAGE ======================
full_tex = r"""\clearpage
\begin{landscape}

""" + latex + r"""

\end{landscape}
\clearpage
"""

# ====================== WRITE FILE ======================
os.makedirs(output_dir, exist_ok=True)
with open(tex_path, 'w', encoding='utf-8') as f:
    f.write(full_tex)

print(f"✅ LaTeX table successfully created at:")
print(f"   {tex_path}")
print("\nHow to use in your paper (add to preamble if not already present):")
print(r"""
\usepackage{pdflscape}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{colortbl}
\usepackage{array}
""")
print("Then simply put in your document:")
print(r"   \input{compare-results/cpe_confusion_table.tex}")