// Macro_BaSiC_flatfieldonly.ijm
//
// Opens a merged 3D .tif (one representative z-plane per tile, produced by
// stack_unstack_3d_tifs_perchannel.py), runs the BaSiC plugin to estimate
// the illumination flat-field, and saves the flat-field as a 2D .tif.
//
// The flat-field is a single 2D image describing how illumination varies
// across the field of view. It is a property of the optics, not the sample,
// so one flat-field per channel is sufficient to correct every z-plane of
// every tile. The Python script (stack_unstack_3d_tifs_perchannel.py) reads
// this flat-field and applies it to all tiles.
//
// Run this macro once per channel. It will save:
//   flatfield_merged_<channel>.tif   (next to the input merged file)

// ── SELECT INPUT ──────────────────────────────────────────────────────────────

path = File.openDialog("Select the merged .tif image");
if (path == "") exit("No file selected");

dir  = File.getParent(path);
name = File.getName(path);

if (!File.exists(path)) exit("Selected file does not exist: " + path);

// ── OPEN AND RUN BaSiC ────────────────────────────────────────────────────────

open(path);
if (nImages == 0) exit("Failed to open image: " + path);

selectImage(name);

run("BaSiC ",
    "processing_stack=" + name +
    " flat-field=None dark-field=None shading_estimation=[Estimate shading profiles]" +
    " shading_model=[Estimate flat-field only (ignore dark-field)]" +
    " setting_regularisationparametes=Automatic temporal_drift=Ignore" +
    " correction_options=[Compute shading only] lambda_flat=0.50 lambda_dark=0.50");

// ── SAVE THE FLAT-FIELD ───────────────────────────────────────────────────────
// BaSiC opens the estimated flat-field in a window called "Flat-field:<imagename>".
// This is the 2D illumination map the Python script needs.

flatfield_name = "Flat-field:" + name;
if (!isOpen(flatfield_name)) {
    exit("Flat-field image not found — check BaSiC ran correctly");
}

selectImage(flatfield_name);
save_path = dir + File.separator + "flatfield_" + name;
saveAs("Tiff", save_path);

if (File.exists(save_path)) {
    print("Flat-field saved to: " + save_path);
} else {
    print("WARNING: flat-field file could not be saved.");
}

run("Close All");
