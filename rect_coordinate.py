import cv2
import numpy as np
from imutils import perspective

def get_coordinate(file):
    image = cv2.imread(file)
    img_size = image.shape

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    canny = cv2.Canny(blurred, 120, 255, 1)

    # Find contours
    cnts = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

    areas = np.array([])

    for cc in range(len(cnts)):
        # if len(cnts[cc]) < 6:
            # area = cv2.contourArea(cnts[cc])
        x, y, w, h = cv2.boundingRect(cnts[cc])
        area = w*h
        areas = np.append(areas, area)


    # Iterate thorugh contours and draw rectangles around contours

    rect = cv2.minAreaRect(cnts[np.argmax(areas)])
    box = np.int0(cv2.boxPoints(rect))

    # order the points in the contour such that they appear
    # in top-left, top-right, bottom-right, and bottom-left
    # order, then draw the outline of the rotated bounding
    # box
    return perspective.order_points(box), [img_size[1], img_size[0]]
