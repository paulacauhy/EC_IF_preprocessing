"""
enlarge_masks.py

Expands Cellpose segmentation masks for all mouse samples using
skimage's expand_labels.

For each sample, reads every .tif file ending in 'mask' from:
    <experiment_dir>/<sample>/output_cellpose_masks/

Saves the dilated mask as:
    <experiment_dir>/<sample>/output_cellpose_masks/<original_name>_dilated.tif
"""

import os
import glob

import numpy as np
from PIL import Image
from skimage.segmentation import expand_labels

# ══════════════════════════════════════════════════════════════════════════════
# USER CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

EXPERIMENT_DIR = "/media/paulacauhy/Elements1/1503_MEC_horizo_TBR1_RELN_CALB_T231"

MOUSE_SECTIONS = [
    "2aryonly_slide2_IF",
    "htauki00660_slide1_IF",
    "htauki00661_slide1_IF",
    "htauki01513_slide1_IF",
    "htauki01514_slide2_IF",
    "htauki01514_slide4_IF",
    "M12_slide1_IF",
    "M16_slide2_IF",
    "M16_slide4_IF",
    "s305n01144_slide3_IF",
    "s305n01145_slide1_IF",
    "s305n01145_slide3_IF",
    "s305n11383_slide4_IF",
    "s305n11384_slide1_IF",
]

EXPANSION_PIXELS = 10   # adjust to control how many pixels each mask expands

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING 
# ══════════════════════════════════════════════════════════════════════════════

def process_sample(sample_dir):
    """Expand all masks in one sample's output_cellpose_masks folder."""

    masks_dir = os.path.join(sample_dir, "output_cellpose_masks")

    if not os.path.exists(masks_dir):
        print(f"  WARNING — output_cellpose_masks folder not found, skipping.")
        return

    # Match only files whose name ends with 'mask.tif'
    mask_files = glob.glob(os.path.join(masks_dir, "*mask.tif"))

    if not mask_files:
        print(f"  WARNING — no mask.tif files found in: {masks_dir}")
        return

    print(f"  Found {len(mask_files)} mask file(s).")

    for mask_path in mask_files:
        filename  = os.path.basename(mask_path)
        base_name = os.path.splitext(filename)[0]
        print(f"  Processing: {filename}")

        # Load mask
        with Image.open(mask_path) as img:
            labels = np.array(img)

        # Expand labels
        labels_enlarged = expand_labels(labels, distance=EXPANSION_PIXELS)

        # Save dilated mask
        dilated_path = os.path.join(masks_dir, base_name + "_dilated.tif")
        Image.fromarray(labels_enlarged.astype(np.uint16)).save(dilated_path)

        print(f"    Original labels : {len(np.unique(labels)) - 1}")
        print(f"    Expanded labels : {len(np.unique(labels_enlarged)) - 1}")
        print(f"    Saved → {os.path.basename(dilated_path)}")


def main():
    print("=== Mask enlargement — batch run ===")
    print(f"Experiment dir   : {EXPERIMENT_DIR}")
    print(f"Expansion pixels : {EXPANSION_PIXELS}")
    print(f"Samples          : {len(MOUSE_SECTIONS)}\n")

    for mouse_section in MOUSE_SECTIONS:
        print(f"[{mouse_section}]")
        sample_dir = os.path.join(EXPERIMENT_DIR, mouse_section)

        if not os.path.exists(sample_dir):
            print(f"  WARNING — sample folder not found, skipping.")
            continue

        process_sample(sample_dir)
        print()

    print("=== Done ===")


if __name__ == "__main__":
    main()
