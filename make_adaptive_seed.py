import numpy as np
import pandas as pd

# from PIL import Image
from tifffile import imread, imwrite
import os,sys
from datetime import datetime
import glob
import threading
lock = threading.Lock()
import time
import yaml
from scipy.spatial import ConvexHull

# Add the lib directory to the system path
import sprout_core.sprout_core as sprout_core
import sprout_core.config_core as config_core
from sprout_core.sprout_core import reorder_segmentation



def load_config_yaml(config, parent_key=''):
    """
    Recursively load configuration values from a YAML dictionary into global variables.

    Args:
        config (dict): Configuration dictionary.
        parent_key (str): Key prefix for nested configurations (default is '').
    """
    for key, value in config.items():
        if isinstance(value, dict):
            load_config_yaml(value, parent_key='')
        else:
            globals()[parent_key + key] = value

def split_size_check(mask, split_size_limit):
    split_size_lower = split_size_limit[0]
    split_size_upper = split_size_limit[1]
    split_size_condition = True
    if split_size_lower is not None or split_size_upper is not None:
        split_size_temp = np.sum(mask)
        if (split_size_lower is not None) and (split_size_temp < split_size_lower): 
            split_size_condition = False 
        if (split_size_upper is not None) and (split_size_temp > split_size_upper):
            split_size_condition = False 
    
    return split_size_condition

def split_convex_hull_check(mask, split_convex_hull_limit):
    lower = split_convex_hull_limit[0]
    upper = split_convex_hull_limit[1]
    split_size_condition = True
    if lower is not None or upper is not None:
        # split_size_temp = np.sum(mask)
        coords = np.column_stack(np.where(mask))
        if len(coords) >= 4:  # Convex hull needs at least 4 points in 3D
            hull = ConvexHull(coords)
            convex_hull_volume = int(hull.volume)
        else:
            return False
        if (lower is not None) and (convex_hull_volume < lower): 
            split_size_condition = False 
            print(f"convex hull only:{convex_hull_volume}, but lower is {lower}")
        if (upper is not None) and (convex_hull_volume > upper):
            split_size_condition = False 
            print(f"convex hull only:{convex_hull_volume}, but upper is {upper}")
        
    return split_size_condition

def detect_inter(ccomp_combine_seed,ero_seed, seed_ids, inter_log , lock):
    """
    Detect intersections between seeds and combined components.

    Args:
        ccomp_combine_seed (np.ndarray): Combined seed mask.
        ero_seed (np.ndarray): Eroded seed mask.
        seed_ids (list): List of seed IDs to process.
        inter_log (dict): Dictionary to log intersection results.
        lock (threading.Lock): Threading lock for shared resources.
    """
    
    for seed_id in seed_ids:
        seed_ccomp = ero_seed == seed_id
                    
        # Check if there are intersection using the sum of intersection
        inter = np.sum(ccomp_combine_seed[seed_ccomp])

        with lock:
            if inter>0:
                inter_log["inter_count"] +=1
                
                inter_log["inter_ids"] = np.append(inter_log["inter_ids"] , seed_id)
                
                prop = round(inter / np.sum(ccomp_combine_seed),6)*100
                inter_log["inter_props"] = np.append(inter_log["inter_props"], prop)


