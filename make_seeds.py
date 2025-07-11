

import threading
import os, sys
from datetime import datetime
import itertools

import make_mesh
import glob

lock = threading.Lock()


import multiprocessing
max_threads = multiprocessing.cpu_count()

# import configparser
import sprout_core.sprout_core as sprout_core
import sprout_core.config_core as config_core
import sprout_core.vis_lib as vis_lib


import json, yaml
            
pre_set_footprint_list = [
    ["ball"],
    ["ball_XY"],
    ["ball_YZ"] ,
    ["ball_XZ"]

]

pre_set_sub_folders = [footprint[0] for footprint in pre_set_footprint_list]

pre_set_footprint_list_2d = [
    ["disk"],
    ["X"],
    ["Y"] 
]

pre_set_sub_folders_2d = [footprint[0] for footprint in pre_set_footprint_list_2d]




def gen_seed_mp(volume, thre_fp_pairs, ero_iter , segments , 
                        boundary = None ,result_dict = None, return_for_napari = False):
    
    
    for threshold_ero_iter_pair in thre_fp_pairs:
        if isinstance(threshold_ero_iter_pair[0],  tuple):
            threshold = threshold_ero_iter_pair[0][0]
            upper_threshold = threshold_ero_iter_pair[0][1]
        else:
            raise ValueError("Check input thresholds and upper thresholds")

        footprints = threshold_ero_iter_pair[1][0]
        output_seed_folder =  threshold_ero_iter_pair[1][1]
        os.makedirs(output_seed_folder, exist_ok=True)

        output_json_path = os.path.join(output_seed_folder,
                                    f"seed_log_{datetime.now().strftime('%Y%m%d_%H%M')}.json")

        if footprints == 'ball' or footprints == 'default':
            footprints = ['ball'] * ero_iter
        
    
        print(f"Saving every seeds for thresholds {threshold} and upper thresholds {upper_threshold} with {ero_iter} erosion")
        print(f"With the footprints {footprints}")
        
        seed_dict, log_dict = sprout_core.find_seed_by_ero_custom(volume, threshold , segments, ero_iter,
                                          output_dir =output_seed_folder,
                                          footprints = footprints,
                                          upper_threshold = upper_threshold,
                                          boundary = boundary,
                                          is_return_seeds = return_for_napari)
        

        # log_dict['input_file'] = file_path
        print(f"Seeds are saved to {output_seed_folder}")
        print(f"Log file has been saved to {output_json_path}")
                
        with lock:
            # filename = f'output/json/Bount_ori_run_log_{init_threshold}_{target_threshold}.json'
            config_core.write_json(output_json_path, log_dict)   
            if return_for_napari and result_dict is not None:
                result_dict.update(seed_dict)
                # result_dict[output_seed_folder] = seed_dict



