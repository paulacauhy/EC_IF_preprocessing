// Macro_Zslice_keeper.ijm
//
// Keeps a defined range of z-slices for every channel of every mouse section.
// All configuration is at the top of this file — no external files needed.
//
// Expected folder structure:
//   <experiment_dir>/
//       <mouse_section>/
//           raw_tiles/
//               dapi/
//               calbindin/
//               reelin/
//               tbr1/
//               t231/
//
// Output is written to:
//   <experiment_dir>/
//       <mouse_section>/
//           raw_tiles_Zcut/
//               dapi/
//               calbindin/
//               reelin/
//               tbr1/
//               t231/

// ══════════════════════════════════════════════════════════════════════════════
// USER CONFIGURATION — edit this section for each experiment
// Format one line per mouse section: "folder_name, first_slice, last_slice"
// Folder names must exactly match the folders inside your experiment directory.
// ══════════════════════════════════════════════════════════════════════════════

config =
    "2aryonly_slide2_IF, 1, 29 \n" +
    "htauki00660_slide1_IF, 2, 30 \n" +
    "htauki00661_slide1_IF, 1, 29 \n" +
    "htauki01513_slide1_IF, 1, 29 \n" +
    "htauki01514_slide2_IF, 1, 29 \n" +
    "htauki01514_slide4_IF, 2, 30 \n" +
    "M12_slide1_IF, 1, 29 \n" +
    "M16_slide2_IF, 4, 32 \n" +
    "M16_slide4_IF, 9, 37 \n" +
    "s305n01144_slide3_IF, 5, 33 \n" +
    "s305n01145_slide1_IF, 3, 31 \n" +
    "s305n01145_slide3_IF, 1, 29 \n" +
    "s305n11383_slide4_IF, 2, 30 \n" +
    "s305n11384_slide1_IF, 1, 29 \n";

channels = newArray("dapi", "calbindin", "reelin", "tbr1", "t231");

// ══════════════════════════════════════════════════════════════════════════════
// PROCESSING — no edits needed below this line
// ══════════════════════════════════════════════════════════════════════════════

run("Close All");
run("Clear Results");

experimentDir = getDirectory("Select the experiment root folder");

print("=== Z-slice keeper — batch run ===");
print("Experiment dir: " + experimentDir);
print("----------------------------------");

// Parse the config string into lines
lines = split(config, "\n");

for (row = 0; row < lines.length; row++) {

    line = trim(lines[row]);
    if (line == "") continue;

    columns      = split(line, ",");
    mouseSection = trim(columns[0]);
    firstSlice   = parseInt(trim(columns[1]));
    lastSlice    = parseInt(trim(columns[2]));

    print("\n[" + mouseSection + "]  keeping slices " + firstSlice + " to " + lastSlice);

    for (c = 0; c < channels.length; c++) {

        channel = channels[c];

        inputPath  = experimentDir + mouseSection + File.separator
                   + "raw_tiles"     + File.separator + channel + File.separator;
        outputPath = experimentDir + mouseSection + File.separator
                   + "raw_tiles_Zcut" + File.separator + channel + File.separator;

        if (!File.exists(inputPath)) {
            print("  [" + channel + "] WARNING — folder not found, skipping.");
            continue;
        }

        // Create output folders if they don't exist yet
        File.makeDirectory(experimentDir + mouseSection + File.separator + "raw_tiles_Zcut");
        File.makeDirectory(outputPath);

        fileList = getFileList(inputPath);
        nFound   = 0;

        for (i = 0; i < fileList.length; i++) {
            filename = fileList[i];

            if (endsWith(filename, ".tif") || endsWith(filename, ".tiff")) {
                open(inputPath + filename);
                stackTitle = getTitle();

                // Slice Keeper creates a new image, leaving two windows open
                run("Slice Keeper", "first=" + firstSlice
                                  + " last="  + lastSlice
                                  + " increment=1");

                // Save the cropped result, then close both windows
                saveAs("Tiff", outputPath + filename);
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
