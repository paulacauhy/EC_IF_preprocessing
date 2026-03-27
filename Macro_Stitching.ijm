// Macro_Stitching.ijm
//
// Stitches all channels for both z_max and z_mean projections, using the
// dapi tile configuration computed for z_max to align all other channels
// and both projection types.
//
// STEP 1 — z_max, dapi:
//   Runs Grid/Collection Stitching with overlap calculation to determine tile
//   positions. FIJI writes TileConfiguration.registered.txt into the dapi
//   z_max folder.
//
// STEP 2 — z_max, all other channels:
//   Copies the registered configuration from z_max/dapi into each other
//   channel's z_max folder (substituting the channel name), then stitches
//   using those pre-computed positions.
//
// STEP 3 — z_mean, all channels:
//   Copies the registered configuration from z_max/<channel> into the
//   corresponding z_mean/<channel> folder for every channel (substituting
//   the projection folder name), then stitches using those same positions.
//   No overlap calculation is needed — tile positions are identical for
//   both projections as they are determined by the microscope stage.
//
// Expected input structure:
//   <experiment_dir>/
//       <mouse_section>/
//           z_max/
//               dapi/    calbindin/    reelin/    tbr1/    t231/
//           z_mean/
//               dapi/    calbindin/    reelin/    tbr1/    t231/
//
// Output:
//   <experiment_dir>/
//       <mouse_section>/
//           stitched_zmax/
//               <mouseID>_stitched_dapi_zmax.tif
//               <mouseID>_stitched_calbindin_zmax.tif  ...
//           stitched_zmean/
//               <mouseID>_stitched_dapi_zmean.tif
//               <mouseID>_stitched_calbindin_zmean.tif ...

// ══════════════════════════════════════════════════════════════════════════════
// USER CONFIGURATION — edit this section for each experiment
// ══════════════════════════════════════════════════════════════════════════════

mouseSections = newArray(
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
    "s305n11384_slide1_IF"
);

// All channels — dapi must remain first as it is used to compute positions
channels = newArray("dapi", "calbindin", "reelin", "tbr1", "t231");

// Grid parameters
gridCols    = 5;
gridRows    = 4;
tileOverlap = 10;   // percent

// ══════════════════════════════════════════════════════════════════════════════
// PROCESSING — no edits needed below this line
// ══════════════════════════════════════════════════════════════════════════════

run("Close All");
run("Clear Results");

experimentDir = getDirectory("Select the experiment root folder");

print("=== Stitching — batch run ===");
print("Experiment dir: " + experimentDir);
print("-----------------------------");