def find_seed_by_ero_mp(volume, input_threshold_ero_iter_pairs , segments , 
                        output_seed_folder, output_json_path,  footprints = 'default',
                        boundary = None):
    """
    Seed generation using erosion and thresholds for multi-threading.

    Args:
        volume (np.ndarray): 3D volume data.
        input_threshold_ero_iter_pairs (list): List of (threshold, erosion) pairs.
        segments (int): Number of segments to keep.
        output_seed_folder (str): Directory to save seed outputs.
        output_json_path (str): Path to save the log JSON.
        footprints (str): Footprint type for erosion (default is 'default').
        boundary (np.ndarray): Boundary for defining non-target area (default: None).
    """
    
    for threshold_ero_iter_pair in input_threshold_ero_iter_pairs:
        # threshold = threshold_ero_iter_pair[0]
        if isinstance(threshold_ero_iter_pair[0],  int):
            threshold = threshold_ero_iter_pair[0]
            upper_threshold = None
        elif isinstance(threshold_ero_iter_pair[0],  tuple):
            threshold = threshold_ero_iter_pair[0][0]
            upper_threshold = threshold_ero_iter_pair[0][1]
        else:
            raise ValueError("Check input thresholds and upper thresholds")

        ero_iter = threshold_ero_iter_pair[1]
        
        if footprints == 'ball' or footprints == 'default':
            footprints = ['ball'] * ero_iter
        
    
        print(f"Saving every seeds for thresholds {threshold} and upper thresholds {upper_threshold} with {ero_iter} erosion")
        print(f"With the footprints {footprints}")
        
        log_dict = sprout_core.find_seed_by_ero_custom(volume, threshold , segments, ero_iter,
                                          output_dir =output_seed_folder,
                                          footprints = footprints,
                                          upper_threshold = upper_threshold,
                                          boundary = boundary)
        
        # seed = seed.astype('uint8')
        # seed_file = os.path.join(output_seed_folder , 
        #                     f"thre_ero_{ero_iter}iter_thre{threshold}.tif")
        
        # tifffile.imwrite(seed_file, 
        #     seed)
        
        # log_dict['input_file'] = file_path
        print(f"Seeds are saved to {output_seed_folder}")
        print(f"Log file has been saved to {output_json_path}")
                
        with lock:
            # filename = f'output/json/Bount_ori_run_log_{init_threshold}_{target_threshold}.json'
            config_core.write_json(output_json_path, log_dict)   




