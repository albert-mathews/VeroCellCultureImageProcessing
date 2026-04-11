import os
import csv

# ====================== CONFIG ======================
output_dir = "compare-results"
csv_path   = os.path.join(output_dir, "cpe_confusion_table_short.csv")
tex_path   = os.path.join(output_dir, "cpe_confusion_table.tex")

# Colors (now properly defined)
COLOR_MAP = {
    1: r"\cellcolor{TPgreen}",   # True Positive / CRO yes
    0: r"\cellcolor{TNwhite}",   # True Negative
    -1: r"\cellcolor{FNyellow}", # False Negative
    -2: r"\cellcolor{FPred}"     # False Positive
}

cpe_labels = ["Dy", "Ro", "V", "D", "G", "Re"]
group_names = ["CRO", "ChatGPT", "Claude", "Gemini", "Grok"]

# ====================== READ CSV ======================
rows = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    for row in reader:
        rows.append(row)

# ====================== BUILD LaTeX (fixed version) ======================
latex_content = r"""\begin{table}[p]
\centering
\small
\setlength{\tabcolsep}{2pt}
\caption{CPE Detection Confusion Table: AI Models vs CRO Ground Truth}
\label{tab:cpe_confusion}

\begin{tabular}{cc *{30}{>{\centering\arraybackslash}p{0.58cm}}}
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
        except:
            val = 0
        color_cmd = COLOR_MAP.get(val, "")
        cell = color_cmd   # empty cell = only color
        latex_row += f" & {cell}"
    
    latex_row += r" \\"
    latex_content += latex_row + "\n"

latex_content += r"""\bottomrule
\end{tabular}
\end{table}

% ====================== LEGEND ======================
\begin{table}[p]
\centering
\caption*{Legend}
\begin{tabular}{>{\centering\arraybackslash}p{18pt} l}
\toprule
\cellcolor{TPgreen}   & CRO asserted or AI True Positive (1) \\
\cellcolor{TNwhite}   & AI True Negative (0) \\
\cellcolor{FNyellow}  & AI False Negative (−1) \\
\cellcolor{FPred}     & AI False Positive (−2) \\
\bottomrule
\end{tabular}
\end{table}
"""

# ====================== FULL DOCUMENT SNIPPET (ready for Overleaf) ======================
full_tex = r"""\clearpage
\begin{landscape}

% Required packages (already in your main.tex, but safe to have here)
\usepackage{pdflscape}
\usepackage[table]{xcolor}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{array}

% Define the exact colors used
\definecolor{TPgreen}{HTML}{98FB98}
\definecolor{TNwhite}{HTML}{FFFFFF}
\definecolor{FNyellow}{HTML}{FFFACD}
\definecolor{FPred}{HTML}{FFB6C1}

""" + latex_content + r"""

\end{landscape}
\clearpage
"""

# ====================== SAVE ======================
os.makedirs(output_dir, exist_ok=True)
with open(tex_path, 'w', encoding='utf-8') as f:
    f.write(full_tex)

print(f"✅ FIXED LaTeX table saved to:")
print(f"   {tex_path}")
print("\nJust upload this new file to Overleaf → Recompile. It should now:")
print("   • Fit perfectly in landscape")
print("   • Show correct colors")
print("   • Have no 'Undefined color model HTML' error")