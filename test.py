import cv2
from template_matching_sift_based import sift_flann_ransac_matching, is_convex_polygon
from ftp_connector import *
from database import Database, DatabaseConfig
import argparse
import json
import sys
from exit_code import *
from utils import polygon_to_latlon
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


SHIP_DETECT_OUTPUT_DIR = "/data/RASTER_PREPR/output_ship_detect/"
DOWNLAD_SHIP_DETECT_OUTPUT_DIR = "output_ship_detect/"
# ftp_config = FtpConfig().read_from_json('config.json')
# downloaded_founded_image_and_labels = ftp_download_all_files(ftp_server=ftp_config.host,
#                                                                     ftp_port=ftp_config.port,
#                                                                     username=ftp_config.user,
#                                                                     password=ftp_config.password,
#                                                                     remote_dir=SHIP_DETECT_OUTPUT_DIR,
#                                                                     local_dir=DOWNLAD_SHIP_DETECT_OUTPUT_DIR,
#                                                                     force_download=True
#                                                                 )

downloaded_founded_image_and_labels = list_all_files(DOWNLAD_SHIP_DETECT_OUTPUT_DIR)
downloaded_template_image_file = 'imgs/01.png'

results = []
for item in downloaded_founded_image_and_labels:
    if item.endswith(".png"):
        print("Checking ship: ", item)
        result_image, crop, polygon = sift_flann_ransac_matching(item, downloaded_template_image_file)
        if polygon is None: 
            continue
        if is_convex_polygon(polygon):
            print("Found: ", item)
            cv2.imshow("Got match", result_image)
            cv2.waitKey(0)
            results.append(item)


# # List of PNG paths
# png_paths = [
#     'output_ship_detect/tay_ho_1m/001.png',
#     'output_ship_detect/tay_ho_1m/002.png'
# ]

# Create JSON structure
json_data = create_json_from_paths(results)

# Output JSON data
print(json.dumps(json_data).replace(DOWNLAD_SHIP_DETECT_OUTPUT_DIR, SHIP_DETECT_OUTPUT_DIR))

# for item in results:
#     item.replace(DOWNLAD_SHIP_DETECT_OUTPUT_DIR, SHIP_DETECT_OUTPUT_DIR)