def make_seeds(**kwargs):
    """
    Generate seed masks for image segmentation using erosion and thresholding.

    This function processes an input image to generate seed masks for segmentation, supporting both 2D and 3D images. 
    It allows for configurable erosion iterations, thresholding, and footprint shapes, and can run in parallel using multiple threads. 
    Optionally, it can generate mesh files from the resulting seeds.

    Parameters
    ----------
    img : np.ndarray, optional
        The input image array. If not provided, `img_path` must be specified.
    workspace : str, optional
        Base directory to prepend to `img_path` and `output_folder`.
    img_path : str, optional
        Path to the input image file. Used if `img` is not provided.
    boundary : np.ndarray, optional
        Boundary mask array. If not provided, `boundary_path` may be used.
    boundary_path : str, optional
        Path to the boundary mask file.
    output_folder : str, optional
        Directory where output files will be saved.
    base_name : str, optional
        base_name for naming output files and folders.
    erosion_steps : int
        Number of erosion iterations to perform.
    thresholds : int or list of int
        Lower threshold(s) for segmentation. Can be a single value or a list.
    upper_thresholds : int or list of int, optional
        Upper threshold(s) for segmentation. If provided, must match the length of `thresholds`.
    segments : int, optional
        Number of connected components to keep after segmentation.
    num_threads : int, optional
        Number of threads to use for parallel processing. Defaults to 1.
    is_make_meshes : bool, optional
        Whether to generate mesh files from the seed masks. Defaults to False.
    downsample_scale : int, optional
        Downsampling factor for mesh generation. Defaults to 10.
    step_size : int, optional
        Step size for mesh generation. Defaults to 1.
    footprints : str or list of str, optional
        Custom erosion footprints to use. If not provided, pre-set footprints are used based on image dimensionality.
    return_for_napari : bool, optional
        If True, returns seed masks for napari visualization. Defaults to False.

    Returns
    -------
    seed_dict : dict
        Dictionary of generated seed masks (only if return_for_napari is True).
    log_dict : dict
        Dictionary containing:
            - "output_seed_sub_folders": List of output subfolder paths for seed masks.
            - "output_log_files": List of log file paths for each run.

    Raises
    ------
    AssertionError
        If `thresholds` and `upper_thresholds` are provided but have different lengths, or if lower threshold is not less than upper threshold.
    ValueError
        If provided footprints are invalid or not supported.

    Notes
    -----
    - The function saves configuration and logs in the output directory.
    - Mesh generation requires the `make_mesh` module.
    - Threading is used for parallel processing of threshold/erosion parameter combinations.
    - If `return_for_napari` is True, the function returns a dictionary of seed masks for visualization.
    """
    
    
    
    # Input and Output
    img = kwargs.get('img', None) 
    workspace = kwargs.get('workspace', None)
    img_path = kwargs.get('img_path', None)  
    
    # Getting the boundary
    boundary  = kwargs.get('boundary', None) 
    boundary_path  = kwargs.get('boundary_path', None) 

    output_folder = kwargs.get('output_folder', None) 
    base_name = kwargs.get('base_name', None) 

    # Add work space if necessary
    if workspace is not None:
        img_path = os.path.join(workspace, img_path)
        output_folder =os.path.join(workspace, output_folder)
    
    output_folder = os.path.abspath(output_folder)
    
    base_name = config_core.check_and_assign_base_name(base_name, img_path, "seed")

            
    img = config_core.check_and_load_data(img, img_path, "img")
    boundary = config_core.check_and_load_data(boundary, boundary_path, "boundary", must_exist=False)
    config_core.valid_input_data(img, boundary=boundary)
    
    # Seed generation related 
    erosion_steps = kwargs.get('erosion_steps', None)
    thresholds = kwargs.get('thresholds', None) 
    upper_thresholds = kwargs.get('upper_thresholds', None) 

    thresholds, upper_thresholds = config_core.check_and_assign_thresholds(thresholds, upper_thresholds)
    
 
    segments = kwargs.get('segments', None)  
    num_threads = kwargs.get('num_threads', None) 
    
    is_make_meshes = kwargs.get('is_make_meshes', False) 
    downsample_scale = kwargs.get('downsample_scale', 10) 
    step_size  = kwargs.get('step_size', 1) 

    footprints = kwargs.get('footprints', None)
    
    return_for_napari = kwargs.get('return_for_napari', False)

    if num_threads is None:
        num_threads = max(1, max_threads // 2)

    if num_threads>=max_threads:
        num_threads = max(1,max_threads-1)


    is_3d = (img.ndim == 3)
    


    log_dict = {
        "output_seed_sub_folders":[],
        "output_log_files":[]
    }
    
    # for ero_iter in erosion_steps:
        
    ## Dealing with footprints
    if footprints is None:
        # if input footprints is not provided, use pre-set footprints
        if is_3d:
            footprint_list = [footprint*erosion_steps for footprint in pre_set_footprint_list]
            output_seed_sub_folders = pre_set_sub_folders
        else:
            footprint_list = [footprint*erosion_steps for footprint in pre_set_footprint_list_2d]
            output_seed_sub_folders = pre_set_sub_folders_2d
    else:
        
        footprint_list , output_seed_sub_folders = config_core.check_and_assign_footprint(footprints, erosion_steps , with_folder_name=True)
        footprint_list = [footprint_list]
        output_seed_sub_folders = [output_seed_sub_folders]
         
    
    # Create threshold pairs

    thresholds_pairs = list(zip(thresholds, upper_thresholds))
    
    
    output_seed_sub_folders = [os.path.join(output_folder, base_name,
                                            output_seed_sub_folder) for output_seed_sub_folder in output_seed_sub_folders]
    
    thre_fp_pairs = list(itertools.product(thresholds_pairs, zip(footprint_list,output_seed_sub_folders)))
    
    sublists = [thre_fp_pairs[i::num_threads] for i in range(num_threads)]   

    

    start_time = datetime.now()
    print(f"""{start_time.strftime("%Y-%m-%d %H:%M:%S")}
    Making erosion seeds for 
        Img: {base_name}
        boundary: {boundary_path if boundary_path else "None"}
        Is 3D image: {is_3d}
        Threshold for Img {thresholds}
        Upper Thresholds for Img {upper_thresholds}
        Erode {erosion_steps} iterations
        Keeping {segments} components
        Running in {num_threads} threads
        Output folder: {output_folder}
            """)      

    # Create a list to hold the threads
    threads = []

    seeds_dict = {}
    # Start a new thread for each sublist
    for sublist in sublists:

        # thread = threading.Thread(target=find_seed_by_ero_mp, args=(img,sublist, segments,
        #                                                             output_seed_sub_folder,output_json_path, footprints,
        #                                                             boundary))

        thread = threading.Thread(target=gen_seed_mp, args=(img,sublist, erosion_steps, segments,
                                                                    boundary, seeds_dict, return_for_napari))
        threads.append(thread)
        thread.start()
        
    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # print(f"All threads have completed. Log is saved at {output_json_path},seeds are saved at {output_seed_folder}")

    
    end_time = datetime.now()
    running_time = end_time - start_time
    total_seconds = running_time.total_seconds()
    minutes, _ = divmod(total_seconds, 60)
    print(f"Running time:{minutes}")

    for output_seed_sub_folder in output_seed_sub_folders:
        log_dict["output_seed_sub_folders"].append(output_seed_sub_folder)
        output_json_path = os.path.join(output_seed_sub_folder,
                            f"seed_log_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
        log_dict["output_log_files"].append(output_json_path)

        # # Make meshes  
        if is_make_meshes: 
            tif_files = glob.glob(os.path.join(output_seed_sub_folder, '*.tif'))

            for tif_file in tif_files:
                make_mesh.make_mesh_for_tiff(tif_file,output_seed_sub_folder,
                                    num_threads=num_threads,no_zero = True,
                                    colormap = "color10",
                                    downsample_scale=downsample_scale,
                                    step_size=step_size)
    
    config_core.save_config_with_output({
        "output_dict": log_dict,
        "params": kwargs},output_seed_sub_folder)
        
    return seeds_dict , log_dict
 
def plot(output_dict, full_log_plot_path):
    output_log_files = output_dict["output_log_files"]
    output_seed_sub_folders = output_dict["output_seed_sub_folders"]
    
    plot_list = []
    for output_log_file, output_seed_sub_folder in zip(output_log_files,output_seed_sub_folders):
        
        with open(output_log_file, 'r') as config_file:
            json_data = json.load(config_file)
        
        vis_lib.plot_seeds_log_json(json_data, os.path.join(output_seed_sub_folder, "seeds.png"))
        
        # plot_data = vis_lib.seeds_json_to_plot_ready(output_log_file)
        # vis_lib.plot_seeds_log(plot_data, os.path.join(output_seed_sub_folder, "seeds.png"))
        
        plot_list.append(os.path.join(output_seed_sub_folder, "seeds.png"))

    
    vis_lib.merge_plots(plot_list, full_log_plot_path)

def run_make_seeds(file_path):
    _, extension = os.path.splitext(file_path)
    print(f"processing config the file {file_path}")

    if extension == '.yaml':
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
            optional_params = config_core.validate_input_yaml(config, config_core.input_val_make_seeds_all)
            

    
    _, output_dict = make_seeds(
        workspace= optional_params['workspace'],
            img_path= config['img_path'],
            boundary_path = optional_params['boundary_path'],
            output_folder = config['output_folder'],
            num_threads = config['num_threads'],
            erosion_steps = config['erosion_steps'],
            thresholds = config['thresholds'],
            segments = config['segments'],
            upper_thresholds = optional_params['upper_thresholds'],
            
            is_make_meshes = optional_params['is_make_meshes'],
            downsample_scale = optional_params['downsample_scale'],
            step_size  = optional_params['step_size'],
            footprints = optional_params['footprints'],
            base_name = optional_params['base_name'],
            )    


if __name__ == "__main__":
    # Get the file path from the first command-line argument or use the default
    file_path = sys.argv[1] if len(sys.argv) > 1 else './make_seeds.yaml'
    
    run_make_seeds(file_path)
    
    
    # Make plot based on the seeds log json
    # Doing this after parallel/multi processing
    # plot(output_dict, os.path.join(os.path.join(optional_params['workspace'], config['output_folder'], "full_log.png")))
