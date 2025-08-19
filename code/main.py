import json
import re

import cv2
import numpy as np
from pyrtz2.src.components.image import process_image

image_file = "data/cell25meas0000.tif"
labels = ["cell", "meas"]
im_annotations_file = "data/DN1-rapid_im_annotations.json"

with open(im_annotations_file, "r") as f:
    im_annotations = json.load(f)

image = cv2.imread(image_file)

filename = image_file.split("/")[-1]  # Get 'cell01meas0000.tif'
match = re.match(r"cell(\d+)meas(\d+)\.tif", filename)
if match:
    keys = (match.group(1), match.group(2))
else:
    print("Filename format not recognized.")


def return_full_key(keys):
    for im_key in im_annotations.keys():
        if keys[0] == eval(im_key)[0]:
            return im_key
    return None


full_key = return_full_key(keys)
im_annotation = im_annotations[full_key]

image_label = process_image(image, im_annotation)  # type: ignore

# plot the contours with red color over the image
for contour in image_label:
    contour_np = np.array(contour, dtype=np.int32)
    cv2.drawContours(image, [contour_np], -1, (0, 0, 255), 1)

mask = np.zeros(image.shape[:2], dtype=np.uint8)
for contour in image_label:
    contour_np = np.array(contour, dtype=np.int32)
    cv2.drawContours(mask, [contour_np], -1, 255, -1)  # Fill the contour

cv2.imshow("Mask", mask)

cv2.imshow("Image", image)
cv2.waitKey(0)
cv2.destroyAllWindows()
