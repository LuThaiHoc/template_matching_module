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

FTP_SERVER_OUTPUT_DIR = "/output/template_matching"
MODULE_SERVE_TASK_TYPE = 7 # the type of task that module is going to serve
SHIP_DETECT_OUTPUT_DIR = "/data/RASTER_PREPR/output_ship_detect"
DOWNLAD_SHIP_DETECT_OUTPUT_DIR = "output_ship_detect/"

def save_and_upload_images(result_image, cropped_result, avt_task_id, ftp_config: FtpConfig, remote_dir):
    """
    Save result images locally and upload them to the FTP server.

    :param result_image: Image with matches drawn.
    :param cropped_result: Cropped region of the main image.
    :param avt_task_id: ID to use in the filenames.
    :param ftp_config: Ftp config object data.
    :param remote_dir: Upload dir in FTP server
    """
    # Ensure the output directory exists
    if os.name == 'nt':  # Check if the OS is Windows
        output_dir = "C:\\temp\\output\\"
    else:
        output_dir = "/tmp/output/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    result_image_path = os.path.join(output_dir, f"{avt_task_id}_result_image.png")
    cropped_result_path = os.path.join(output_dir, f"{avt_task_id}_cropped_result.png")

    # Save the images locally
    cv2.imwrite(result_image_path, result_image)
    if cropped_result is not None:
        cv2.imwrite(cropped_result_path, cropped_result)
        
    uploaded_result_image_path = None
    uploaded_result_croped_path = None

    # Upload the images to the FTP server
    uploaded_result_image_path = ftp_upload(ftp_server=ftp_config.host, ftp_port=ftp_config.port, username=ftp_config.user, password=ftp_config.password,
               local_file_path=result_image_path, remote_directory=remote_dir)

    if cropped_result is not None:
        uploaded_result_croped_path = ftp_upload(ftp_server=ftp_config.host, ftp_port=ftp_config.port, username=ftp_config.user, password=ftp_config.password,
                   local_file_path=cropped_result_path, remote_directory=remote_dir)
    
    return uploaded_result_image_path, uploaded_result_croped_path

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
            "id": file_id.zfill(3),
            "path": png_path,
            "coords": coords,
            "lb_path": txt_path
        }
        
        json_list.append(json_entry)
    
    return json_list

def create_output_json(result_image_file, cropped_image_file, bbox):
    """
    Create a JSON string with the specified format.

    :param result_image_file: Path to the result image in the FTP server.
    :param cropped_image_file: Path to the cropped image in the FTP server.
    :param bbox: List of points (latitude, longitude) of the bounding box or None.
    :return: JSON string.
    """
    output_dict = {
        "result_image_file": result_image_file if result_image_file is not None else "",
        "cropped_image_file": cropped_image_file if cropped_image_file is not None else "",
        "location": bbox if bbox is not None else []
    }

    return json.dumps(output_dict, separators=(',', ':'))

def create_output_location_json(bbox):
    """
    Create a JSON string with the specified format.

    :param bbox: List of points (latitude, longitude) of the bounding box or None.
    :return: JSON string.
    """
    output_dict = {
        "location": bbox if bbox is not None else []
    }

    return json.dumps(output_dict, separators=(',', ':'))

# Function to print running time
import threading
import time

