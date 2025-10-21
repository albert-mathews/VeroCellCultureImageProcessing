import gspread
import pandas as pd

# Authenticate with your credentials
gc = gspread.service_account(filename="gen-lang-client-0236223593-7ec1e2e53a1d.json")

# Open your sheet (use the title as shown in Google Sheets)
sh = gc.open("virus isolation references").worksheet("refs")

# Fetch all records as a list of dictionaries
data = sh.get_all_records()

# Convert to pandas DataFrame
df = pd.DataFrame(data)

print(df.head())
