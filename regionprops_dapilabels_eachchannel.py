"""
regionprops_dapilabels_eachchannel.py

Measures morphological and intensity properties of segmented cells for all
mouse samples, using dapi dilated masks and stitched z_mean intensity images.

For each sample:
  - Mask:      <sample>/output_cellpose_masks/*dilated.tif
  - Intensity: <sample>/stitched_zmean/<sample>_stitched_<channel>_zmean.tif
  - Output:    <sample>/regionprops_dapimasks_measurements.csv

Additionally saves a merged CSV across all samples (excluding 2aryonly) to:
  <experiment_dir>/regionprops_all_samples.csv
"""

import os
import re
import numpy as np
import pandas as pd
from glob import glob
from PIL import Image
from skimage import measure

# Disable PIL decompression bomb limit — safe for trusted local files
Image.MAX_IMAGE_PIXELS = None

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

CHANNELS = ["dapi", "calbindin", "reelin", "tbr1", "t231"]

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING — no edits needed below this line
# ══════════════════════════════════════════════════════════════════════════════

def intensity_sum(regionmask, intensity_image):
    """Custom regionprops property: sum of intensities within a region."""
    return np.sum(intensity_image[regionmask])


def get_sample_id(mouse_section):
    """
    Extract the sample ID — the string before '_IF' in the folder name.
    e.g. 'htauki00660_slide1_IF' → 'htauki00660_slide1'
    """
    match = re.match(r"^(.+?)_IF$", mouse_section)
    return match.group(1) if match else mouse_section


def get_genotype(mouse_section):
    """
    Assign genotype based on folder name:
      - contains 'htauki' or is 'M16' → HTAUKI
      - contains 's305n'  or is 'M12' → S305N
    """
    name_lower = mouse_section.lower()
    if "htauki" in name_lower or mouse_section.startswith("M16"):
        return "HTAUKI"
    elif "s305n" in name_lower or mouse_section.startswith("M12"):
        return "S305N"
    else:
        return "UNKNOWN"


def find_dilated_mask(sample_dir):
    """Find the single dilated mask tif in output_cellpose_masks/."""
    masks_dir = os.path.join(sample_dir, "output_cellpose_masks")
    if not os.path.exists(masks_dir):
        return None
    matches = glob(os.path.join(masks_dir, "*dilated.tif"))
    if not matches:
        return None
    if len(matches) > 1:
        print(f"  WARNING — multiple dilated masks found, using first: "
              f"{os.path.basename(matches[0])}")
    return matches[0]