def make_seeds_merged_path_wrapper(img_path,
                              threshold,
                              output_folder,
                              n_iters,
                              segments,
                              boundary_path=None,
                              num_threads=1,
                              background=0,
                              sort=True,
                              no_split_limit=3,
                              min_size=5,
                              min_split_prop=0.01,
                              min_split_sum_prop=0,
                              save_every_iter=False,
                              save_merged_every_iter=False,
                              name_prefix="Merged_seed",
                              init_segments=None,
                              footprint="ball",
                              upper_threshold = None,
                              split_size_limit = (None,None),
                              split_convex_hull_limit = (None, None)
                              ):
    """
    Wrapper for make_seeds_merged_mp that performs erosion-based merged seed generation with multi-threading.

    Args:
        img_path (str): Path to the input image.
        threshold (int): Threshold for segmentation. One value
        output_folder (str): Directory to save output seeds.
        n_iters (int): Number of erosion iterations.
        segments (int): Number of segments to extract.
        boundary_path (str, optional): Path to boundary image. Defaults to None.
        num_threads (int, optional): Number of threads to use. Defaults to 1.
        background (int, optional): Background value. Defaults to 0.
        sort (bool, optional): Whether to sort output segment IDs. Defaults to True.
        no_split_limit (int, optional): Early Stop Check: Limit for consecutive no-split iterations. Defaults to 3.
        min_size (int, optional): Minimum size for segments. Defaults to 5.
        min_split_prop (float, optional): Minimum proportion to consider a split. Defaults to 0.01.
        min_split_sum_prop (float, optional): Minimum proportion of (sub-segments from next step)/(current segments)
            to consider a split. Defaults to 0.
        save_every_iter (bool, optional): Save results at every iteration. Defaults to False.
        save_merged_every_iter (bool, optional): Save merged results at every iteration. Defaults to False.
        name_prefix (str, optional): Prefix for output file names. Defaults to "Merged_seed".
        init_segments (int, optional): Initial segments. Defaults to None.
        footprint (str, optional): Footprint shape for erosion. Defaults to "ball".
        split_size_limit (optional): create a split if the region size (np.sum(mask)) is within the limit
        split_convex_hull_limit: create a split if the the convex hull's area/volume is within the limit

    Returns:
        tuple: Merged seeds, original combine ID map, and output dictionary.
    """
    # Read the image
    img = imread(img_path)
    print(f"Loaded image from: {img_path}")
    
    # Read the boundary if provided
    boundary = None
    if boundary_path is not None:
        boundary = imread(boundary_path)
    
    # Prepare values for printing
    start_time = datetime.now()
    values_to_print = {
        "Boundary Path": boundary_path if boundary_path else "None"
    }

    # Print detailed values
    print("Start time: " + start_time.strftime("%Y-%m-%d %H:%M:%S"))
    print(f"Processing Image: {img_path}")
    for key, value in values_to_print.items():
        print(f"  {key}: {value}")
    
    
    # Call the original function
    seed ,ori_combine_ids_map , output_dict=make_seeds_merged_mp(img=img,
                        threshold=threshold,
                        output_folder=output_folder,
                        n_iters=n_iters,
                        segments=segments,
                        boundary=boundary,
                        num_threads=num_threads,
                        no_split_limit=no_split_limit,
                        min_size=min_size,
                        sort=sort,
                        min_split_prop=min_split_prop,
                        background=background,
                        save_every_iter=save_every_iter,
                        save_merged_every_iter=save_merged_every_iter,
                        name_prefix=name_prefix,
                        init_segments=init_segments,
                        footprint=footprint,
                        min_split_sum_prop=min_split_sum_prop,
                        upper_threshold = upper_threshold,
                        split_size_limit = split_size_limit,
                        split_convex_hull_limit = split_convex_hull_limit
                        )


    end_time = datetime.now()
    running_time = end_time - start_time
    total_seconds = running_time.total_seconds()
    minutes, _ = divmod(total_seconds, 60)
    print(f"Running time:{minutes}")
    
    return seed ,ori_combine_ids_map , output_dict


