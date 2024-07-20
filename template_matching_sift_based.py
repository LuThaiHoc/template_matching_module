import cv2
import numpy as np
from utils import polygon_to_latlon

def sift_flann_ransac_matching(main_image_path, template_image_path, lowes_ratio=0.75, min_match_count=5,
                               flann_index_algorithm=1, flann_trees=5, flann_search_checks=50):
    """
    Perform SIFT feature matching with FLANN and RANSAC.

    Parameters:
    - main_image_path (str): Path to the main image.
    - template_image_path (str): Path to the template image.
    - lowes_ratio (float): Threshold for Lowe's ratio test to filter good matches (default: 0.75).
    - min_match_count (int): Minimum number of good matches required to proceed with homography (default: 5).
    - flann_index_algorithm (int): Algorithm to be used for the FLANN index (default: 1).
    - flann_trees (int): Number of trees in the FLANN index (default: 5).
    - flann_search_checks (int): Number of checks during FLANN search (default: 50).

    Returns:
    - result_image (numpy.ndarray): Image with matches drawn.
    - cropped_result (numpy.ndarray): Cropped region of the main image based on the homography.
    - polygon (list): List of points (x, y) of the matched region.
    """
    # Load the images
    main_image = cv2.imread(main_image_path)
    template_image = cv2.imread(template_image_path)
    main_gray = cv2.cvtColor(main_image, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)

    # Initialize SIFT detector
    sift = cv2.SIFT_create()

    # Detect keypoints and descriptors
    keypoints_main, descriptors_main = sift.detectAndCompute(main_gray, None)
    keypoints_template, descriptors_template = sift.detectAndCompute(template_gray, None)

    # Match descriptors using FLANN matcher
    index_params = dict(algorithm=flann_index_algorithm, trees=flann_trees)
    search_params = dict(checks=flann_search_checks)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(descriptors_template, descriptors_main, k=2)

    # Apply Lowe's ratio test to find good matches
    good_matches = []
    for m, n in matches:
        if m.distance < lowes_ratio * n.distance:
            good_matches.append(m)

    cropped_result = None
    polygon = None
    if len(good_matches) >= min_match_count:
        src_pts = np.float32([keypoints_template[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([keypoints_main[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Find homography matrix using RANSAC
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        matches_mask = mask.ravel().tolist()

        h, w = template_image.shape[:2]
        pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, M)

        main_image = cv2.polylines(main_image, [np.int32(dst)], True, 255, 3, cv2.LINE_AA)

        # Get the polygon coordinates
        polygon = np.int32(dst)
        # Get the bounding box coordinates
        min_x, min_y = np.int32(dst).min(axis=0).ravel()
        max_x, max_y = np.int32(dst).max(axis=0).ravel()

        # Crop the result from the main image
        cropped_result = main_image[min_y:max_y, min_x:max_x]

    else:
        matches_mask = None

    # Draw matches
    draw_params = dict(matchColor=(0, 255, 0), singlePointColor=None, matchesMask=matches_mask, flags=2)
    result_image = cv2.drawMatches(template_image, keypoints_template, main_image, keypoints_main, good_matches, None, **draw_params)

    return result_image, cropped_result, polygon


if __name__ == "__main__":
    # main_image_path = '../data/template_matching/main/quang_ninh_1m.tif'
    # template_image_path = '../data/template_matching/template/05_resized.png'

    # main_image_path = 'imgs\map.tif'
    # template_image_path = 'imgs\\04.png'

    main_image_path = 'C:\\temp\data/template_matching\hvkt_gmap_k05m.tif'
    template_image_path = 'imgs/cap1.png'

    import time
    t = time.time()
    result_image, cropped_result, polygon = sift_flann_ransac_matching(main_image_path, template_image_path)
    bbox = polygon_to_latlon(main_image_path, polygon)
    print(bbox)

    # lat, lon = pixel_to_latlon(main_image_path, min_x, min_y)
    # print(f"x,y: {min_x},{min_y} -- lat,long: {lat}-{lon}")

    print("Time excuted: ",time.time() - t)
    result_image = cv2.resize(result_image, (1280,720))
    # cv2.imshow('Template to find', result_image)
    cv2.imshow('SIFT Template Matching with RANSAC', result_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# result: pretty good, can find object with clear features