"""
stack_unstack_3d_tifs_perchannel.py

Prepares input for BaSiC flat-field correction and applies the estimated
flat-field back to every z-plane of every tile.

WORKFLOW:
    1. Edit the USER CONFIGURATION section below.
    2. Run this script — for each channel it stacks one representative z-plane
       per tile into a single merged .tif.
    3. Open each merged_<channel>.tif in FIJI and run Macro_BaSiC_flatfieldonly.ijm.
       The macro saves a flatfield_merged_<channel>.tif next to the merged image.
    4. Press Enter in this script — it loads each flat-field and divides every
       z-plane of every tile by it, saving corrected stacks to
       output_shadingcorrection/<channel>/ inside each mouse folder.

WHY ONE Z-PLANE PER TILE FOR THE MERGE?
    BaSiC estimates a single 2D flat-field from the stack — a map of how
    illumination varies across the field of view. It only needs a representative
    sample of tiles to do this accurately (40-200 images is plenty). Loading all
    z-planes (8,120 frames for 14 mice x 20 tiles x 29 z-planes) would require
    ~65 GB of RAM. One middle z-plane per tile (280 frames, ~2 GB) is sufficient
    and avoids the crash entirely.

WHY FLAT-FIELD DIVISION RATHER THAN USING THE CORRECTED OUTPUT?
    The flat-field is a 2D image of the illumination pattern — a property of the
    optics, constant across all z-planes and all tiles. Dividing each raw z-plane
    by this flat-field directly applies the same correction formula BaSiC uses
    internally:

        corrected_plane = raw_plane / flat_field


FOLDER STRUCTURE:
    <experiment_dir>/
        <mouse_section>/
            raw_tiles_Zcut/
                <channel>/      ← input tiles (3D .tif stacks)
            output_shadingcorrection/
                <channel>/      ← corrected tiles written here
        merged_<channel>.tif            ← produced by this script (step 2)
        flatfield_merged_<channel>.tif  ← produced by FIJI/BaSiC (step 3)
"""

import gc
import os
import re

import numpy as np
import psutil
from pathlib import Path
from tifffile import imread, imwrite, TiffFile

# ══════════════════════════════════════════════════════════════════════════════
# USER CONFIGURATION — edit this section for each experiment
# ══════════════════════════════════════════════════════════════════════════════

EXPERIMENT_DIR = Path("/media/paulacauhy/Elements/1503_MEC_horizo_TBR1_RELN_CALB_T231")

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

INPUT_SUBFOLDER  = "raw_tiles_Zcut"
OUTPUT_SUBFOLDER = "output_shadingcorrection"

COMPRESSION = "zlib"

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING — no edits needed below this line
# ══════════════════════════════════════════════════════════════════════════════

def print_memory_usage():
    process = psutil.Process(os.getpid())
    memory_gb = process.memory_info().rss / 1024 ** 3
    print(f"  Memory in use: {memory_gb:.2f} GB")


def numerical_sort(file):
    """Sort tiles by the number in their filename."""
    numbers = re.findall(r"tile(\d+)", file.stem)
    if numbers:
        return int(numbers[0])
    numbers = re.findall(r"\d+", file.stem)
    return int(numbers[0]) if numbers else 0


def middle_plane(file_path):
    """Load only the middle z-plane of a 3D tif stack."""
    with TiffFile(file_path) as tif:
        n_planes = len(tif.pages)
        mid = n_planes // 2
        return tif.pages[mid].asarray()


def collect_tile_index(channel):
    """
    Scan all mouse sections for a given channel and return an ordered list of
    (input_file, output_dir) pairs. This index is shared by both the merge
    and deconstruct steps so the tile order is guaranteed to match.
    """
    index = []
    for mouse in MOUSE_SECTIONS:
        input_dir = EXPERIMENT_DIR / mouse / INPUT_SUBFOLDER / channel
        if not input_dir.exists():
            print(f"  WARNING — folder not found, skipping: {input_dir}")
            continue
        tif_files = sorted(input_dir.glob("*.tif"), key=numerical_sort)
        if not tif_files:
            print(f"  WARNING — no .tif files in: {input_dir}")
            continue
        out_dir = EXPERIMENT_DIR / mouse / OUTPUT_SUBFOLDER / channel
        for f in tif_files:
            index.append((f, out_dir))
    return index


# ── STEP 1: MERGE ─────────────────────────────────────────────────────────────