def make_seeds_merged_mp(
                         
                        threshold,
                        output_folder,
                        n_iters, 
                        segments,
                        
                        img = None,
                        img_path = None,
                        
                        boundary = None,
                        boundary_path = None,
                        
                        num_threads = 1,
                        background = 0,
                        sort = True,
                        no_split_limit =3,
                        min_size=5,
                        min_split_prop = 0.01,
                        min_split_sum_prop = 0,
                        save_every_iter = False,
                        save_merged_every_iter = False,
                        name_prefix = "Merged_seed",
                        init_segments = None,
                        footprint = "ball",
                        upper_threshold = None,
                        split_size_limit = (None,None),
                        split_convex_hull_limit = (None, None),
                        sub_folder = None                    
                      ):
    """
    Erosion-based merged seed generation with multi-threading.

    Args:
        img (np.ndarray): Input image.
        threshold (int): Threshold for segmentation. One value
        output_folder (str): Directory to save output seeds.
        n_iters (int): Number of erosion iterations.
        segments (int): Number of segments to extract.
        boundary (np.ndarray, optional): Boundary mask. Defaults to None.
        num_threads (int, optional): Number of threads to use. Defaults to 1.
        background (int, optional): Background value. Defaults to 0.
        sort (bool, optional): Whether to sort output segment IDs. Defaults to True.
        no_split_limit (int, optional): Early Stop Check: Limit for consecutive no-split iterations. Defaults to 3.
        min_size (int, optional): Minimum size for segments. Defaults to 5.
        min_split_prop (float, optional): Minimum proportion to consider a split. Defaults to 0.01.
        min_split_sum_prop (float, optional): Minimum proportion of (sub-segments from next step)/(current segments)
            to consider a split. Defaults to 0. Range: 0 to 1
        save_every_iter (bool, optional): Save results at every iteration. Defaults to False.
        save_merged_every_iter (bool, optional): Save merged results at every iteration. Defaults to False.
        name_prefix (str, optional): Prefix for output file names. Defaults to "Merged_seed".
        init_segments (int, optional): Number of segments for the first seed, defaults is None.
            A small number of make the initial sepration faster, as normally the first seed only has a big one component
        footprint (str, optional): Footprint shape for erosion. Defaults to "ball".
        split_size_limit (optional): create a split if the region size (np.sum(mask)) is within the limit
        split_convex_hull_limit: create a split if the the convex hull's area/volume is within the limit

    Returns:
        tuple: Merged seeds, original combine ID map, and output dictionary.
    """
    
    img = sprout_core.check_and_load_data(img, img_path, "img")
    if not (boundary is None and boundary_path is None):
        boundary = sprout_core.check_and_load_data(boundary, boundary_path, "boundary")
        
    
    
    min_split_prop = min_split_prop*100
    min_split_sum_prop = min_split_sum_prop*100



    output_name = f"{name_prefix}_thre_{threshold}_{upper_threshold}_ero_{n_iters}"
    
    if sub_folder is None:
        output_folder = os.path.join(output_folder, output_name)
    else:
        output_folder = os.path.join(output_folder, sub_folder)
    os.makedirs(output_folder,exist_ok=True)

    if isinstance(footprint, str):

        assert footprint in config_core.support_footprints, f"footprint {footprint} is invalid, use supported footprints"
        footprint_list = [footprint]*n_iters
    elif isinstance(footprint, list):
        assert len(footprint) ==n_iters, "If input_footprints is a list, it must have the same length as ero_iters"
        
        check_support_footprint = [footprint in config_core.support_footprints for footprint in footprint]
        if not np.all(check_support_footprint):
            raise ValueError(f"footprint {footprint} is invalid, use supported footprints")
        
        footprint_list = footprint
    else:
        raise ValueError(f"Can't set the footprint list with the input footprint {footprint} ")
    
    values_to_print = {
        "img_path": img_path,
        "Threshold": threshold,
        "upper_threshold": upper_threshold,
        "Output Folder": output_folder,
        "Erosion Iterations": n_iters,
        "Segments": segments,
        "boundary_path": boundary_path,
        
        "Number of Threads": num_threads,
        "Sort": sort,
        "Background Value": background,
        "Save Every Iteration": save_every_iter,
        "Save Merged Every Iteration": save_merged_every_iter,
        "Name Prefix": name_prefix,
        "Footprint": footprint_list,
        "No Split Limit for iters": no_split_limit,
        "Component Minimum Size": min_size,
        "Minimum Split Proportion (%)": min_split_prop,
        "Minimum Split Sum Proportion (%)": min_split_sum_prop,
        "split_size_limit": split_size_limit,
        "split_convex_hull_limit": split_convex_hull_limit
    }

    for key, value in values_to_print.items():
        print(f"  {key}: {value}")

    
    
    
    max_splits = segments
    
    
    if upper_threshold is not None:
        assert threshold<upper_threshold, "lower_threshold must be smaller than upper_threshold"
        img = (img>=threshold) & (img<=upper_threshold)
    else:
        img = img>=threshold
    # img = img<=threshold

    if boundary is not None:
        boundary = sprout_core.check_and_cast_boundary(boundary)
        img[boundary] = False

    if init_segments is None:
        init_segments = segments

    init_seed, _ = sprout_core.get_ccomps_with_size_order(img,init_segments)
    
    output_img_name = f'INTER_thre_{threshold}_{upper_threshold}_ero_0.tif'
    if save_every_iter:
        imwrite(os.path.join(output_folder,output_img_name), init_seed, 
            compression ='zlib')
    
    init_ids = [int(value) for value in np.unique(init_seed) if value != background]
    max_seed_id = int(np.max(init_ids))


    combine_seed = init_seed.copy()
    combine_seed = combine_seed.astype('uint16')


    output_dict = {"total_id": {0: len(np.unique(combine_seed))-1},
                   "split_id" : {0: {}},
                   "split_ori_id": {0: {}},
                   "split_ori_id_filtered":  {0: {}},
                   "split_prop":  {0: {}},
                   "cur_seed_name": {0: output_img_name},
                   "output_folder":output_folder
                   }

    ori_combine_ids_map = {}
    for value in init_ids :
        ori_combine_ids_map[value] = [value]
    
    # Count for no_split_limit
    no_consec_split_count = 0
    

    for ero_iter in range(1, n_iters+1):
        
        
        print(f"working on erosion {ero_iter}")
        
        output_dict["split_id"][ero_iter] = {}
        output_dict["split_ori_id"][ero_iter] = {}
        output_dict["split_ori_id_filtered"][ero_iter] = {}
        output_dict["split_prop"][ero_iter] = {}
        
        img = sprout_core.erosion_binary_img_on_sub(img, kernal_size = 1,footprint=footprint_list[ero_iter-1])
        seed, _ = sprout_core.get_ccomps_with_size_order(img,segments)
        seed = seed.astype('uint16')
        
        output_img_name = f'INTER_thre_{threshold}_{upper_threshold}_ero_{ero_iter}.tif'
        output_dict["cur_seed_name"][threshold] = output_img_name
        
        if save_every_iter:
            output_path = os.path.join(output_folder, output_img_name)
            print(f"\tSaving {output_path}")
            
            imwrite(output_path, seed, 
                compression ='zlib')

        seed_ids = [int(value) for value in np.unique(seed) if value != background]
        combine_ids = [int(value) for value in np.unique(combine_seed) if value != background]
       
        has_split = False
        ## Comparing each ccomp from eroded seed
        ## to each ccomp from the original seed
        
        inter_log = {
            "inter_count":0,
            "inter_ids": np.array([]),
            "inter_props": np.array([])
        }
        
        for combine_id in combine_ids:
            ccomp_combine_seed = combine_seed == combine_id
            
            inter_log["inter_count"] = 0
            inter_log["inter_ids"] = np.array([])
            inter_log["inter_props"] = np.array([])
            
            sublists = [seed_ids[i::num_threads] for i in range(num_threads)]
             # Create a list to hold the threads
            threads = []
            for sublist in sublists:
                thread = threading.Thread(target=detect_inter, args=(ccomp_combine_seed,
                                                                     seed,
                                                                     sublist,
                                                                     inter_log,
                                                                     lock))
                threads.append(thread)
                thread.start()
                
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
        
        
            ## if there are any intersection between seed and the init seed
            if inter_log["inter_count"]>1:
                temp_inter_count = inter_log["inter_count"]
                temp_inter_ids = inter_log["inter_ids"]
                temp_inter_props = inter_log["inter_props"]
                
                # print(f'\t{combine_id} has been split to {temp_inter_count} parts. Ids are {temp_inter_ids}')
                # print(f"\tprops are: {temp_inter_props}")
                
                sum_inter_props = np.sum(temp_inter_props)
                
                
                
                if not split_size_check(ccomp_combine_seed, split_size_limit):
                    print(f"no split, as {combine_id} only has {np.sum(ccomp_combine_seed) }")             

                split_condition =  (sum_inter_props>=min_split_sum_prop) and\
                    split_size_check(ccomp_combine_seed, split_size_limit) and \
                        split_convex_hull_check(ccomp_combine_seed, split_convex_hull_limit)
                
                # print(f"\tSplit prop is {sum_inter_props}")
                if split_condition:
                    combine_seed[combine_seed == combine_id] =0
                    filtered_inter_ids = temp_inter_ids[temp_inter_props>min_split_prop]
                    
                    if len(filtered_inter_ids)>0:
                        has_split = True
                    
                    new_ids = []
                    for inter_id in filtered_inter_ids:
                        max_seed_id +=1
                        
                        combine_seed[seed == inter_id] = max_seed_id
                        # new_ids.append(max_seed_id)     
                        
                        new_ids.append(max_seed_id)
                        for key,value in ori_combine_ids_map.items():
                            if combine_id in value:
                                ori_combine_ids_map[key].append(max_seed_id)
                                break
                                # if len(value) <= max_splits:
                                    
                    output_dict["split_id"][ero_iter][combine_id] = new_ids
                    output_dict["split_ori_id"][ero_iter][combine_id] = inter_log["inter_ids"]
                    output_dict["split_ori_id_filtered"][ero_iter][combine_id] = filtered_inter_ids
                    output_dict["split_prop"][ero_iter][combine_id] = inter_log["inter_props"]                    
        
            output_dict["total_id"][ero_iter] = len(np.unique(combine_seed))-1
    
        if has_split:
            no_consec_split_count=0
        else:
            no_consec_split_count+=1
            
        
        if save_merged_every_iter:
            combine_seed,_ = reorder_segmentation(combine_seed, min_size=min_size, sort_ids=sort)
            output_path = os.path.join(output_folder,"INTER_merged_"+ output_name+f'ero_{ero_iter}.tif')
            
            print(f"\tSaving merged output:{output_path}")
            imwrite(output_path, combine_seed, 
                compression ='zlib')    
        
        if no_consec_split_count>=no_split_limit:
            print(f"detect non split for {no_consec_split_count}rounds")
            print(f"break loop at {ero_iter} iter")
            break
        

    # output_path = os.path.join(output_folder,output_name+'.tif')
    # print(f"\tSaving final output:{output_path}")
    # imwrite(output_path, combine_seed, 
    #     compression ='zlib')
    
    combine_seed,_ = reorder_segmentation(combine_seed, min_size=min_size, sort_ids=sort)
    if sort:
        output_path = os.path.join(output_folder,"FINAL_" + output_name+'_sorted.tif')
    else:
        output_path = os.path.join(output_folder,"FINAL_" + output_name+'.tif')
    print(f"\tSaving final output:{output_path}")
    imwrite(output_path, combine_seed, 
        compression ='zlib')
    

    config_core.save_config_with_output({
        "params": values_to_print},output_folder)
        

    pd.DataFrame(output_dict).to_csv(os.path.join(output_folder,
                                                  f"output_dict_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"),
                                     index=False)

    return combine_seed,ori_combine_ids_map, output_dict    


