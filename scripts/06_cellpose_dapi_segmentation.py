"""
cellpose_dapi_segmentation.py

Runs Cellpose segmentation on all dapi z_max stitched images using a
pretrained model, and saves the resulting masks as uint16 .tif files
in the same folder as the input images.

Usage:
    python cellpose_dapi_segmentation.py
"""

import os
import glob

import numpy as np
from tifffile import imread, imwrite
from cellpose import models

# ══════════════════════════════════════════════════════════════════════════════
# USER CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# Folder containing all dapi z_max stitched images across mice
IMAGE_DIR = r"W:\Paula Cauhy\cellpose"

# Path to the pretrained Cellpose model
PATH_TO_MODEL = r"C:\Users\Pam\.cellpose\models\CP_DAPI_ISS"

# Cellpose parameters
CELLPOSE_PARAMS = {
    "channels":          [0, 0],  # grayscale
    "batch_size":        4,
    "anisotropy":        1.0,
    "cellprob_threshold": 0,
    "flow_threshold":    0.4,     # not used in 3D mode
    "stitch_threshold":  0,
    "do_3D":             False,
    "progress":          True,
}

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING — no edits needed below this line
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # Collect all .tif files in the image directory
    image_files = glob.glob(os.path.join(IMAGE_DIR, "*.tif"))

    if not image_files:
        print(f"No .tif files found in: {IMAGE_DIR}")
        return

    print(f"Found {len(image_files)} image(s) to segment.")
    print(f"Model: {PATH_TO_MODEL}\n")

    # Load the pretrained Cellpose model
    model = models.CellposeModel(pretrained_model=PATH_TO_MODEL, gpu=True)

    for image_path in image_files:
        print(f"Processing: {os.path.basename(image_path)}")

        img = imread(image_path)
        masks, flows, styles = model.eval(
            img.astype(np.uint32),
            **CELLPOSE_PARAMS,
            z_axis=None,
            channel_axis=None,
        )

        # Save mask next to the input image with _mask suffix
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        mask_path = os.path.join(IMAGE_DIR, base_name + "_mask.tif")
        imwrite(mask_path, masks.astype("uint16"))

        print(f"  Mask saved to: {mask_path}")

    print("\n=== Segmentation complete ===")


if __name__ == "__main__":
    main()
