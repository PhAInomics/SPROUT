
The code is highly inspired by Bounti.
It is used to separate parts for 3D scans
Here have three main parts.

1. Generate seeds <br>
Use morphological transformations and connected components (initial segmentations for grow)
    1. `make_seeds.py` is the for generating seeds. Config file template: `make_seeds.yaml` 
        - workspace: The folder for the data
        - file_name: path to input image
        - num_threads: multiple threads
        - target_thresholds: 0 for binary segmentation. For images, it's a threshold for segmenting the images
        - ero_iters: Iterations for erosion
        - segments: Integer >=1, Top <segments> largest disconnected componenets
        - output_seed_folder:
        - output_log_file: Name of the output file name
        - footprints: The way you want to erode your images, current supports "ball" and "cube" :Erosion all directions. 'ball_XY', 'ball_XZ', 'ball_YZ': Erosion on the Plane. 'X', 'Y', 'Z': Erosion on the axis.

    <br>

    2. `make_seeds_foram.py` is the algorithm for generating seeds for the binary segmentation of foram chambers. Fully automatic


2. Grow back to the full
    1. `make_grow_result.py` To grow the seeds to back to the original images with thresholds, or grow back to the binary segmentation<br>
    `make_grow_result.yaml`

3. Visualization 
    1. `make_mesh.py` Create a mesh for every class for the input seed/result<br>
    Can change `make_mesh.yaml` values to set the input, and output directory
    A folder of seeds/results
    One seed/result
    
    2. `plot_mesh.py` Plot Generated meshes. <br>
    Currently under testing
    
## BounTI multithread implementation
`./BounTI/run_bounti_mp.py` is used to run BounTI and BounTI flood, with a list of initial thresholds. 


## Help functions:
Merge classes in one image
Merge classes from two images
Remove classes

## Parallelization:
`make_mesh.py`, `make_seeds.py`, `make_seeds_foram.py` currently support running in multiple processes. Please check your CPU and set the right `num_threads` in the configuration file