def make_seeds_merged_by_thres_path_wrapper(img_path,
                                       thresholds,
                                       output_folder,
                                       n_iters,
                                       segments,
                                       num_threads=1,
                                       boundary_path=None,
                                       background=0,
                                       sort=True,
                                       
                                       no_split_limit=3,
                                       min_size=5,
                                       min_split_prop=0.01,
                                       min_split_sum_prop=0,
                                       
                                       save_every_iter=False,
                                       save_merged_every_iter=False,
                                       name_prefix="Merged_seed",
                                       init_segments=None,
                                       footprint="ball",
                                       
                                       upper_thresholds = None,
                                       split_size_limit = (None, None),
                                       split_convex_hull_limit = (None, None)
                                       ):
    """
    Wrapper for make_seeds_merged_by_thres_mp that performs thresholds-based merged seed generation.

    Args:
        img_path (str): Path to the input image.
        thresholds (list): List of thresholds for segmentation.
        output_folder (str): Directory to save the output.
        n_iters (int): Number of erosion iterations.
        segments (int): Number of segments to extract.
        num_threads (int, optional): Number of threads for parallel processing. Defaults to 1.
        boundary_path (str, optional): Path to boundary image. Defaults to None.
        background (int, optional): Value of background pixels. Defaults to 0.
        sort (bool, optional): Whether to sort segment IDs. Defaults to True.
        
        no_split_limit (int, optional): Early Stop Check: Limit for consecutive no-split iterations. Defaults to 3.
        min_size (int, optional): Minimum size for segments. Defaults to 5.
        min_split_prop (float, optional): Minimum proportion to consider a split. Defaults to 0.01.
        min_split_sum_prop (float, optional): Minimum proportion of (sub-segments from next step)/(current segments)
            to consider a split. Defaults to 0.
            
        save_every_iter (bool, optional): Save results at every iteration. Defaults to False.
        save_merged_every_iter (bool, optional): Save merged results at every iteration. Defaults to False.
        name_prefix (str, optional): Prefix for output file names. Defaults to "Merged_seed".
        init_segments (int, optional): Number of segments for the first seed, defaults is None.
            A small number of make the initial sepration faster, as normally the first seed only has a big one component
        footprint (str, optional): Footprint shape for erosion. Defaults to "ball".
        split_size_limit (optional): create a split if the region size (np.sum(mask)) is within the limit
        split_convex_hull_limit: create a split if the the convex hull's area/volume is within the limit
    Returns:
        tuple: Merged seed, original combine ID map, and output dictionary.
    """
    # Read the image
    img = imread(img_path)
    print(f"Loaded image from: {img_path}")
    
    # Read the boundary if provided
    boundary = None
    if boundary_path is not None:
        boundary = imread(boundary_path)
    
    # Prepare values for printing
    start_time = datetime.now()
    values_to_print = {
        "Boundary Path": boundary_path if boundary_path else "None"
    }

    # Print detailed values
    print("Start time: " + start_time.strftime("%Y-%m-%d %H:%M:%S"))
    print(f"Processing Image: {img_path}")
    for key, value in values_to_print.items():
        print(f"  {key}: {value}")
    
    # Call the original function
    combine_seed,ori_combine_ids_map, output_dict  = make_seeds_merged_by_thres_mp(img=img,
                                  thresholds=thresholds,
                                  output_folder=output_folder,
                                  n_iters=n_iters,
                                  segments=segments,
                                  boundary=boundary,
                                  num_threads=num_threads,
                                  no_split_limit=no_split_limit,
                                  min_size=min_size,
                                  sort=sort,
                                  min_split_prop=min_split_prop,
                                  background=background,
                                  save_every_iter=save_every_iter,
                                  save_merged_every_iter=save_merged_every_iter,
                                  name_prefix=name_prefix,
                                  init_segments=init_segments,
                                  footprint=footprint,
                                  min_split_sum_prop=min_split_sum_prop,
                                  
                                  upper_thresholds = upper_thresholds,
                                  split_size_limit = split_size_limit,
                                  split_convex_hull_limit = split_convex_hull_limit)

    end_time = datetime.now()
    running_time = end_time - start_time
    total_seconds = running_time.total_seconds()
    minutes, _ = divmod(total_seconds, 60)
    print(f"Running time:{minutes}")
    
    return combine_seed,ori_combine_ids_map, output_dict

