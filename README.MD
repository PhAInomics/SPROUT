# SPROUT
_A semi-automated, threshold-based segmentation toolkit for 2D/3D grayscale images_

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Usage](#usage)
  - [Input Data Format](#input-data-format)
  - [Seed Generation](#seed-generation)
  - [Merged Seed Generation](#merged-seed-generation)
  - [Seed Growth](#seed-growth)
  - [Batch Processing Pipelines](#batch-processing-pipelines)
- [View & Edit (napari)](#view--edit-napari)
- [Demo Results](#demo-results)
- [Extras](#extra-features)

## Introduction

**SPROUT: Semi-automated Parcellation of Region Outputs Using Thresholding and Transformation**  
SPROUT is a tool for parcellating segments from **3D scans** (e.g., micro-CT, MRI, and other imaging data) using semi-automated seed generation and growth. It can be applied to a diverse range of datasets, from **skulls and entire skeletons** (e.g., isolating individual bones) to **organs and man-made structures** (e.g., concrete blocks). 

New in February 2025: SPROUT now supports 2D greyscale images.

Example applications and method details are provided in:  
**Y. He, M. Camaiti, L.E. Roberts, J.M. Mulqueeney, M. Didziokas, A. Goswami. 2024.**  
[*Introducing SPROUT (Semi-automated Parcellation of Region Outputs Using Thresholding and Transformation): an adaptable computer vision tool to generate 3D and 2D segmentations.*](https://www.biorxiv.org/content/10.1101/2024.11.22.624847v1.abstract)  


## Prerequisites

1. **Python and Environment Setup**
   - **Install Python**: If Python is not already installed, we recommend downloading the [Anaconda distribution](https://www.anaconda.com/products/distribution). After providing your email, follow the download link and select the version suitable for your operating system.
   - **Set up Python Environment**:
     - For Windows users with Anaconda, open the **Anaconda Prompt** from the Start menu.
     - For other installations, open a terminal with Python access.

2. **Create and Configure Python Environment**
   - SPROUT supports **Python 3.10**. Required libraries and versions are:
     ```
     NumPy: 1.26.4
     Pandas: 2.2.1
     Scikit-image: 0.22.0
     Tifffile: 2024.2.12
     Pyyaml: 6.0.1
     Trimesh: 4.3.1
     Matplotlib: 3.8.3
     open3d: 0.18.0
     ```
   - Steps to create the environment:
     1. **Create the environment**:
        ```bash
        conda create -n sprout python=3.10
        ```
     2. **Activate the environment**:
        ```bash
        conda activate sprout
        ```
     3. **Install dependencies**:
        ```bash
        pip install numpy==1.26.4 pandas==2.2.1 scikit-image==0.22.0 tifffile==2024.2.12 pyyaml==6.0.1 trimesh==4.3.1 matplotlib==3.8.3 open3d==0.18.0
        ```

### 🧪 Recommended Visualization Tools

**💡 Strongly recommended: [napari](https://napari.org/)**  
SPROUT comes with a napari plugin for interactive 2D/3D visualization and editing of seeds, segmentation results, and more.

To install napari and the SPROUT plugin:

```bash
pip install napari
cd ./napari_sprout
pip install -e .
```
You can launch napari by running napari in the command line.
The SPROUT plugin will appear under the Plugins menu in the napari UI.

----------

### Other Optional Tools

You can use other tools, for detail please see: [Extras](#extra-features)



## Usage

SPROUT follows a **three-step workflow** for multi-class segmentation:  

1. **Seed Generation**  
   Identify and segment individual components within a **2D or 3D image** by mainly tuning **thresholding and erosion**. This step generates candidate seeds for further processing. Alternatively, a function called merged seeds generation can be used to generate better seeds.

2. **Candidate Seed Selection**  
   Review and choose the candidate seed for growth. This ensures that the segmentation process focuses on the desired regions.  

3. **Growth**  
   Expand the candidate seed to match the target regions, ensuring accurate segmentation of structures within the image.  



![workflow](./material/flowchart.png)

A detailed tutorial with step-by-step instructions and screenshots is available in the [`./material/`](./material/) directory.


### **Input Data Format**
SPROUT processes 2D and 3D grayscale images stored in **TIFF (`.tif`, `.tiff`) format**. 

- **Supported file types:** `.tif`, `.tiff`
- **Image Type:** 2D or 3D grayscale images
- **Bit Depth:** 8-bit, 16-bit, or 32-bit (floating point)
- **File Structure:**  
   - 2D images: `(Height, Width)`
   - 3D images: `(Depth, Height, Width)`

**Unsupported inputs:** Color images.

Two low-resolution scans are available in `./data`, including a **dog skeleton** `demo_dog.tiff` and a **foraminifera chamber segmentation** `demo_foram_segmentation.tif`.  
Additional demo data for the tutorial can be found [here](https://zenodo.org/records/14358829).

### Seed Generation
Use thresholds, morphological transformations and connected components to separate specimen into target regions

#### **`make_seeds.py`**  
`make_seeds.py` is the for generating seeds. 
   - **Usage**: 
      - Run with the default configuration:  
         ```bash
         python make_seeds.py
         ```
         *(Reads the `./make_seeds.yaml` file)*  
      - Run with a custom configuration:  
         ```bash
         python make_seeds.py <config>.yaml
         ```
      - Run with the template configuration:  
         ```bash
         python make_seeds.py ./template/make_seeds.yaml
         ```
      An example YAML configuration file can be found at `./template/make_seeds.yaml`, where it generate seeds on the `demo_foram_segmentation.tif`


   - **Key Parameters**:  
      I/O Parameters:
      - `file_name`: Path to the input image.  
      - `output_folder`: Folder to save the generated seeds.    

      Seed Generation Settings:
      - `thresholds`: Thresholds for creating binary masks in seed generation process. `mask = input >= threshold`. 
      - `ero_iters`: Number of erosion iterations.  
      - `segments`: Number of largest disconnected components to retain (≥1).  
      - `num_threads`: Number of threads for parallel processing (recommended to match `target_thresholds`).  
      - `footprints`: Shape of the erosion footprint:
         - `'ball'` and `'cube'`: Erosion in all directions.  
         - `'ball_XY'`, `'ball_XZ'`, `'ball_YZ'`: Erosion in specific planes.  
         - `'X'`, `'Y'`, `'Z'`: Erosion along specific axes.  

      Optional Settings:
      - `boundary_path`: Path to boundary mask, which helps to define non-target region explicitly. Defaults is None.
      - `upper_thresholds`: A list of upper thresholds used to create binary masks. Default is None, if provided, the mask is defined as `mask = (input >= threshold) & (input <= upper_threshold)`. 
      - `workspace`: Base folder for all input and output files. Default is ""

   - **Outputs**:  
   Seeds will be saved in the `output_folder` for each combination of erosion and threshold (or threshold pairs if an upper threshold is provided), following the naming convention:  
   **`seed_ero_{ero_iter}_thre{threshold}_{upper_threshold}_seg_{segments}.tif`**. Additionally, a running log file named `output_log_file` will be saved.  

#### **`make_seeds_all.py`**  
Similar to `make_seeds.py` in usage and configuration, but does not require specifying `footprints`. It automatically generates seeds using predefined footprints: `'ball'`, `'ball_XY'`, `'ball_XZ'`, and `'ball_YZ'`. 

   - **Usage**: 
      - Run with the default configuration:  
         ```bash
         python make_seeds_all.py
         ```
         *(Reads the `./make_seeds_all.yaml` file)*  
      - Run with a custom configuration:  
         ```bash
         python make_seeds_all.py <config>.yaml
         ```
      - Run with the template configuration:  
         ```bash
         python make_seeds_all.py ./template/make_seeds_all.yaml
         ```
      An example YAML configuration file can be found at `./template/make_seeds_all.yaml`, where it generate seeds on the `demo_dog.tiff` for different footprints

   - **Outputs**:  
   Generated seeds will be saved in subfolders within the `output_folder`, corresponding to each erosion footprint: `seeds_ball`, `seeds_XY`, `seeds_YZ`, `seeds_XZ`. Within each subfolder, the naming convention follows a structure similar to `make_seeds.py`. Additionally, an overall logging plot named `full_log.png` will be saved.

### Merged Seed Generation
`make_seeds_merged.py` is an algorithm designed for generating seeds through an automated merging process. This algorithm can:
   1. Detect separations within a segmented region.
   2. Retain regions that might be disappear when increasing threshold value or erosion.
   - **Usage**: An example YAML configuration file can be found at `./template/make_seeds_merged.yaml`.
      - Run with the default configuration:  
         ```bash
         python make_seeds_merged.py
         ```
         *(Reads the `./make_seeds_merged.yaml` file)*  
      - Run with a custom configuration:  
         ```bash
         python make_seeds_merged.py <config>.yaml
         ```
      - Run with the template configuration:  
         ```bash
         python make_seeds_merged.py ./template/make_seeds_merged.yaml
         ```
      An example YAML configuration file is available at `./template/make_seeds_merged.yaml`, which demonstrates seed generation on `demo_dog.tiff` using a list of 10 increasing thresholds with zero erosions.

   - **Outputs**  
   Generated seeds will be saved in the `output_folder`. The final output will be saved as `{name_prefix}_ero_{n_iters}_sorted.tif`, while intermediate results may also be saved depending on the settings of `save_every_iter` and `save_merged_every_iter`. The naming convention for intermediate results follows a structure similar to `make_seeds.py`. Additionally, a log file documenting the separations and components is saved as `output_dict.csv`.

#### Types of Merged Seed Generation:
The type of process depends on the input parameters:

1. **Threshold-Based Process**:  
   If a list of thresholds is provided, the merged seeds will be generated across seeds from different thresholds and the same erosion settings.

2. **Erosion-Based Process**:  
   If a single threshold or a list containing just one threshold is provided, the merged seeds will be generated across seeds from no erosion to the target erosion while keeping the same threshold.



### Seed Growth

**`make_grow_result.py`**, grows seeds back to the original images using thresholds.

   - **Usage**: An example YAML configuration file can be found at `./template/make_grow_result.yaml`.
      - Run with the default configuration:  
         ```bash
         python make_grow_result.py
         ```
         *(Reads the `./make_grow_result.yaml` file)*  
      - Run with a custom configuration:  
         ```bash
         python make_grow_result.py <config>.yaml
         ```
      - Run with the template configuration:  
         ```bash
         python make_grow_result.py ./template/make_grow_result.yaml
         ```
      An example YAML configuration file is available at `./template/make_grow_result.yaml`, which grows on the merged seed of `demo_dog.tiff` from the example input in `make_seeds_merged.py`.

   - **Key Parameters**:  
      I/O Parameters:
      - `img_path`: Path to the input image.  
      - `seg_path`: Path to the seed file.  
      

      Growth Settings:
      - `thresholds`: A list of thresholds used to create binary masks for the growth process, where `mask = input >= threshold`. Growth begins at higher thresholds to ensure better control and avoid overgrowth. 
      - `dilate_iters`: List of integers specifying dilation iterations for each threshold.  
      - `touch_rule`: (Default: `"stop"`) Rule for handling overlaps during growth.  
      - `save_interval`: Interval for saving intermediate results. 
      - `num_threads`: Number of threads

      Optional Settings:
      - `workspace`: Base folder for all input and output files. Default is ""
      - `boundary_path`: Path to boundary mask, which helps to define non-target region explicitly. Defaults is None.
      - `upper_thresholds`: A list of upper thresholds used to create binary masks for the growth process. Default is None, if provided, the mask is defined as `mask = (input >= threshold) & (input <= upper_threshold)`. 
      - `to_grow_ids`: Specify segmentation classes to grow, default is growing on all ids
      - `grow_to_end`: Whether grow the seed match the thresholded binary mask as close as possible. It will override the dilate_iters. Default False.
      - `tolerate_iters` Early stopping: limit for consecutive no-growth iterations. Defaults is 3.
      - `min_diff`: The minimum difference to consider a growth in a dilation iteration. Default is 50

   - **Outputs**  
   Grown results will be saved in the `output_folder`. The final output will be saved as `final_grow_{input_image_name}.tif`, while intermediate results may also be saved depending on the settings of `save_interval`.

   - **Features**:  
      - Allows expanding segmentation regions gradually from high to low thresholds, reducing the risk of overgrowth and ensuring more precise boundaries.
      - Supports early stopping if the size increase is below a minimum threshold (default: 50 voxels) for a set number of iterations (default: 3 consecutive iterations).


### Batch Processing Pipelines

#### **`PipelineSeed.py`**  
   This script is used for batch seed generation, including the creation of seeds and merged seeds. 

   - **Usage**: An example YAML configuration file can be found at `./template/PipelineSeed.yaml`.
      - Run with the default configuration:  
         ```bash
         python PipelineSeed.py
         ```
         *(Reads the `./PipelineSeed.yaml` file)*  
      - Run with a custom configuration:  
         ```bash
         python PipelineSeed.py <config>.yaml
         ```
      - Run with a custom configuration:  
         ```bash
         python PipelineSeed.py ./template/PipelineSeed.yaml
         ```
      An example YAML configuration file is available at `./template/PipelineSeed.yaml`, which uses an example csv file `./template/seeds_input.csv`. The example generates merged seeds for both `demo_dog.tiff` and `demo_foram_segmentation` with different thresholds and erosions.

   - **Input CSV**:  
     The batch processing CSV file can be found at `./template/seeds_input.csv`. The `img_path` column is mandatory, specifying the path to the input images. Other parameters, such as `seed_threshold`, `boundary_path` and `ero_iters`, are optional and can be set on a per-input basis in the CSV or set globally for all inputs in the YAML file.

   This pipeline offers flexibility and scalability for large-scale seed generation tasks.

#### **`PipelineGrow.py`**  
   This script is designed for batch processing of growth on seeds.

   - **Usage**: An example YAML configuration file can be found at `./template/PipelineGrow.yaml`.
      - Run with the default configuration:  
         ```bash
         python PipelineGrow.py
         ```
         *(Reads the `./PipelineGrow.yaml` file)*  
      - Run with a custom configuration:  
         ```bash
         python PipelineGrow.py <config>.yaml
         ```
      - Run with a custom configuration:  
         ```bash
         python PipelineGrow.py ./template/PipelineGrow.yaml
         ```
      An example YAML configuration file is available at `./template/PipelineGrow.yaml`, which uses an example csv file `./template/grow_input.csv`. The example grows on the merged seeds generated from the `PipelineSeed.py` example.

   - **Input CSV**:  
   The batch processing CSV file is located at `./template/grow_input.csv`. The `img_path` and `seg_path` columns are mandatory, specifying the path to the input images and candidate seeds. Other parameters, such as `thresholds`, `boundary_path` and `dilate_iters`, are optional and can be set on a per-file basis in the CSV or set globally for all inputs in the YAML file..

## View & Edit (napari)

TODO


You can also visualize, inspect, and edit seeds or results using 3D image processing tools such as **3D Slicer**, **DragonFly**, and **AVIZO**. Alternatively, you can generate meshes and view or edit them in mesh-based tools like **MeshLab**. See Extra section


## Demo Results

SPROUT has been successfully applied to a variety of datasets, including:
- **Micro-CT full skeleton**
- **Micro-CT skull**
- **MRI heart**
- **Micro-CT concrete**
- **Binary segmentation of Forams**

The image below illustrates the outcomes from left to right:
1. **Volumetric Representations**: Visualizations of the original image stacks.
2. **Merged Seeds**: Results after applying SPROUT's segmentation and merging processes.
3. **Grow Results**: Results after growing on the candidate seeds

![Result1](./material/result_1.png)



----------
## Extra Features

   - [Visualize by Meshes](#visualize-by-meshes)
   - [Avizo Addons](#avizo-addons)
   - [ImageJ Macros](#imagej-mdacros)
   - [Helper Functions](#helper-functions)
   - [Parallelization Support](#parallelization-support)
   - [BounTI Multithreaded Implementation](#bounti-multithreaded-implementation)
   - [Unzipping Morphosource Zip Files](#miscellaneous-unzipping-morphosource-zip-files)


### Optional Tools
1. **MeshLab**  
   - MeshLab is a tool for viewing 3D meshes generated by SPROUT.

2. **Optional Visualization Tools**  
   - 3D: Tools like **DragonFly** or **Avizo** can be used to visualize and manipulate SPROUT's segmentation results.
   - 2D: Tools like **ImageJ** can be used to visualize and manipulate SPROUT's 2D segmentation results.

### Visualize by Meshes
SPROUT provide scripts to generate meshes for visualisation.

#### **`make_mesh.py`**
Generates meshes for segmentations.
   - **Usage**:
      - Run with the default configuration:  
         ```bash
         python make_mesh.py  
         ```
         *(Reads the `./make_mesh.yaml` file)*  
      - Run with a custom configuration:  
         ```bash
         python make_mesh.py <config>.yaml  
         ```
      - Run with a custom configuration:  
         ```bash
         python make_mesh.py ./template/make_mesh.yaml
         ```
      An example YAML configuration file is available at `./template/make_mesh.yaml`, which generates meshes for the grown results from the example in the `PipelineGrow.py`

   - **Key Parameters**:  
      - `img_path`: Path to the input segmentation. (Specify **either** `img_path` or `input_folder`)  
      - `input_folder`: A folder containing multiple segmentations.  
      - `output_folder`: Directory where the generated meshes will be saved. 
      - `num_threads`: Number of threads for parallel processing.  
      - `downsample_scale`: Mesh simplification factor (*higher values reduce mesh complexity*).
      - `step_size`: Controls the **marching cubes** mesh reconstruction (*1 = original size; higher values generate simpler meshes*).  
  
  - **Outputs**, For each **input segmentation**, a corresponding folder (matching the segmentation filename) will be created, containing:  
      - **Individual Meshes** (`.ply` format)  
         - Example: `1.ply`, `2.ply`, `3.ply` (each representing a separate segmentation class).  
      - **Merged Meshes**  
         - `merged.ply`: Combined mesh of all classes.  
         - `merged_n_to_m.ply`: Merged meshes for **class groups (e.g., classes 1–10, 11–20, etc.)**.  

Meshes use a 10-color cyclic colormap, where class IDs 1–10 map to distinct colors and repeat for IDs beyond 10.  
![Color Map](./material/colourmap.png)


### Avizo Addons
Addon scripts are saved in `./avizo` folder. 
Change the extension from `py` to `pyscro`, and drag into AVIZO's `Project View` to use it.

#### **`PreProcess.py`**  
It is a script designed for pre-processing images based on the skull-suture workflow. It simplifies the pre-processing pipeline by combining multiple functions into a single add-on, eliminating the need to open multiple functions in AVIZO. 

When setting up the input in the add-on UI, the following operations can be performed:
- **Cropping**: Define a region of interest to focus on specific parts of the image.
- **Swapping Axes**: Reorient the volume by swapping axes as needed.
- **Resampling**: Scale voxel sizes to adjust the resolution of the dataset.
- **Converting to 8-bit**: Reduce the bit depth of the image for standardization or compatibility.

Additionally, it automatically creates all essential objects useful for preprocessing, such as:
- Volume rendering
- Ortho-slices
- Axes
- Bounding boxes

**Transformations (e.g., rotations)** are not currently supported and must be performed separately.

#### **`LoadVisFiles.py`**  

It is a script designed to batch process and visualize segmentation labels in AVIZO.

- **Batch Loading and Conversion**: Load and convert 8-bit segmentation labels into AVIZO in a single batch, streamlining the workflow. Supports reordering material/class IDs based on size using AVIZO's `reorder` function. Some AVIZO versions may not support the reorder function. In such cases, simply untick the reorder option during processing.
- **Visualization Options**: Provides options for visualizing segmentation labels in either voxel or mesh format, enabling flexible data exploration.
- **Material Name Mapping**: Outputs the relationship between material names and their corresponding segmentation classes, ensuring clarity and traceability during visualization.

#### **`Edit.py`**  

Performs the same tasks described in the Helper Functions for Editing section, combining multiple editing operations into a single script for convenience.

---

### **ImageJ Macros**  

SPROUT provides ImageJ macros (`.ijm` files) in the `./plugins` folder to facilitate segmentation visualization and editing within ImageJ. These macros are **recommended for use with 2D images**.  

You can either **run the scripts directly in the Macro Editor** or **install the `.ijm` files** for easier access. Refer to the official ImageJ [documentation](https://imagej.net/ij/developer/macro/macros.html) for detailed instructions on macro installation and usage.  

#### **`load_vis_results.ijm`**  
This macro loads and colorizes all image files in a selected folder using the `glasbey` color lookup table (`LUT`). It is useful for quickly visualizing multiple segmentation results (e.g., seeds and grown results) in ImageJ.  
 
  - Asks for an input folder containing segmentation results  
  - Loads all images in the folder into ImageJ  
  - Applies `Lookup Tables` → `glasbey` for colorized segmentation display  

#### **`SPROUT_edit.ijm`**  
This macro allows users to manually edit segmentation masks in ImageJ using the `Multi-point tool` providing an intuitive way to refine **seeds** and **grown results**. 
1. Users can select regions of interest with the `Multi-point tool` and apply the following operations:  
   1. **Merge segmentation classes**: Combine selected segments into a single class.  
   2. **Convert selected segments to background**: Remove unwanted regions by setting them as background.  
   3. **Keep only selected regions**: Retain only the chosen areas and set all other segments as background.  
2. Users can use ROI tools like rectangle, polygon and free-hand to select regions and get the selected regions into user-input value. Then a split connected components can be performed, if users separate a region into multiple.   


### Helper Functions

#### Editing scripts
Editing scripts for segmentations (seeds and results) are provided in the `./help_functions/` folder:

- **`filter_class.py`**: Retains only the specified IDs in a segmentation.
- **`merge_class.py`**: Merges a list of IDs into a single ID in a segmentation.
- **`merge_imgs.py`**: Merges two segmentations (IDs for each segmentation can be specified).
- **`sort_and_filter_seg_by_size.py`**: Orders segments by size and removes those smaller than a given size.
- **`split_class.py`**: Splits a segment into multiple segments if separations (disconnected components) exist.

#### Processing files

- **`read_tiff_to_csv.py`**: Reads `.tif` or `.tiff` files from specified folders (e.g., `img`, `seg`, and `boundary`), aligns them based on filenames, and outputs a CSV file. This CSV file can then be used as input for pipeline scripts. Options are provided to handle prefixes and suffixes for alignment.

---
### Parallelization Support

All SPROUT scripts (`make_seeds.py`, `make_seeds_all.py`, `make_seeds_merged.py`, `make_grow_result.py`, `make_mesh.py`, `PipelineSeed.py`, `PipelineGrow.py`) support **parallelization** using Python's `threading` library. This allows for faster execution by distributing tasks across multiple threads.

- **How It Works**:  
  You can specify the number of threads in the configuration file (`num_threads`). By utilizing multiple threads, the scripts can process data simultaneously, significantly improving efficiency for large datasets or computationally intensive tasks.

- **Recommendation**:  
  For optimal performance, set `num_threads` to match the number of CPU cores on your system.

---
### BounTI Multithreaded Implementation

SPROUT was inspired by **BounTI**, a boundary-preserving threshold iteration approach:  
**M. Didziokas, E. Pauws, L. Kölby, R. H. Khonsari, M. Moazen. 2024.**  
[*BounTI: A user-friendly tool for automatic hard tissue segmentation.*](https://pubmed.ncbi.nlm.nih.gov/38760955/) *Journal of Anatomy 245, 829–841*.

The script `./BounTI/run_bounti_mp.py` is designed to run **BounTI** and **BounTI Flood** using a multithreaded approach. It efficiently processes a list of initial thresholds in parallel, leveraging multiple threads for improved performance.

---
### Miscellaneous: Unzipping Morphosource Zip Files


The following scripts provide utilities for handling [Morphosource datasets](https://www.morphosource.org/) in the `./help_functions/morphosource/` folder:

- **`morphosource_unzip.ipynb`**: Jupyter Notebook version for interactive use.
- **`morphosource_unzip.py`**: Python script for command-line usage. Input configurations (the input folder and the output folder) are stored in `morpho.yaml`.

#### Functionality:
- Unzips all `*.zip` files from a specified input folder to a target output folder.
- Logs important details for each file, including:
  - Path of the original `.zip` file.
  - Path of the extracted contents.
  - Status of the extraction (success/failure).
- Supports batch unzipping of Morphosource datasets in a folder.

#### Morphosource File Structure:
These scripts handle the expected Morphosource file structure, ensuring extracted files are well-organized for subsequent processing.

