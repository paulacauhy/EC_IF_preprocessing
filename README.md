# Mouse Entorhinal Cortex IF Image Pre-processing
All scripts and macros necessary to reproduce image pre-processing steps linked to analysis of pTau vulnerability in mouse entorhinal cortex (EC) neuronal populations from multiplex IF imaging data.

## Extracting Raw Tiles

Python script saved as **'01_extract_tiles.py’** , which should be saved in the root experiment directory. This is necessary when working with images acquired in the UKDRI-UCL "Quadcam" Nikon microscope. Need to change input and output directories in the script. The script expects that the following primary-secondary antibody combinations were used: DAPI (405), Calbindin (488), Reelin (568), TBR1 (647), pT231 (750). 
**Tiles are saved separately per channel in folder 'raw_tiles’**. Each step of the pipeline will save output images into a new folder. 
### Expected folder structure:

  <experiment_dir>/
      <mouse_section>/
          raw_tiles/
              dapi/
              calbindin/
              reelin/
              tbr1/
              t231/

## Subset to Z planes of interest

For each mouse, manually select the Z planes that are in focus and that will be used for the Z projection for the analysis. The goal is to have a matching number of z planes across all sections to avoid final intensity differences being a byproduct of imaged tissue thickness. Use DAPI channel to select which planes to keep in order to remain unbiased. Run **'02_Macro_Zslice_keeper.ijm’** . 
In the macro, you’ll find the config section that looks like this:

config =
    “section_B, 3, 22 \n” +
    “section_C, 1, 20 \n”;
  
The numbers in the macro config mean, in order, first z plane to keep, and last z plane to keep. Now the two images will be reduced to a total of 20 z planes, matching the reference.

The notation is inclusive on both ends. first=3 last=22 keeps 20 slices — planes 3, 4, 5 … 22, with 22 itself included. The formula is: count = last − first + 1

## Flat-field correction
This step requires running a python script and a FIJI macro side-by-side. Start with **'03_stack_unstack_3d_tifs_perchannel.py**. 
WORKFLOW:
    1. Edit the USER CONFIGURATION section in the python script.
    2. Run this script — for each channel it stacks one representative z-plane
       per tile into a single merged .tif.
    3. Open each merged_<channel>.tif in FIJI and run **03_Macro_BaSiC_flatfieldonly.ijm**.
       The macro saves a flatfield_merged_<channel>.tif next to the merged image.
    4. Press Enter in the python script — it loads each flat-field generated with the FIJI macro and divides every
       z-plane of every tile by it, saving corrected stacks to
       output_shadingcorrection/<channel>/ inside each section folder.

## Z Projection + Background Subtraction
Macros **'04_Macro_ZMAX_projection.ijm’** and **'04_Macro_ZMEAN_projection.ijm’**. Z projections are saved in the folders 'z_max’ and 'z_mean’ for each section and channel.
Important: these macros also include a Background Subtraction step (TopHat Filter radius =30) after making the projection, so images saved have already been filtered. If you do not desire to run this, manually remove this section from the macros.

## Stitching

First, run Stitching in ImageJ for the dapi channel from zmax projection of each section

- Plugins → Stitching → Grid/Collection Stitching
    - Type: Grid: Snake by rows
    - Order: Right & Down
    - Then change for the number of tiles (e.g. 4x2), the overlap, the input directory, change first file index to 0; adjust file name to how they're named inside folder

Then, copy the generated “TileConfiguration.registered.txt” file into the z_max_projection folder of the other channels

Open the .txt file and change file name from dapi_tile0 to t231_tile0 … 

When running stitching for other channels, now change setting in ImageJ:

- Plugins → Stitching → Grid/Collection Stitching
    - Type: Positions from file
    - Select the "TileConfiguration.txt” saved inside the folder for the channel you want to stich
    - Uncheck boxes: compute overlap, subpixel accuracy

Copy these "TileConfiguration.txt" used for each channel in z_max folder to the z_mean folder and run stitching again for z_mean projection.

Files saved in folders **stitched_z_max** and **stitched_z_mean** folders

## Cellpose segmentation
First, create a folder within experiment root directory containing all stitched DAPI Z Max images from all sections. This will be input folder for this step.
In the conda environment **'cellpose_environment.yml'**, run python script **'06_cellpose_dapi_segmentation.py'**. This requires the trained model **'CP_DAPI_ISS'**. Before running the script, change path to model and input folder in the user configuration section.
The script will output mask uint16 .tif images in the same input folder.

## Expand nuclei masks
First, create a folder 'output_cellpose_masks' inside the folder of each section. In there, copy the section's resulting .tif from the cellpose segmentation step. 
In the conda environment **'image_preprocessing_environment.yml'**, run python script **'07_enlarge_masks.py'**. Before running, adjust user configuration in the script. The user configuration section includes the number of pixels used for expansion. The default is set to 10 pixels.

## Measure signal intensity for all channels inside DAPI masks
Measures morphological and intensity properties of segmented cells for all sections, using dapi dilated masks and stitched z_mean intensity images.
In the conda environment **'image_preprocessing_environment.yml'**, run python script **'08_regionprops_dapilabels_eachchannel.py'**.
Before running script, adjust user configuration section.
Saves a merged CSV across all samples with measurements of each channel per cell mask to:  <experiment_dir>/regionprops_all_samples.csv
