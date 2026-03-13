import os
import csv

# Assuming output_path and output_dir from previous code
output_dir = "compare-results"
output_path = os.path.join(output_dir, "cpe_confusion_table_short.csv")

# Colors
COLOR_MAP = {
    1: "#98FB98",  # Pale green for TP / Present
    0: "#FFFFFF",  # White for TN / Absent
    -1: "#FFFACD",  # Lemon chiffon for FN
    -2: "#FFB6C1"   # Light pink for FP
}

# CPE labels
cpe_labels = ["Dy", "Ro", "V", "D", "G", "Re"]

# Group names
group_names = ["CRO", "ChatGPT", "Claude", "Gemini", "Grok"]

# Column indices for groups (starting after path=0, id=1)
group_starts = [2, 8, 14, 20, 26]
group_ends = [7, 13, 19, 25, 31]

# Read CSV
rows = []
with open(output_path, 'r') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Skip header
    for row in reader:
        rows.append(row)

# Generate HTML
html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CPE Confusion Table</title>
    <style>
        body {
            font-family: Arial, sans-serif;
        }
        table {
            border-collapse: collapse;
            border: 2px solid #333;
            margin: 20px auto;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            background-color: #fff;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 4px 6px;
            text-align: center;
            font-size: 12px;
        }
        th.data-header, td.data-cell {
            width: 15px;
        }
        th {
            background-color: #f4f4f4;
            font-weight: bold;
            color: #333;
        }
        thead tr:last-child th {
            border-bottom: 2px solid #333 !important;
        }
        tr:nth-child(even) {
            background-color: #fafafa;
        }
        tr:hover {
            background-color: #f0f0f0;
        }
    </style>
</head>
<body>
    <table>
        <thead>
            <tr>
                <th colspan="2" style="border-left: 2px solid #333; border-right: 2px solid #333;">Image</th>
"""
for i, group in enumerate(group_names):
    border_left = "border-left: 2px solid #333;" if i > 0 else ""
    html += f'<th colspan="6" style="{border_left} border-right: 2px solid #333;">{group}</th>\n'
html += """
            </tr>
            <tr>
                <th style="border-left: 2px solid #333;">path</th>
                <th style="border-right: 2px solid #333;">id</th>
"""
col_index = 2
for group_idx in range(len(group_names)):
    for label in cpe_labels:
        style = ""
        if col_index in group_starts:
            style += "border-left: 2px solid #333; "
        if col_index in group_ends:
            style += "border-right: 2px solid #333; "
        html += f'<th style="{style}" class="data-header">{label}</th>\n'
        col_index += 1
html += """
            </tr>
        </thead>
        <tbody>
"""
for row in rows:
    html += "            <tr>\n"
    for i, val in enumerate(row):
        if i < 2:  # path and id
            style = ""
            if i == 0:
                style = "border-left: 2px solid #333;"
            if i == 1:
                style = "border-right: 2px solid #333;"
            html += f'                <td style="{style}">{val}</td>\n'
        else:  # data cells
            try:
                v = int(val)
            except ValueError:
                v = 0
            bg = COLOR_MAP.get(v, "#FFFFFF")
            style = f"background-color: {bg};"
            if i in group_starts:
                style += " border-left: 2px solid #333;"
            if i in group_ends:
                style += " border-right: 2px solid #333;"
            html += f'                <td style="{style}" class="data-cell"></td>\n'
    html += "            </tr>\n"
html += """
        </tbody>
    </table>
</body>
</html>
"""

# Save HTML
html_path = os.path.join(output_dir, "cpe_confusion_table.html")
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML file created at: {html_path}")