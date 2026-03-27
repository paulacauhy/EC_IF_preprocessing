// Macro_ZMEAN_projection.ijm
//
// Creates a Z Mean Intensity projection for every channel of every mouse
// section, then applies a Top Hat filter for background subtraction.
//
// Expected folder structure:
//   <experiment_dir>/
//       <mouse_section>/
//           output_shadingcorrection/
//               dapi/
//               calbindin/
//               reelin/
//               tbr1/
//               t231/
//
// Output is written to:
//   <experiment_dir>/
//       <mouse_section>/
//           z_mean/
//               dapi/
//               calbindin/
//               reelin/
//               tbr1/
//               t231/

// ══════════════════════════════════════════════════════════════════════════════
// USER CONFIGURATION — edit this section for each experiment
// List every mouse section folder, one per line.
// Folder names must exactly match the folders inside your experiment directory.
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

channels = newArray("dapi", "calbindin", "reelin", "tbr1", "t231");

// ══════════════════════════════════════════════════════════════════════════════
// PROCESSING — no edits needed below this line
// ══════════════════════════════════════════════════════════════════════════════

run("Close All");
run("Clear Results");

experimentDir = getDirectory("Select the experiment root folder");

print("=== Z MEAN projection — batch run ===");
print("Experiment dir: " + experimentDir);
print("-------------------------------------");

for (m = 0; m < mouseSections.length; m++) {

    mouseSection = mouseSections[m];
    print("\n[" + mouseSection + "]");

    for (c = 0; c < channels.length; c++) {

        channel = channels[c];

        inputPath  = experimentDir + mouseSection + File.separator
                   + "output_shadingcorrection" + File.separator + channel + File.separator;
        outputPath = experimentDir + mouseSection + File.separator
                   + "z_mean" + File.separator + channel + File.separator;

        if (!File.exists(inputPath)) {
            print("  [" + channel + "] WARNING — folder not found, skipping.");
            continue;
        }

        // Create output folders if they don't exist yet
        File.makeDirectory(experimentDir + mouseSection + File.separator + "z_mean");
        File.makeDirectory(outputPath);

        fileList = getFileList(inputPath);
        nFound   = 0;

        for (i = 0; i < fileList.length; i++) {
            filename = fileList[i];

            if (endsWith(filename, ".tif") || endsWith(filename, ".tiff")) {
                open(inputPath + filename);
                stackTitle = getTitle();

                // Z MEAN projection — creates a new image window
                run("Z Project...", "projection=[Average Intensity]");

                // Background subtraction
                run("Top Hat...", "radius=30");

                // Save the projected image
                saveAs("Tiff", outputPath + filename);

                // Close the projection, then the original stack
                close();
                selectWindow(stackTitle);
                close();

                nFound++;
            }
        }

        print("  [" + channel + "] " + nFound + " file(s) processed.");
    }
}

print("\n=== Processing complete ===");