def update_running_time(task_id, db : Database, stop_event):
    start_time = time.time()
    while not stop_event.is_set():
        elapsed_time = time.time() - start_time 
        # print(f"Running time {running_time}")
        if elapsed_time > 2: # only update running time > 2 in task_stat to avoid confilict with tast_stat=1 (finished) or task_stat = 0 (error)
            db.update_task(task_id, task_stat=round(elapsed_time, 1))
        else:
            db.update_task(task_id, task_stat=round(elapsed_time, 2))
        # TODO: check processing resource and update task ETA here
        
        time.sleep(0.5)  # Update every second
        
    print(f"Running time thread for task {task_id} stopped.")

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='SIFT Template Matching with FLANN RANSAC')
    parser.add_argument('--avt_task_id', type=int, default=None,
                        help='Avt task id to process')
    parser.add_argument('--config_file', type=str, default=None,
                        help='Config file for database and ftp server config')

    args, unknown = parser.parse_known_args()
    avt_task_id = args.avt_task_id
    config_json_path = args.config_file
    
    
    if config_json_path is None:
        if getattr(sys, 'frozen', False):
            # Running as bundled executable
            current_script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        else:
            # Running as script
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
        config_json_path = os.path.join(current_script_dir, 'config.json')
        
    print(f"Working with config file: {config_json_path}")
    
    db_config = DatabaseConfig().read_from_json(config_json_path)
    db = Database(db_config.host, db_config.port, db_config.user, db_config.password, db_config.database)
    if not db.connected:
        # Let the WTM (Worker Task Manager) know that this module cannot connect to the database
        # (this case can happen when module and WTM run on difference machines)
        # Solve: exit module with code and get it in WTM
        print("Cannot connect to the database")
        sys.exit(EXIT_CANNOT_CONNECT_TO_DATABASE)
    else:
        print("Succeed connect to the database!")
    
    # update running time in thread
    # just start thread here and skip some process above because it dont take times to excute
    stop_event = threading.Event()
    running_time_thread = threading.Thread(target=update_running_time, args=(avt_task_id, db, stop_event))
    running_time_thread.daemon = True  # Set as daemon so it won't block program exit
    running_time_thread.start()
        
    task = None
    if avt_task_id is None:
        # try to get task by module type
        task = db.get_waiting_task_by_type(MODULE_SERVE_TASK_TYPE)
    else:
        task = db.get_task_by_id(avt_task_id)
    
    if task is None:
        print("Cannot get task by ID")
        sys.exit(EXIT_INVALID_INPUT_AVT_TASK_ID)
    else:
        avt_task_id = task.id

        
    # Convert JSON string to dictionary
    if task.task_param is None:
        print("Input params not valid - No data")
        db.update_task(id=avt_task_id, task_stat=0, task_message=exit_code_messages[EXIT_INVALID_MODULE_PARAMETERS])
        sys.exit(EXIT_INVALID_MODULE_PARAMETERS)

    task_param_dict = json.loads(task.task_param)
    

    # Access the data as a dictionary
    # main_image_file = task_param_dict.get("main_image_file", "")
    template_image_file = task_param_dict.get("template_image_file", "")
    
    if template_image_file == "":
        print("Input params not valid")
        db.update_task(task_id=avt_task_id, task_stat=0, task_message=exit_code_messages[EXIT_INVALID_MODULE_PARAMETERS])
        sys.exit(EXIT_INVALID_MODULE_PARAMETERS)
    
    print("Template image file:", template_image_file)

    ftp_config = FtpConfig().read_from_json(config_json_path)
    downloaded_template_image_file = ftp_download(ftp_server=ftp_config.host, ftp_port=ftp_config.port, username=ftp_config.user, password=ftp_config.password, file_path=template_image_file)
    
    if downloaded_template_image_file is None:
        print("Cannot download file from ftp server!")
        db.update_task(task_id=avt_task_id, task_stat=0, task_message=exit_code_messages[EXIT_FTP_DOWNLOAD_ERROR])
        sys.exit(EXIT_FTP_DOWNLOAD_ERROR)
    
    downloaded_founded_image_and_labels = ftp_download_all_files(ftp_server=ftp_config.host,
                                                                    ftp_port=ftp_config.port,
                                                                    username=ftp_config.user,
                                                                    password=ftp_config.password,
                                                                    remote_dir=SHIP_DETECT_OUTPUT_DIR,
                                                                    local_dir=DOWNLAD_SHIP_DETECT_OUTPUT_DIR,
                                                                    force_download=True
                                                                )
    
    results = []
    for item in downloaded_founded_image_and_labels:
        if item.endswith(".png"):
            print("Checking ship: ", item)
            result_image, crop, polygon = sift_flann_ransac_matching(item, downloaded_template_image_file)
            if polygon is None: 
                continue
            if is_convex_polygon(polygon):
                # print("Found: ", item)
                # cv2.imshow("Got match", result_image)
                # cv2.waitKey(0)
                results.append(item)

        
    print("Got list matching ship: ", results)
    json_data = create_json_from_paths(results)
    json_output_str = json.dumps(json_data).replace(DOWNLAD_SHIP_DETECT_OUTPUT_DIR, SHIP_DETECT_OUTPUT_DIR)
    json_output_str.replace("\\","/")
    
    # stop update thread
    stop_event.set()
    running_time_thread.join()
    
    # update finished result to database
    db.update_task(task_id=avt_task_id, task_stat=1, task_output=json_output_str, task_message=exit_code_messages[EXIT_FINISHED])
    
    print("Process finished")
    sys.exit(EXIT_FINISHED)
    
        
    
# python main.py --avt_task_id 22