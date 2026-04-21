from pathlib import Path
import zipfile

print("=== Checking resources.zip and extracted models ===\n")

root = Path('.')
zip_path = root / 'resources.zip'
resources_dir = root / 'resources'

print(f"resources.zip exists: {zip_path.exists()}")
print(f"resources.zip size: {zip_path.stat().st_size:,} bytes\n")

# 1. Inspect the zip file itself
try:
    with zipfile.ZipFile(zip_path) as z:
        print("✅ resources.zip is a valid zip file")
        print(f"   Contains {len(z.namelist())} files")
        keras_files = [f for f in z.namelist() if f.endswith('.keras')]
        print(f"   .keras files inside zip: {keras_files}\n")
except Exception as e:
    print(f"❌ resources.zip is corrupted: {e}")

# 2. Check the extracted .keras files (magic bytes)
print("Checking extracted models:")
for mf in ['model1.keras', 'model2.keras', 'model3.keras']:
    model_path = resources_dir / mf
    if model_path.exists():
        with open(model_path, 'rb') as f:
            header = f.read(8)
        print(f"   {mf}: size = {model_path.stat().st_size:,} bytes | first bytes = {header}")
    else:
        print(f"   {mf}: not found")