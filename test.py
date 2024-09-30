import cv2
from template_matching_sift_based import sift_flann_ransac_matching, is_convex_polygon
from ftp_connector import *
from database import Database, DatabaseConfig
import argparse
import json
import sys
from exit_code import *
import string

import json
import os

def read_coords_from_file(txt_path):
    """
    Read coordinates from a text file.

    :param txt_path: Path to the .txt file.
    :return: List of coordinates read from the file.
    """
    try:
        with open(txt_path, 'r') as file:
            coords = [float(value) for value in file.read().strip().split()]
        return coords
    except FileNotFoundError:
        print(f"File not found: {txt_path}")
        return None
    except ValueError:
        print(f"Error reading coordinates from file: {txt_path}")
        return None

def create_json_from_paths(png_paths):
    """
    Create a JSON structure from a list of PNG paths.

    :param png_paths: List of PNG paths.
    :return: JSON structure as a list of dictionaries.
    """
    json_list = []
    
    for png_path in png_paths:
        # Extract the file ID and create corresponding paths
        file_id = os.path.basename(png_path).split('.')[0]
        txt_path = png_path.replace('.png', '.txt')
        
        # Read coordinates from the corresponding .txt file
        coords = read_coords_from_file(txt_path)
        if coords is None:
            continue
        
        # Create the JSON entry
        json_entry = {
            "id": file_id.zfill(3),  # Assuming you want zero-padded IDs
            "path": png_path,
            "coords": coords,
            "lb_path": txt_path
        }
        
        json_list.append(json_entry)
    
    return json_list

def list_all_files(directory):
    """
    List all files in the given directory and its subdirectories.

    :param directory: Path to the directory.
    :return: List of file paths.
    """
    file_list = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_list.append(os.path.join(root, file))
    
    return file_list


# SHIP_DETECT_OUTPUT_DIR = "/data/RASTER_PREPR/output_ship_detect/"
# DOWNLAD_SHIP_DETECT_OUTPUT_DIR = "output_ship_detect/quang_ninh_1m"
DOWNLAD_SHIP_DETECT_OUTPUT_DIR = "output_ship_detect/"

ftp_config = FtpConfig().read_from_json('config.json')

all_dirs = []

for find_dir in ftp_config.find_dirs:
    chid_dirs = ftp_get_all_child_dirs(
        ftp_server=ftp_config.host,
        ftp_port=ftp_config.port,
        username=ftp_config.user,
        password=ftp_config.password,
        remote_dir=find_dir
    )
    chid_dirs.remove(find_dir) # dont find in parent dir, just find in sub-dir
    all_dirs += chid_dirs
    

i = 0

downloaded_template_image_file = './template.png'

results = []
for searching_dir in all_dirs:
    download_local_dir = os.path.join(DOWNLAD_SHIP_DETECT_OUTPUT_DIR,  os.path.basename(os.path.normpath(searching_dir)))
    # print(download_local_dir, searching_dir)

    downloaded_founded_image_and_labels = ftp_download_all_files(ftp_server=ftp_config.host,
                                                                            ftp_port=ftp_config.port,
                                                                            username=ftp_config.user,
                                                                            password=ftp_config.password,
                                                                            remote_dir=searching_dir,
                                                                            local_dir=download_local_dir,
                                                                            force_download=False
                                                                        )
    for item in downloaded_founded_image_and_labels:
        if item.endswith(".png") or item.endswith(".jpg") or item.endswith(".jpeg"):
            logger.debug(f"Checking ship: {item}")
            result_image, crop, polygon = sift_flann_ransac_matching(item, downloaded_template_image_file)
            if polygon is None: 
                continue
            
            # if True:
            if is_convex_polygon(polygon):
                logger.debug(f"Found match: {item}")
                # cv2.imshow("Got match", result_image)
                # cv2.waitKey(0)
                results.append((item, searching_dir))
    
    # print(downloaded_founded_image_and_labels)
    # i += 1
    # if i >= 2: 
    #     break
    
logger.debug(f"Result: {results}")

# downloaded_founded_image_and_labels = list_all_files(DOWNLAD_SHIP_DETECT_OUTPUT_DIR)
# # downloaded_template_image_file = '/tmp/data/TEMPLATE/07_resized.png'
# downloaded_template_image_file = '/media/hoc/WORK/remote/AnhPhuong/SAT/Project/SAT_Modules/data/template_matching/template/h7_camera.png'


# results = []
# for item in downloaded_founded_image_and_labels:
#     if item.endswith(".png"):
#         # print("Checking ship: ", item)
#         result_image, crop, polygon = sift_flann_ransac_matching(item, downloaded_template_image_file)
#         if polygon is None: 
#             continue
        
#         print("Found: ", item)
#         cv2.imshow("Matching result", result_image)
#         cv2.waitKey(50)
#         if is_convex_polygon(polygon):
#             print("Polygon convex: ", item)
#             # cv2.imshow("Got match", result_image)
#             # cv2.waitKey(0)
#             results.append(item)
#         else:
#             print("Polygon not convex")


# # # List of PNG paths
# # png_paths = [
# #     'output_ship_detect/tay_ho_1m/001.png',
# #     'output_ship_detect/tay_ho_1m/002.png'
# # ]

# print(results)

# # Create JSON structure
# json_data = create_json_from_paths(results)

# # Output JSON data
# # print(json.dumps(json_data).replace(DOWNLAD_SHIP_DETECT_OUTPUT_DIR, SHIP_DETECT_OUTPUT_DIR))

# # for item in results:
# #     item.replace(DOWNLAD_SHIP_DETECT_OUTPUT_DIR, SHIP_DETECT_OUTPUT_DIR)


