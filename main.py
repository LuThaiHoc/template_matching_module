import cv2
from template_matching_sift_based import sift_flann_ransac_matching, is_convex_polygon
from ftp_connector import *
from database import Database, DatabaseConfig, AvtTask
import argparse
import json
import sys
from exit_code import *
from utils import logger
import time, glob

FTP_SERVER_OUTPUT_DIR = "/output/template_matching"
MODULE_SERVE_TASK_TYPE = 7 # the type of task that module is going to serve
# SHIP_DETECT_OUTPUT_DIR = "/data/RASTER_PREPR/output_ship_detect/"
SHIP_DETECT_OUTPUT_DIR = "/data/DETECTOR_OUTPUT/"
DOWNLAD_SHIP_DETECT_OUTPUT_DIR = "output_ship_detect/"
CHECK_WAITING_TASK_INTERVAL = 5 # check for waiting task every 5s

def delete_all_files_in_dir(directory):
    # Use glob to get all files in the directory
    files = glob.glob(os.path.join(directory, '*'))

    for file in files:
        try:
            if os.path.isfile(file):
                os.remove(file)  # Delete the file
                print(f"File '{file}' removed successfully")
        except OSError as e:
            print(f"Error: {e.strerror} - {file}")


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
        logger.error(f"File not found: {txt_path}")
        return None
    except ValueError:
        logger.error(f"Error reading coordinates from file: {txt_path}")
        return None

def create_json_from_paths(png_paths):
    """
    Create a JSON structure from a list of PNG paths.

    :param png_paths: List of PNG paths.
    :return: JSON structure as a list of dictionaries.
    """
    json_list = []
    
    for png_path, main_file in png_paths:
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
            "lb_path": txt_path,
            "at" : main_file
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

# Function to logger.debug running time
import threading
import time