def merge_channel(channel):
    """
    Load the middle z-plane from each tile across all mouse sections and stack
    them into a single merged .tif for BaSiC to process.
    """
    print(f"\n{'='*60}")
    print(f"MERGING channel: {channel}")
    print(f"{'='*60}")

    index = collect_tile_index(channel)
    if not index:
        print(f"  ERROR — no tiles found for channel {channel}, skipping.")
        return False

    planes = []
    for i, (input_file, _) in enumerate(index):
        plane = middle_plane(input_file)
        planes.append(plane)
        print(f"  [{i+1}/{len(index)}] {input_file.parent.parent.name} / {input_file.name}")

    print(f"\n  Stacking {len(planes)} representative planes...")
    print_memory_usage()

    merged = np.stack(planes, axis=0)   # shape: (n_tiles, height, width)
    planes.clear()
    gc.collect()

    merged_path = EXPERIMENT_DIR / f"merged_{channel}.tif"
    print(f"  Saving → {merged_path}  shape={merged.shape}")
    imwrite(str(merged_path), merged, compression=COMPRESSION)

    del merged
    gc.collect()

    print(f"  Done. Open this file in FIJI and run Macro_BaSiC_flatfieldonly.ijm.")
    print(f"  FIJI will save: flatfield_merged_{channel}.tif  (in the same folder)")
    return True


# ── STEP 2: APPLY FLAT-FIELD TO ALL TILES ─────────────────────────────────────

def apply_flatfield_channel(channel):
    """
    Load the flat-field estimated by BaSiC and divide every z-plane of every
    tile by it. The flat-field is a 2D image (height x width) representing the
    illumination pattern, constant across z-planes and tiles.

    Correction formula:
        corrected_plane = raw_plane / flat_field

    Output is saved as float32 to preserve precision after division, then cast
    back to the original bit-depth of the raw tiles.
    """
    print(f"\n{'='*60}")
    print(f"APPLYING FLAT-FIELD — channel: {channel}")
    print(f"{'='*60}")

    flatfield_path = EXPERIMENT_DIR / f"flatfield_merged_{channel}.tif"
    if not flatfield_path.exists():
        print(f"  ERROR — flat-field not found: {flatfield_path}")
        print(f"  Make sure FIJI has finished running for this channel.")
        return

    flat_field = imread(str(flatfield_path)).astype(np.float32)
    if flat_field.ndim != 2:
        raise ValueError(
            f"Expected a 2D flat-field image, got shape {flat_field.shape}. "
            f"Check that the correct file was saved by the macro."
        )
    print(f"  Flat-field loaded: shape={flat_field.shape}, dtype={flat_field.dtype}")

    # Avoid division by zero — replace any zero pixels with 1.0 (no correction)
    flat_field = np.where(flat_field == 0, 1.0, flat_field)

    index = collect_tile_index(channel)
    if not index:
        print(f"  ERROR — no tiles found for channel {channel}.")
        return

    for i, (input_file, out_dir) in enumerate(index):
        mouse_name = input_file.parent.parent.name
        print(f"  [{i+1}/{len(index)}] {mouse_name} / {input_file.name}")

        raw_stack = imread(str(input_file))         # shape: (z, height, width)
        original_dtype = raw_stack.dtype

        # Divide each z-plane by the flat-field
        corrected_stack = (raw_stack.astype(np.float32) / flat_field)

        # Clip to valid range for the original bit-depth and restore dtype
        max_val = np.iinfo(original_dtype).max
        corrected_stack = np.clip(corrected_stack, 0, max_val).astype(original_dtype)

        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / input_file.name
        imwrite(str(out_file), corrected_stack, compression=COMPRESSION)

        del raw_stack, corrected_stack
        if i % 5 == 0:
            gc.collect()
            print_memory_usage()

    print(f"  Channel {channel} complete.")


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    print("=== BaSiC flat-field correction — stack / apply script ===")
    print(f"Experiment dir : {EXPERIMENT_DIR}")
    print(f"Mouse sections : {len(MOUSE_SECTIONS)}")
    print(f"Channels       : {CHANNELS}")
    print(f"Available RAM  : {psutil.virtual_memory().available / 1024**3:.1f} GB\n")

    # ── STEP 1: merge one plane per tile for each channel ─────────────────────
    print("STEP 1 — Building merged images for BaSiC.")
    print("After this, run Macro_BaSiC_flatfieldonly.ijm in FIJI for each channel.")
    print("Then press Enter to continue.\n")

    any_merged = False
    for channel in CHANNELS:
        ok = merge_channel(channel)
        if ok:
            any_merged = True

    if not any_merged:
        print("No channels could be merged. Check your folder structure.")
        return

    # ── PAUSE: wait for the user to run BaSiC in FIJI ─────────────────────────
    input("\nAll merged images saved. Run Macro_BaSiC_flatfieldonly.ijm in FIJI "
          "for each channel, then press Enter to apply the flat-fields... ")

    # ── STEP 2: apply flat-field to all z-planes of all tiles ─────────────────
    print("\nSTEP 2 — Applying flat-fields to all tiles.")

    for channel in CHANNELS:
        apply_flatfield_channel(channel)

    print("\n=== All channels complete ===")


if __name__ == "__main__":
    main()
