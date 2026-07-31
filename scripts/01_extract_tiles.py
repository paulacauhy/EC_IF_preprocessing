import os
import gc
import sys
import nd2
import numpy as np
import subprocess
import tifffile

# Define paths
input_dir = '/media/paulacauhy/Elements/20260312_quadcam_MEC_horizontal/'
output_dir = '/media/paulacauhy/Elements/1503_MEC_horizo_TBR1_RELN_CALB_T231/'

# Channel indices
channel_names = {
    'dapi': 0,
    'calbindin': 5,
    'reelin': 10,
    'tbr1': 15,
    't231': 19
}


def already_processed(raw_tiles_dir):
    """Return True if raw_tiles_dir already exists."""
    if not os.path.isdir(raw_tiles_dir):
        return False
    return True


def process_file(input_path, raw_tiles_dir):
    """Process a single ND2 file. Run in a subprocess so SIGBUS doesn't kill the main script."""
    with nd2.ND2File(input_path) as nd2_file:
        shape = nd2_file.shape
        print(f"Image shape: {shape}", flush=True)

        n_tiles, n_z, n_channels, n_y, n_x = shape

        max_channel = max(channel_names.values())
        if max_channel >= n_channels:
            print(f"WARNING: File only has {n_channels} channel(s); "
                  f"max requested index is {max_channel}. Skipping.", flush=True)
            return

        image = nd2_file.to_dask()
        vs = nd2_file.voxel_size()
        print(f"Voxel size (µm): x={vs.x}, y={vs.y}, z={vs.z}", flush=True)

        for tile_index in range(n_tiles):
            for channel_name, channel_index in channel_names.items():

                z_slices = []
                for z_index in range(n_z):
                    try:
                        frame = image[tile_index, z_index, channel_index, :, :].compute()
                        z_slices.append(frame)
                    except Exception as e:
                        print(f"WARNING: Could not read tile={tile_index} z={z_index} "
                              f"channel={channel_name}: {e}. Substituting blank frame.", flush=True)
                        z_slices.append(np.zeros((n_y, n_x), dtype='uint16'))

                tile_np = np.stack(z_slices, axis=0).astype('uint16')
                del z_slices
                gc.collect()

                channel_dir = os.path.join(raw_tiles_dir, channel_name)
                os.makedirs(channel_dir, exist_ok=True)
                output_path = os.path.join(channel_dir, f"tile{tile_index}.tif")

                tifffile.imwrite(
                    output_path,
                    tile_np,
                    imagej=True,
                    resolution=(1 / vs.x, 1 / vs.y),
                    metadata={'axes': 'ZYX', 'spacing': vs.z, 'unit': 'um'},
                )
                print(f"Saved {output_path}", flush=True)

                del tile_np
                gc.collect()


# ── Entry point when called as a subprocess ───────────────────────────────────
if __name__ == '__main__' and len(sys.argv) == 3:
    _input_path, _raw_tiles_dir = sys.argv[1], sys.argv[2]
    os.makedirs(_raw_tiles_dir, exist_ok=True)
    process_file(_input_path, _raw_tiles_dir)
    sys.exit(0)


# ── Main loop ─────────────────────────────────────────────────────────────────
if __name__ == '__main__' and len(sys.argv) == 1:
    nd2_files = sorted(f for f in os.listdir(input_dir) if f.endswith('.nd2'))
    print(f"Found {len(nd2_files)} ND2 file(s): {nd2_files}")

    file_sizes = {f: os.path.getsize(os.path.join(input_dir, f)) for f in nd2_files}
    median_size = sorted(file_sizes.values())[len(file_sizes) // 2]
    for f, size in file_sizes.items():
        if size < median_size * 0.5:
            print(f"WARNING: {f} is {size / 1e9:.2f} GB vs median "
                  f"{median_size / 1e9:.2f} GB — may be truncated/corrupt")

    for nd2_filename in nd2_files:
        input_path = os.path.join(input_dir, nd2_filename)
        file_stem = os.path.splitext(nd2_filename)[0]
        raw_tiles_dir = os.path.join(output_dir, file_stem, 'raw_tiles')

        print(f"\n{'='*60}")
        print(f"Processing: {nd2_filename}  ({file_sizes[nd2_filename]/1e9:.2f} GB)")


        if already_processed(raw_tiles_dir):
            print(f"↷ Skipping: {raw_tiles_dir} already exists.")
            continue

        print(f"Output: {raw_tiles_dir}")

        result = subprocess.run(
            [sys.executable, __file__, input_path, raw_tiles_dir],
            text=True
        )

        if result.returncode == 0:
            print(f"✓ Finished: {nd2_filename}")
        elif result.returncode == -7:
            print(f"✗ SIGBUS on {nd2_filename} even with memory_map=False — "
                  f"file is severely corrupt and unreadable. Skipping.")
        else:
            print(f"✗ Failed: {nd2_filename} (exit code {result.returncode}). Skipping.")
