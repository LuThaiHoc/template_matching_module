import cv2
from template_matching_sift_based import sift_flann_ransac_matching, is_convex_polygon

img = "/media/hoc/WORK/remote/AnhPhuong/SAT/Project/SAT_Modules/template_matching_deployment/output_ship_detect/quang_ninh_1m/000.png"


print("Hello")
result_image, crop, polygon = sift_flann_ransac_matching(img, "/tmp/data/TEMPLATE/07_resized.png")
if polygon is not None: 
    cv2.imshow("Got match", result_image)
    cv2.waitKey(0)
    print(polygon)
    if is_convex_polygon(polygon):
        print("Found: ", img)
        cv2.imshow("Got match1", result_image)
        cv2.waitKey(0)
else:
    print("Not detect")