for (m = 0; m < mouseSections.length; m++) {

    mouseSection = mouseSections[m];
    print("\n[" + mouseSection + "]");

    // Create output folders for both projections
    zmaxStitchedDir  = experimentDir + mouseSection + File.separator + "stitched_zmax"  + File.separator;
    zmeanStitchedDir = experimentDir + mouseSection + File.separator + "stitched_zmean" + File.separator;
    File.makeDirectory(experimentDir + mouseSection + File.separator + "stitched_zmax");
    File.makeDirectory(experimentDir + mouseSection + File.separator + "stitched_zmean");

    dapiZmaxPath = experimentDir + mouseSection + File.separator
                 + "z_max" + File.separator + "dapi" + File.separator;

    if (!File.exists(dapiZmaxPath)) {
        print("  WARNING — z_max/dapi folder not found, skipping this mouse.");
        continue;
    }

    // ── STEP 1: stitch z_max dapi with overlap calculation ───────────────────

    print("  [z_max / dapi] computing tile positions...");

    run("Grid/Collection stitching",
        "type=[Grid: snake by rows]" +
        " order=[Right & Down                ]" +
        " grid_size_x=" + gridCols +
        " grid_size_y=" + gridRows +
        " tile_overlap=" + tileOverlap +
        " first_file_index_i=0" +
        " directory=" + dapiZmaxPath +
        " file_names=dapi_tile{i}.tif" +
        " output_textfile_name=TileConfiguration.txt" +
        " fusion_method=[Linear Blending]" +
        " regression_threshold=0.30" +
        " max/avg_displacement_threshold=2.50" +
        " absolute_displacement_threshold=3.50" +
        " compute_overlap" +
        " computation_parameters=[Save memory (but be slower)]" +
        " image_output=[Fuse and display]");

    saveAs("Tiff", zmaxStitchedDir + mouseSection + "_stitched_dapi_zmax.tif");
    close();
    print("  [z_max / dapi] saved.");

    // Read the registered config that FIJI just wrote into the dapi z_max folder
    dapiRegisteredFile = dapiZmaxPath + "TileConfiguration.registered.txt";
    if (!File.exists(dapiRegisteredFile)) {
        print("  ERROR — TileConfiguration.registered.txt not found in "
            + dapiZmaxPath + ". Skipping this mouse.");
        continue;
    }
    dapiRegisteredContent = File.openAsString(dapiRegisteredFile);

    // ── STEP 2: stitch all other channels for z_max ───────────────────────────
    // Copy dapi registered config into each channel folder (substituting the
    // channel name), then stitch using those pre-computed positions.

    for (c = 1; c < channels.length; c++) {    // start at 1 to skip dapi

        channel = channels[c];
        channelZmaxPath = experimentDir + mouseSection + File.separator
                        + "z_max" + File.separator + channel + File.separator;

        if (!File.exists(channelZmaxPath)) {
            print("  WARNING — z_max/" + channel + " folder not found, skipping.");
            continue;
        }

        // Substitute channel name in the registered config and write it
        channelContent = replace(dapiRegisteredContent, "dapi", channel);
        File.saveString(channelContent, channelZmaxPath + "TileConfiguration.txt");

        print("  [z_max / " + channel + "] stitching with dapi positions...");

        run("Grid/Collection stitching",
            "type=[Positions from file]" +
            " order=[Defined by TileConfiguration]" +
            " directory=" + channelZmaxPath +
            " layout_file=TileConfiguration.txt" +
            " fusion_method=[Linear Blending]" +
            " regression_threshold=0.30" +
            " max/avg_displacement_threshold=2.50" +
            " absolute_displacement_threshold=3.50" +
            " computation_parameters=[Save memory (but be slower)]" +
            " image_output=[Fuse and display]");

        saveAs("Tiff", zmaxStitchedDir + mouseSection + "_stitched_" + channel + "_zmax.tif");
        close();
        print("  [z_max / " + channel + "] saved.");
    }

    // ── STEP 3: stitch all channels for z_mean ────────────────────────────────
    // Derive every channel's z_mean tile configuration directly from
    // dapiRegisteredContent (already in memory from Step 1) by substituting
    // the channel name and z_max → z_mean in one step. This avoids relying on
    // per-channel registered files from Step 2, which FIJI does not write when
    // running without compute_overlap.

    for (c = 0; c < channels.length; c++) {

        channel = channels[c];

        channelZmeanPath = experimentDir + mouseSection + File.separator
                         + "z_mean" + File.separator + channel + File.separator;

        if (!File.exists(channelZmeanPath)) {
            print("  WARNING — z_mean/" + channel + " folder not found, skipping.");
            continue;
        }

        // Start from the dapi registered content, substitute the channel name
        // (no-op for dapi itself), then substitute the projection folder name
        zmeanContent = replace(dapiRegisteredContent, "dapi", channel);
        zmeanContent = replace(zmeanContent, "z_max", "z_mean");
        File.saveString(zmeanContent, channelZmeanPath + "TileConfiguration.txt");

        print("  [z_mean / " + channel + "] stitching with z_max positions...");

        run("Grid/Collection stitching",
            "type=[Positions from file]" +
            " order=[Defined by TileConfiguration]" +
            " directory=" + channelZmeanPath +
            " layout_file=TileConfiguration.txt" +
            " fusion_method=[Linear Blending]" +
            " regression_threshold=0.30" +
            " max/avg_displacement_threshold=2.50" +
            " absolute_displacement_threshold=3.50" +
            " computation_parameters=[Save memory (but be slower)]" +
            " image_output=[Fuse and display]");

        saveAs("Tiff", zmeanStitchedDir + mouseSection + "_stitched_" + channel + "_zmean.tif");
        close();
        print("  [z_mean / " + channel + "] saved.");
    }
}

print("\n=== Stitching complete ===");
