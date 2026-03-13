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
    <div style="width: fit-content; margin: 20px auto;">
    <table>
        <thead>
            <tr>
                <th colspan="2" style="border-left: 2px solid #333; border-right: 2px solid #333;">Image</th>
"""
for i, group in enumerate(group_names):
    border_left = "border-left: 2px solid #333;" if i > 0 else ""
    html += '<th colspan="6" style="{0} border-right: 2px solid #333;">{1}</th>\n'.format(border_left, group)
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
        html += '<th style="{0}" class="data-header">{1}</th>\n'.format(style, label)
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
            html += '                <td style="{0}">{1}</td>\n'.format(style, val)
        else:  # data cells
            try:
                v = int(val)
            except ValueError:
                v = 0
            bg = COLOR_MAP.get(v, "#FFFFFF")
            style = "background-color: {0};".format(bg)
            if i in group_starts:
                style += " border-left: 2px solid #333;"
            if i in group_ends:
                style += " border-right: 2px solid #333;"
            html += '                <td style="{0}" class="data-cell"></td>\n'.format(style)
    html += "            </tr>\n"
html += """
        </tbody>
    </table>
    <table style="border: 2px solid #333; margin-top: 20px; margin-left: 0; border-collapse: collapse;">
        <tr>
            <td style="width: 15px; height: 15px; background-color: #98FB98; border: 1px solid #ccc;"></td>
            <td style="border: 1px solid #ccc; text-align: left; padding-left: 10px;">CRO asserted or AI True Positive</td>
        </tr>
        <tr>
            <td style="width: 15px; height: 15px; background-color: #FFFFFF; border: 1px solid #ccc;"></td>
            <td style="border: 1px solid #ccc; text-align: left; padding-left: 10px;">AI True Negative</td>
        </tr>
        <tr>
            <td style="width: 15px; height: 15px; background-color: #FFFACD; border: 1px solid #ccc;"></td>
            <td style="border: 1px solid #ccc; text-align: left; padding-left: 10px;">AI False Negative</td>
        </tr>
        <tr>
            <td style="width: 15px; height: 15px; background-color: #FFB6C1; border: 1px solid #ccc;"></td>
            <td style="border: 1px solid #ccc; text-align: left; padding-left: 10px;">AI False Positive</td>
        </tr>
    </table>
    </div>
</body>
</html>
"""

# Save HTML
html_path = os.path.join(output_dir, "cpe_confusion_table.html")
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML file created at: {html_path}")