def make_seeds_merged_by_thres_mp(
                        thresholds,
                        output_folder,
                        n_iters, 
                        segments,
                        
                        img = None,
                        img_path = None,
                        
                        boundary =None,
                        boundary_path = None,
                        
                        num_threads = 1,
                        
                        background = 0,
                        sort = True,
                        
                        no_split_limit =3,
                        min_size=5,
                        min_split_prop = 0.01,
                        min_split_sum_prop = 0,
                        
                        save_every_iter = False,
                        save_merged_every_iter = False,
                        name_prefix = "Merged_seed",
                        init_segments = None,
                        footprint = "ball",
                        
                        upper_thresholds = None,
                        split_size_limit = (None, None),
                        split_convex_hull_limit = (None, None),
                        sub_folder = None  
                    ):
    """
    Thresholds-based merged seed generation.

    Args:
        img (np.ndarray): Input image.
        thresholds (list): List of thresholds for segmentation.
        output_folder (str): Directory to save the output.
        n_iters (int): Number of erosion iterations.
        segments (int): Number of segments to extract.
        num_threads (int, optional): Number of threads for parallel processing. Defaults to 1.
        boundary (np.ndarray, optional): Boundary mask. Defaults to None.
        background (int, optional): Value of background pixels. Defaults to 0.
        sort (bool, optional): Whether to sort segment IDs. Defaults to True.
        
        no_split_limit (int, optional): Early Stop Check: Limit for consecutive no-split iterations. Defaults to 3.
        min_size (int, optional): Minimum size for segments. Defaults to 5.
        min_split_prop (float, optional): Minimum proportion to consider a split. Defaults to 0.01.
        min_split_sum_prop (float, optional): Minimum proportion of (sub-segments from next step)/(current segments)
            to consider a split. Defaults to 0.
            
        save_every_iter (bool, optional): Save results at every iteration. Defaults to False.
        save_merged_every_iter (bool, optional): Save merged results at every iteration. Defaults to False.
        name_prefix (str, optional): Prefix for output file names. Defaults to "Merged_seed".
        init_segments (int, optional): Number of segments for the first seed, defaults is None.
            A small number of make the initial sepration faster, as normally the first seed only has a big one component
        footprint (str, optional): Footprint shape for erosion. Defaults to "ball".
        split_size_limit (optional): create a split if the region size (np.sum(mask)) is within the limit
        split_convex_hull_limit: create a split if the the convex hull's area/volume is within the limit

    Returns:
        tuple: Merged seed, original combine ID map, and output dictionary.
    """

    img = sprout_core.check_and_load_data(img, img_path, "img")
    if not (boundary is None and boundary_path is None):
        boundary = sprout_core.check_and_load_data(boundary, boundary_path, "boundary")

    min_split_prop = min_split_prop*100
    min_split_sum_prop = min_split_sum_prop*100

    output_name = f"{name_prefix}_ero_{n_iters}"
    
    
    if sub_folder is None:
        output_folder = os.path.join(output_folder, output_name)
    else:
        output_folder = os.path.join(output_folder, sub_folder)

    os.makedirs(output_folder,exist_ok=True)

    if isinstance(footprint, str):

        assert footprint in config_core.support_footprints, f"footprint {footprint} is invalid, use supported footprints"
        footprint_list = [footprint]*n_iters
    elif isinstance(footprint, list):
        assert len(footprint) ==n_iters, "If input_footprints is a list, it must have the same length as ero_iters"
        
        check_support_footprint = [footprint in config_core.support_footprints for footprint in footprint]
        if not np.all(check_support_footprint):
            raise ValueError(f"footprint {footprint} is invalid, use supported footprints")
        
        footprint_list = footprint
    else:
        raise ValueError(f"Can't set the footprint list with the input footprint {footprint} ")
        
    values_to_print = {
        "img_path": img_path,
        "Thresholds": thresholds,
        "upper_thresholds": upper_thresholds,
        "Output Folder": output_folder,
        "Erosion Iterations": n_iters,
        "Segments": segments,
        "boundary_path": boundary_path,
        
        "Number of Threads": num_threads,
        "Sort": sort,
        
        "Background Value": background,
        "Save Every Iteration": save_every_iter,
        "Save Merged Every Iteration": save_merged_every_iter,
        "Name Prefix": name_prefix,
        "Footprint": footprint_list,
        "No Split Limit for iters": no_split_limit,
        "Component Minimum Size": min_size,
        "Minimum Split Proportion (%)": min_split_prop,
        "Minimum Split Sum Proportion (%)": min_split_sum_prop,
        "split_size_limit": split_size_limit,
        "split_convex_hull_limit": split_convex_hull_limit
    }

    for key, value in values_to_print.items():
        print(f"  {key}: {value}")



    
    max_splits = segments
    
    if init_segments is None:
        init_segments = segments

    if upper_thresholds is not None:
        assert len(thresholds) == len(upper_thresholds), "lower_thresholds and upper_thresholds should have the same length"
        assert thresholds[0]<upper_thresholds[0], "lower_threshold must be smaller than upper_threshold"
        mask = (img>=thresholds[0]) & (img<=upper_thresholds[0])
    else:
        mask = img>=thresholds[0]
    
    
    if boundary is not None:
        boundary = sprout_core.check_and_cast_boundary(boundary)
        img[boundary] = False
    
    for ero_iter in range(1, n_iters+1):
        mask = sprout_core.erosion_binary_img_on_sub(mask, kernal_size = 1,
                                                     footprint=footprint_list[ero_iter-1])
    init_seed, _ = sprout_core.get_ccomps_with_size_order(mask,init_segments)
    
    output_img_name = f'INTER_thre_{thresholds[0]}_ero_{n_iters}.tif'
    if save_every_iter:
        imwrite(os.path.join(output_folder,output_img_name), init_seed, 
            compression ='zlib')
            
    
    init_ids = [int(value) for value in np.unique(init_seed) if value != background]
    max_seed_id = int(np.max(init_ids))


    combine_seed = init_seed.copy()
    combine_seed = combine_seed.astype('uint16')

    output_dict = {"total_id": {0: len(np.unique(combine_seed))-1},
                   "split_id" : {0: {}},
                   "split_ori_id": {0: {}},
                   "split_ori_id_filtered":  {0: {}},
                   "split_prop":  {0: {}}, 
                   "cur_seed_name": {0: output_img_name},
                   "output_folder":output_folder
                   }

    ori_combine_ids_map = {}
    for value in init_ids :
        ori_combine_ids_map[value] = [value]
    
    no_consec_split_count = 0
    

    for idx_threshold, threshold in enumerate(thresholds[1:]):
        print(f"working on thre {threshold}")
        
        output_dict["split_id"][threshold] = {}
        output_dict["split_ori_id"][threshold] = {}
        output_dict["split_ori_id_filtered"][threshold] = {}
        output_dict["split_prop"][threshold] = {}
        
        
        if upper_thresholds is not None:
            assert threshold<upper_thresholds[1 + idx_threshold], "lower_threshold must be smaller than upper_threshold"
            mask = (img>=threshold) & (img<=upper_thresholds[1 + idx_threshold])
        else:
            mask = img>=threshold

        # mask = img>=threshold
        
        for ero_iter in range(1, n_iters+1):
            mask = sprout_core.erosion_binary_img_on_sub(mask, kernal_size = 1,
                                                         footprint=footprint_list[ero_iter-1])
        seed, _ = sprout_core.get_ccomps_with_size_order(mask,segments)
        seed = seed.astype('uint16')
        
        output_img_name = f'INTER_thre_{threshold}_ero_{n_iters}.tif'
        output_dict["cur_seed_name"][threshold] = output_img_name
        if save_every_iter:
            output_path = os.path.join(output_folder,output_img_name)
            print(f"\tSaving {output_path}")
            imwrite(output_path, seed, compression ='zlib')
        
        seed_ids = [int(value) for value in np.unique(seed) if value != background]
        combine_ids = [int(value) for value in np.unique(combine_seed) if value != background]
        
        
        has_split = False
        ## Comparing each ccomp from eroded seed
        ## to each ccomp from the original seed
        
        inter_log = {
            "inter_count":0,
            "inter_ids": np.array([]),
            "inter_props": np.array([])
        }
        
        for combine_id in combine_ids:
            ccomp_combine_seed = combine_seed == combine_id
            
            inter_log["inter_count"] = 0
            inter_log["inter_ids"] = np.array([])
            inter_log["inter_props"] = np.array([])
            
            sublists = [seed_ids[i::num_threads] for i in range(num_threads)]
             # Create a list to hold the threads
            threads = []
            for sublist in sublists:
                thread = threading.Thread(target=detect_inter, args=(ccomp_combine_seed,
                                                                     seed,
                                                                     sublist,
                                                                     inter_log,
                                                                     lock))
                threads.append(thread)
                thread.start()
                
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
        
        
            ## if there are any intersection between seed and the init seed
            if inter_log["inter_count"]>1:
                temp_inter_count = inter_log["inter_count"]
                temp_inter_ids = inter_log["inter_ids"]
                temp_inter_props = inter_log["inter_props"]
                
                
                # print(f'\t{combine_id} has been split to {temp_inter_count} parts. Ids are {temp_inter_ids}')
                # print(f"\tprops are: {temp_inter_props}")
                
                sum_inter_props = np.sum(temp_inter_props)
                # print(f"\tSplit prop is {sum_inter_props}")
                

                if not split_size_check(ccomp_combine_seed, split_size_limit):
                    print(f"no split, as {combine_id} only has {np.sum(ccomp_combine_seed) }")
                        

                split_condition =  (sum_inter_props>=min_split_sum_prop) and\
                    split_size_check(ccomp_combine_seed, split_size_limit) and \
                        split_convex_hull_check(ccomp_combine_seed, split_convex_hull_limit)

                if split_condition:
                    combine_seed[combine_seed == combine_id] =0
                    filtered_inter_ids = temp_inter_ids[temp_inter_props>min_split_prop]
                    
                
                    if len(filtered_inter_ids)>0:
                        has_split = True
                    
                    new_ids = []
                    for inter_id in filtered_inter_ids:
                        max_seed_id +=1
                        
                        combine_seed[seed == inter_id] = max_seed_id
                        # new_ids.append(max_seed_id)     
                        
                        new_ids.append(max_seed_id)
                        for key,value in ori_combine_ids_map.items():
                            if combine_id in value:
                                ori_combine_ids_map[key].append(max_seed_id)
                                break
                                # if len(value) <= max_splits:
                                    
                    output_dict["split_id"][threshold][combine_id] = new_ids
                    output_dict["split_ori_id"][threshold][combine_id] = inter_log["inter_ids"]
                    output_dict["split_ori_id_filtered"][threshold][combine_id] = filtered_inter_ids
                    output_dict["split_prop"][threshold][combine_id] = inter_log["inter_props"]
                
        
            output_dict["total_id"][threshold] = len(np.unique(combine_seed))-1
    
        if has_split:
            no_consec_split_count=0
        else:
            no_consec_split_count+=1
            
        if no_consec_split_count>=no_split_limit:
                print(f"detect non split for {no_consec_split_count}rounds")
                print(f"break loop at {threshold} threshold")
                break
        
        if save_merged_every_iter:
            combine_seed,_ = reorder_segmentation(combine_seed, min_size=min_size, sort_ids=sort)
            output_path = os.path.join(output_folder, "INTER_merged_" + output_name+f'thre_{threshold}.tif')
            
            print(f"\tSaving merged output:{output_path}")
            imwrite(output_path, combine_seed, 
                compression ='zlib')    
    
    # output_path = os.path.join(output_folder,output_name+'.tif')
    # print(f"\tSaving final output:{output_path}")
    # imwrite(output_path, combine_seed, 
    #     compression ='zlib')
    
    

        
    combine_seed,_ = reorder_segmentation(combine_seed, min_size=min_size, sort_ids=sort)
    if sort:
        output_path = os.path.join(output_folder,"FINAL_" + output_name+'_sorted.tif')
    else:
        output_path = os.path.join(output_folder,"FINAL_" + output_name+'.tif')
        
    print(f"\tSaving final output:{output_path}")
    imwrite(output_path, combine_seed, 
        compression ='zlib')

    config_core.save_config_with_output({
        "params": values_to_print},output_folder)
        

    pd.DataFrame(output_dict).to_csv(os.path.join(output_folder,
                                                  f"output_dict_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"),
                                     index=False)
    
             
    return combine_seed,ori_combine_ids_map, output_dict  