def update_running_time(task_id, db : Database, stop_event):
    start_time = time.time()
    while not stop_event.is_set():
        elapsed_time = time.time() - start_time 
        # logger.debug(f"Running time {running_time}")
        if elapsed_time > 2: # only update running time > 2 in task_stat to avoid confilict with tast_stat=1 (finished) or task_stat = 0 (error)
            db.update_task(task_id, task_stat=round(elapsed_time, 0))
            logger.debug(f"Update running time to {round(elapsed_time, 0)}")
        else:
            db.update_task(task_id, task_stat=2)
        # TODO: check processing resource and update task ETA here
        
        time.sleep(0.5)  # Update every second
        
    logger.debug(f"Running time thread for task {task_id} stopped.")

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='SIFT Template Matching with FLANN RANSAC')
    
    
    # parser.add_argument('--avt_task_id', type=int, default=None,
    #                     help='Avt task id to process')
    parser.add_argument('--config_file', type=str, default=None,
                        help='Config file for database and ftp server config')

    args, unknown = parser.parse_known_args()
    # avt_task_id = args.avt_task_id
    config_json_path = args.config_file
    
    
    if config_json_path is None:
        if getattr(sys, 'frozen', False):
            # Running as bundled executable
            current_script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        else:
            # Running as script
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
        config_json_path = os.path.join(current_script_dir, 'config.json')
        
    logger.debug(f"Working with config file: {config_json_path}")
    
    db_config = DatabaseConfig().read_from_json(config_json_path)
    db = Database(db_config.host, db_config.port, db_config.user, db_config.password, db_config.database)
    if not db.connected:
        # Let the WTM (Worker Task Manager) know that this module cannot connect to the database
        # (this case can happen when module and WTM run on difference machines)
        # Solve: exit module with code and get it in WTM
        logger.debug("Cannot connect to the database")
        sys.exit(EXIT_CANNOT_CONNECT_TO_DATABASE)
    else:
        logger.debug("Succeed connect to the database!")
        
    # check the database every 5s for finding waiting task
    while True:
        # get the waiting task
        task : AvtTask = db.get_first_waiting_task_by_type(MODULE_SERVE_TASK_TYPE)
        if task is None:
            logger.debug("No waiting task, check again after 5s")
            time.sleep(CHECK_WAITING_TASK_INTERVAL)
            continue
        
        # check task id ref to know whether there are a running task
        if task.task_id_ref is not None and task.task_id_ref > 0:
            # if there is an running task
            ref_task = db.get_task_by_id(task.task_id_ref)
            if ref_task is not None:
                # if this task is running, wait for it end then server the current first task in waiting queue
                if ref_task.task_stat > 1: # 0 for error, 1 for finished, > 1 for running
                    logger.debug(f"Task reference (id {ref_task.id}) of task {task.id} is running, waiting for this task finished!")
                    time.sleep(5)
                    continue # the program will re-get this task after 5s (by the code in while loop)
        
        logger.debug(f"Serving task with id: {task.id}")
        
        # update running time in thread
        # just start thread here and skip some process above because it dont take times to excute
        stop_event = threading.Event()
        running_time_thread = threading.Thread(target=update_running_time, args=(task.id, db, stop_event))
        running_time_thread.daemon = True  # Set as daemon so it won't block program exit
        running_time_thread.start()
            
        # Convert JSON string to dictionary
        if task.task_param is None:
            logger.debug(f"Input params of task {task.id} is not valid - No data")
            stop_event.set()
            running_time_thread.join()
            db.update_task(id=task.id, task_stat=0, task_message=exit_code_messages[EXIT_INVALID_MODULE_PARAMETERS])
            continue

        task_param_dict = json.loads(task.task_param)
        

        # Access the data as a dictionary
        # main_image_file = task_param_dict.get("main_image_file", "")
        template_image_file = task_param_dict.get("template_image_file", "")
        main_image_files = task_param_dict.get("main_image_files", [])
        
        if template_image_file == "":
            logger.debug(f"Input params of task {task.id} is not valid - No template image file")
            stop_event.set()
            running_time_thread.join()
            db.update_task(id=task.id, task_stat=0, task_message=exit_code_messages[EXIT_INVALID_MODULE_PARAMETERS])
            continue
        
        if len(main_image_files) == 0:
            logger.debug(f"Input params of task {task.id} is not valid - No main image file")
            stop_event.set()
            running_time_thread.join()
            db.update_task(id=task.id, task_stat=0, task_message=exit_code_messages[EXIT_INVALID_MODULE_PARAMETERS])
            continue
        
        
        logger.debug(f"Finding object by image: {template_image_file}")
        output_ship_detect_of_main_image_files = [(f"{SHIP_DETECT_OUTPUT_DIR}/{os.path.splitext(os.path.basename(file))[0]}", file) for file in main_image_files]
        results = []
        
        ftp_config = FtpConfig().read_from_json(config_json_path)
        downloaded_template_image_file = ftp_download(ftp_server=ftp_config.host, ftp_port=ftp_config.port, username=ftp_config.user, password=ftp_config.password, file_path=template_image_file)
        logger.debug(f"Template image file downloaded at: {downloaded_template_image_file}")
        
        if downloaded_template_image_file is None:
            logger.error("Cannot download file from ftp server!")
            db.update_task(task_id=task.id, task_stat=0, task_message=exit_code_messages[EXIT_FTP_DOWNLOAD_ERROR])
            stop_event.set()
            running_time_thread.join()
            continue
        
        for output_ship_detect_dir, main_file in output_ship_detect_of_main_image_files:
            logger.debug(f"Downloading all output ship detect in {output_ship_detect_dir}")
            download_local_dir = os.path.join(DOWNLAD_SHIP_DETECT_OUTPUT_DIR,  os.path.basename(os.path.normpath(output_ship_detect_dir)))
            
            delete_all_files_in_dir(download_local_dir)
            
            downloaded_founded_image_and_labels = ftp_download_all_files(ftp_server=ftp_config.host,
                                                                            ftp_port=ftp_config.port,
                                                                            username=ftp_config.user,
                                                                            password=ftp_config.password,
                                                                            remote_dir=output_ship_detect_dir,
                                                                            local_dir=download_local_dir,
                                                                            force_download=True
                                                                        )
            if len(downloaded_founded_image_and_labels) == 0:
                logger.warning(f"No ship detect in {output_ship_detect_dir}, maybe no ship found or the main image was not processed by ship detector model")          
            
            for item in downloaded_founded_image_and_labels:
                if item.endswith(".png"):
                    logger.debug(f"Checking ship: {item}")
                    result_image, crop, polygon = sift_flann_ransac_matching(item, downloaded_template_image_file)
                    if polygon is None: 
                        continue
                    
                    # if True:
                    if is_convex_polygon(polygon):
                        logger.debug(f"Found match: {item}")
                        # cv2.imshow("Got match", result_image)
                        # cv2.waitKey(0)
                        results.append((item, main_file))

                
        logger.debug(f"Got list matching ship: {results}")
        json_data = create_json_from_paths(results)
        json_output_str = json.dumps(json_data).replace(DOWNLAD_SHIP_DETECT_OUTPUT_DIR, SHIP_DETECT_OUTPUT_DIR)
        json_output_str.replace("\\","/")
        
        logger.debug(f"Return result json: {json_output_str}")
        
        # stop update thread
        stop_event.set()
        running_time_thread.join()
        
        # update finished result to database
        db.update_task(task_id=task.id, task_stat=1, task_output=json_output_str, task_message=exit_code_messages[EXIT_FINISHED])
        
        logger.debug("Process finished")
        continue
    
        
    
# python main.py --avt_task_id 22