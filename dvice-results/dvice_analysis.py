#!/usr/bin/env python3
"""
dvice_analysis.py

This script processes 101 PNG microscopy images using the three DVICE Keras models
(model1.keras, model2.keras, model3.keras) for detection of virus-induced cytopathic effects (CPE).
It closely mimics the preprocessing and prediction workflow from the DVICE notebook/demo
(without direct copy-paste of notebook cells) to ensure compatibility with the trained EfficientNet-B3-based models.

Key decisions based on notebook + paper (PMC11180103 / Nature Communications 2024):
- Images are grayscale transmitted-light microscopy (TL) images of cell cultures (infected/uninfected by AdV, VACV, SARS-CoV-2, RV, etc.).
- prepforML preprocessing is mandatory: percentile rescale (1-99), resize to 224x224 with bicubic interpolation, clip [0,1], convert to uint8, and gray2rgb.
  This matches the exact input format expected by the models (EfficientNet-B0/B3 backbone + classification head).
- Each model is a binary classifier (uninfected vs. infected) trained on specific virus panels/cell lines for robust CPE detection.
  Output of model.predict is shape (1, 2) with softmax probabilities: index 0 = uninfected, index 1 = infected (standard convention confirmed via notebook's np.argmax usage and binary task).
- We extract the "infected" probability (pred[0][1]) for each model as the primary result column.
- Additional columns for predicted class (0/1) and raw probabilities are included for completeness/auditability (paper emphasizes probability-based infectivity scoring).
- Filename parsing: e.g., "EXP_path2_passage4_302.png" → path=2, id=302 (using regex for robustness).
- Results saved to dvice-results.csv in the script's root folder.
- Script is standalone, runs in the root folder containing resources/ and ../converted_pngs/.

Dependencies (must be installed in environment): tensorflow, scikit-image, numpy, pandas, pathlib, re
"""

import os
import glob
import re
import numpy as np
import pandas as pd
import skimage.io
import skimage.transform
import skimage.exposure
import skimage.color
import tensorflow as tf
from pathlib import Path


def prep_for_ml(img, img_size=(224, 224), interpolation='Bi-cubic'):
    """
    Preprocess a single grayscale microscopy image exactly as required by DVICE models.
    Mimics the notebook's prepforML function logic for 100% compatibility:
      - Convert to float32
      - Robust intensity rescaling using 1st/99th percentiles (handles varying illumination)
      - Resize to 224x224 (EfficientNet input size) with bicubic interpolation
      - Clip to [0,1], convert to uint8, and expand to RGB
    This step is critical because the models were trained on this exact normalized 224x224x3 uint8 RGB format.
    """
    # Step 1: Convert to float and robust percentile-based contrast normalization (per notebook)
    proc_im = img.astype(np.float32)
    p_low, p_high = np.percentile(proc_im, (1, 99))
    proc_im = skimage.exposure.rescale_intensity(proc_im, in_range=(p_low, p_high))

    # Step 2: Resize if needed (bicubic = order 3)
    inter_opt = {'Nearest-neighbor': 0, 'Bi-linear': 1, 'Bi-quadratic': 2, 'Bi-cubic': 3,
                 'Bi-quartic': 4, 'Bi-quintic': 5}
    if proc_im.shape != img_size:
        proc_im = skimage.transform.resize(
            proc_im,
            output_shape=img_size,
            order=inter_opt[interpolation],
            preserve_range=True,
            anti_aliasing=True
        )

    # Step 3: Clip, to uint8, and convert grayscale to RGB (models expect 3-channel input)
    proc_im = np.clip(proc_im, 0, 1)
    proc_im = skimage.img_as_ubyte(proc_im)
    proc_im = skimage.color.gray2rgb(proc_im)

    return proc_im


def main():
    # Paths (relative to script root folder)
    root_dir = Path('.')
    models_dir = root_dir / 'resources'
    images_dir = root_dir / '..' / 'converted_pngs'

    # Verify paths
    if not models_dir.exists():
        raise FileNotFoundError(f"Models directory not found: {models_dir}")
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    # Load the three DVICE models once (EfficientNet-B3 based binary classifiers)
    # === MODEL LOADING - Fixed for legacy HDF5 format ===
    # if you extracted modelX.keras from resources.zip, you need to change the file extension to modelX.h5
    model_files = ['model1.h5', 'model2.h5', 'model3.h5']
    models = []
    for mf in model_files:
        model_path = models_dir / mf
        full_path = str(model_path.resolve().absolute())
        
        print(f"Loading model: {full_path}")
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {full_path}")
        
        # Load legacy HDF5 models (this is what your files actually are)
        model = tf.keras.models.load_model(
            full_path,
            compile=False,      # Important - models were saved without optimizer state
            safe_mode=False
        )
        models.append(model)
        print(f"✅ Successfully loaded {mf}")

    # Find all 101 PNG images
    png_files = sorted(list(images_dir.glob('*.png')))
    print(f"Found {len(png_files)} PNG images to process.")

    results = []
    for png_path in png_files:
        filename = png_path.name
        print(f"Processing: {filename}")

        # Parse path and id from filename (e.g. EXP_path2_passage4_302.png)
        # Regex is robust to slight naming variations in the 101-image dataset
        path_match = re.search(r'path(\d+)', filename, re.IGNORECASE)
        path_val = int(path_match.group(1)) if path_match else None

        id_match = re.search(r'_(\d+)\.png$', filename)
        id_val = int(id_match.group(1)) if id_match else None

        if path_val is None or id_val is None:
            print(f"  Warning: Could not parse path/id from {filename} - skipping")
            continue

        # Load raw image (grayscale PNG expected)
        raw_img = skimage.io.imread(str(png_path))
        # Ensure 2D grayscale (in case any PNG is RGB)
        if len(raw_img.shape) == 3:
            raw_img = skimage.color.rgb2gray(raw_img)

        # Preprocess exactly as required by DVICE models
        preprocessed = prep_for_ml(raw_img)
        # Add batch dimension: (1, 224, 224, 3) uint8 RGB
        input_batch = np.expand_dims(preprocessed, axis=0)

        # Run predictions with all three models
        model_results = {}
        for i, model in enumerate(models, start=1):
            pred = model.predict(input_batch, verbose=0)  # shape (1, 2)
            pred_probs = pred[0]  # [uninfected_prob, infected_prob]

            # Per paper/notebook: binary classification → infected probability is index 1
            infected_prob = float(pred_probs[1])
            predicted_class = int(np.argmax(pred_probs))  # 0=uninfected, 1=infected

            model_results[f'model{i}_infected'] = infected_prob
            model_results[f'model{i}_class'] = predicted_class
            model_results[f'model{i}_probs'] = pred_probs.tolist()  # raw for debugging

        # Store row
        row = {
            'path': path_val,
            'id': id_val,
            **model_results
        }
        results.append(row)

    # Save to CSV (as specified: path, id, <results columns>)
    df = pd.DataFrame(results)
    csv_path = root_dir / 'dvice-results.csv'
    df.to_csv(csv_path, index=False)
    print(f"\nProcessing complete! Results saved to: {csv_path}")
    print(f"Columns: {list(df.columns)}")
    print(f"Processed {len(results)} images successfully.")


if __name__ == "__main__":
    main()