import os
import zipfile
from pathlib import Path

print("=== DVICE Model Diagnostic ===\n")

root = Path('.')
resources_dir = root / 'resources'

print(f"Current folder: {Path.cwd()}")
print(f"Resources folder exists: {resources_dir.exists()}\n")

model_files = ['model1.keras', 'model2.keras', 'model3.keras']

for mf in model_files:
    model_path = resources_dir / mf
    full_path = str(model_path.resolve().absolute())
    print(f"Checking: {mf}")
    print(f"   Full path: {full_path}")
    
    if model_path.exists():
        size = model_path.stat().st_size
        print(f"   File size: {size:,} bytes ({size/1024/1024:.1f} MB)")
        
        # Test if it's a valid .keras zip file
        try:
            with zipfile.ZipFile(model_path) as z:
                print("   ✅ VALID .keras zip file")
                print(f"   Contains {len(z.namelist())} files")
        except Exception as e:
            print(f"   ❌ NOT a valid .keras file: {e}")
    else:
        print("   ❌ File not found!")
    print("-" * 60)