def process_sample(mouse_section):
    """
    Run regionprops for one sample across all channels.
    Returns a DataFrame with all channels combined, or None on failure.
    """
    sample_dir = os.path.join(EXPERIMENT_DIR, mouse_section)

    if not os.path.exists(sample_dir):
        print(f"  WARNING — sample folder not found, skipping.")
        return None

    # ── Find dilated dapi mask ────────────────────────────────────────────────
    mask_path = find_dilated_mask(sample_dir)
    if mask_path is None:
        print(f"  WARNING — no dilated mask found in output_cellpose_masks/, skipping.")
        return None
    print(f"  Mask: {os.path.basename(mask_path)}")

    try:
        with Image.open(mask_path) as img:
            label_image = np.array(img)
    except Exception as e:
        print(f"  ERROR loading mask: {e}")
        return None

    n_labels = len(np.unique(label_image)) - 1
    print(f"  Labels: {n_labels}")

    # ── Process each channel ─────────────────────────────────────────────────
    all_channel_dfs = []
    stitched_dir = os.path.join(sample_dir, "stitched_zmean")

    for channel in CHANNELS:
        intensity_path = os.path.join(
            stitched_dir,
            f"{mouse_section}_stitched_{channel}_zmean.tif"
        )

        if not os.path.exists(intensity_path):
            print(f"  WARNING — intensity file not found for {channel}, skipping.")
            continue

        print(f"  [{channel}] measuring...")

        try:
            with Image.open(intensity_path) as img:
                intensity_image = np.array(img)
        except Exception as e:
            print(f"  ERROR loading {channel}: {e}")
            continue

        if label_image.shape != intensity_image.shape:
            print(f"  ERROR — shape mismatch for {channel}: "
                  f"mask={label_image.shape}, intensity={intensity_image.shape}")
            continue

        regions = measure.regionprops(
            label_image,
            intensity_image,
            extra_properties=[intensity_sum]
        )

        rows = []
        for region in regions:
            rows.append({
                "label":                region.label,
                "channel":              channel,
                "area":                 region.area,
                "perimeter":            region.perimeter,
                "centroid_x":           region.centroid[1],
                "centroid_y":           region.centroid[0],
                "major_axis_length":    region.major_axis_length,
                "minor_axis_length":    region.minor_axis_length,
                "eccentricity":         region.eccentricity,
                "solidity":             region.solidity,
                "extent":               region.extent,
                "orientation":          region.orientation,
                "mean_intensity":       region.mean_intensity,
                "max_intensity":        region.max_intensity,
                "min_intensity":        region.min_intensity,
                "intensity_sum":        region.intensity_sum,
                "bbox_min_row":         region.bbox[0],
                "bbox_min_col":         region.bbox[1],
                "bbox_max_row":         region.bbox[2],
                "bbox_max_col":         region.bbox[3],
                "convex_area":          region.convex_area,
                "equivalent_diameter":  region.equivalent_diameter,
                "euler_number":         region.euler_number,
                "filled_area":          region.filled_area,
                "feret_diameter_max":   region.feret_diameter_max,
            })

        if rows:
            all_channel_dfs.append(pd.DataFrame(rows))
            print(f"    {len(rows)} regions measured.")
        else:
            print(f"    No regions found for {channel}.")

    if not all_channel_dfs:
        print(f"  ERROR — no channel data collected for {mouse_section}.")
        return None

    # ── Combine all channels into one DataFrame ───────────────────────────────
    sample_df = pd.concat(all_channel_dfs, ignore_index=True)

    # Save per-sample CSV
    output_path = os.path.join(
        sample_dir, "regionprops_dapimasks_measurements.csv"
    )
    sample_df.to_csv(output_path, index=False)
    print(f"  Saved → regionprops_dapimasks_measurements.csv  "
          f"({len(sample_df)} rows)")

    return sample_df


def main():
    print("=== Regionprops — batch run ===")
    print(f"Experiment dir : {EXPERIMENT_DIR}")
    print(f"Samples        : {len(MOUSE_SECTIONS)}\n")

    all_samples_dfs = []

    for mouse_section in MOUSE_SECTIONS:
        print(f"[{mouse_section}]")

        sample_df = process_sample(mouse_section)

        # Exclude 2aryonly from the merged output
        if sample_df is not None and "2aryonly" not in mouse_section:
            sample_df["sample"]   = get_sample_id(mouse_section)
            sample_df["genotype"] = get_genotype(mouse_section)
            all_samples_dfs.append(sample_df)

        print()

    # ── Save merged CSV across all samples ────────────────────────────────────
    if all_samples_dfs:
        merged_df = pd.concat(all_samples_dfs, ignore_index=True)

        # Reorder so sample and genotype appear as the first columns
        first_cols = ["sample", "genotype"]
        remaining  = [c for c in merged_df.columns if c not in first_cols]
        merged_df  = merged_df[first_cols + remaining]

        merged_path = os.path.join(
            EXPERIMENT_DIR, "regionprops_all_samples.csv"
        )
        merged_df.to_csv(merged_path, index=False)
        print(f"Merged CSV saved → regionprops_all_samples.csv  "
              f"({len(merged_df)} rows, "
              f"{merged_df['sample'].nunique()} samples)")
    else:
        print("No data collected — merged CSV not saved.")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