def run_make_adaptive_seed(file_path):
  
    _, extension = os.path.splitext(file_path)
    print(f"processing config the file {file_path}")
    if extension == '.yaml':
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
            optional_params = config_core.validate_input_yaml(config, config_core.input_val_make_adaptive_seed)
            

        # optional_params_2 = sprout_core.assign_optional_params(config, sprout_core.optional_params_default_seeds)
        
    # Checking if it's merged from erosion of threhsolds
    if isinstance(config['thresholds'], int):
        seed_merging_mode = "ERO"
    elif isinstance(config['thresholds'], list):
        if all(isinstance(t, int) for t in config['thresholds']):
            if len(config['thresholds']) == 1:
                seed_merging_mode = "ERO"
                config['thresholds'] = config['thresholds'][0]
                if optional_params['upper_thresholds'] is not None:
                    optional_params['upper_thresholds'] = optional_params['upper_thresholds'][0]
                
            elif len(config['thresholds']) > 1:
                seed_merging_mode = "THRE"
        else:
            raise ValueError("'thresholds' must be an int or a list of int(s).")
    
    
    # Track the overall start time
    overall_start_time = time.time()
    
    ## Use path then actual img data as the input        
    # img = imread(config['img_path'])
    # if optional_params['boundary_path'] is not None:
    #     boundary = imread(optional_params['boundary_path'])
    # else:
    #     boundary = None
    
    sub_folder = os.path.basename(config['img_path'])
    
    if seed_merging_mode == "ERO":
        seed ,ori_combine_ids_map , output_dict=  make_seeds_merged_mp(
                                    threshold=config['thresholds'],
                                    output_folder=config['output_folder'],
                                    n_iters=config['ero_iters'], 
                                    segments= config['segments'],
                                    num_threads = config['num_threads'],
                                    
                                    img_path = config['img_path'],
                                    boundary_path = optional_params['boundary_path'],                                            
                                    
                                    background = optional_params["background"],
                                    sort = optional_params["sort"],
                                    
                                    name_prefix = optional_params["name_prefix"],
                                    
                                    no_split_limit =optional_params["no_split_limit"],
                                    min_size=optional_params["min_size"],
                                    min_split_prop = optional_params["min_split_prop"],
                                    min_split_sum_prop = optional_params["min_split_sum_prop"],
                                    
                                    save_every_iter = optional_params["save_every_iter"],
                                    save_merged_every_iter = optional_params["save_merged_every_iter"],
                                    
                                    init_segments = optional_params["init_segments"],
                                    footprint = optional_params["footprints"],
                                    
                                    upper_threshold = optional_params["upper_thresholds"],
                                    split_size_limit= optional_params["split_size_limit"],
                                    split_convex_hull_limit = optional_params["split_convex_hull_limit"],
                                    
                                    sub_folder = sub_folder
                                        
                                    )
    
    # pd.DataFrame(ori_combine_ids_map).to_csv(os.path.join(output_folder, 'ori_combine_ids_map.csv'),index=False)
    
    elif seed_merging_mode=="THRE":
   
        seed ,ori_combine_ids_map , output_dict= make_seeds_merged_by_thres_mp(

                                   thresholds=config['thresholds'],
                                    output_folder=config['output_folder'],
                                    n_iters=config['ero_iters'], 
                                    segments= config['segments'],
                                    
                                    num_threads = config['num_threads'],
                                    
                                    img_path = config['img_path'],
                                    boundary_path = optional_params['boundary_path'],    
                                    
                                    background = optional_params["background"],
                                    sort = optional_params["sort"],
                                    
                                    name_prefix = optional_params["name_prefix"],
                                    
                                    no_split_limit =optional_params["no_split_limit"],
                                    min_size=optional_params["min_size"],
                                    min_split_prop = optional_params["min_split_prop"],
                                    min_split_sum_prop = optional_params["min_split_sum_prop"],
                                    
                                    save_every_iter = optional_params["save_every_iter"],
                                    save_merged_every_iter = optional_params["save_merged_every_iter"],
                                                                        
                                    init_segments = optional_params["init_segments"],
                                    footprint = optional_params["footprints"],
                                    
                                    upper_thresholds = optional_params["upper_thresholds"],
                                    split_size_limit= optional_params["split_size_limit"],
                                    split_convex_hull_limit = optional_params["split_convex_hull_limit"],
                                    
                                    sub_folder = sub_folder                
                                    )
                

    

    
    # Track the overall end time
    overall_end_time = time.time()

    # Output the total running time
    print(f"Total running time: {overall_end_time - overall_start_time:.2f} seconds")
        

    

if __name__ == "__main__":        
   
    # Get the file path from the first command-line argument or use the default
    file_path = sys.argv[1] if len(sys.argv) > 1 else './make_adaptive_seed.yaml'

    run_make_adaptive_seed(file_path=file_path)
  