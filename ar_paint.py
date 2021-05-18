#! /usr/bin/python3

import argparse
import copy
import json
import numpy as np
import cv2
import datetime
import math
import warnings

from colorama import Fore


# ---------------------------
# help context and input args
# ---------------------------


def parse_arguments():
    parser = argparse.ArgumentParser(description=' With this program, you will draw with a color object',
                                     epilog="And now have fun, be a disciple of Dali!")

    parser.add_argument('-j', '--json', help="Gives the path way to the file with the color specs. of the pointer",
                        action="store", default='limits.json')

    parser.add_argument('-usp', '--use_shake_prevention', help='Run the shake prevention code.',
                        action="store_true", default=False)
    parser.add_argument('-ucm', '--use_canvas_mode', help='Instead of painting in a white screen the user'
                                                          ' paint in the images coming from the camera.',
                        action="store_true", default=False)

    return parser.parse_args()


def create_canvas(ucm_status, capture):
    _, camera_image = capture.read()
    width, height = camera_image.shape[:2]
    canvas_image = np.ones((width, height, 3), np.uint8) * 255

    return canvas_image


# Distance function
def distance(xi, xii, yi, yii):
    if xi >= xii:
        a = xi - xii
    else:
        a = xii - xi

    if xi >= xii:
        b = yi - yii
    else:
        b = yii - yi

    sq1 = a*a
    sq2 = b*b
    return math.sqrt(sq1 + sq2)


def main():
    # --------------------------------------------------------------------
    # -------------------------initialization-----------------------------
    # --------------------------------------------------------------------

    # read arguments from user

    args = parse_arguments()
    myFile = args.json
    usp_status = args.use_shake_prevention
    ucm_status = args.use_canvas_mode
    color = (0, 0, 0)
    thickness = 5
    counter = 1
    # disable all warnings
    warnings.filterwarnings("ignore")

    # read the json in order to extract the dict with de segmentation limits
    try:
        json_file = open(myFile)
    except:
        print(Fore.RED + 'Please add the path of a json file with the segmentation limits' + Fore.RESET)
        print('Type "./ar_paint.py -h" for instructions')
        return

    limits = json.load(json_file)

    # camera's initialization
    camera_window = "Images from Camera"
    cv2.namedWindow(camera_window)
    segmentation_window = "Segmentation Image"
    cv2.namedWindow(segmentation_window)
    painting_object_window = "Painting Object"
    cv2.namedWindow(painting_object_window)
    capture = cv2.VideoCapture(0)

    # connectivity between pixels
    connectivity = 4

    # creation of screen to paint, could be white screen or the camera's image itself
    painting_canvas_window = "Painting Canvas"
    cv2.namedWindow(painting_canvas_window)
    canvas_image = create_canvas(ucm_status, capture)

    mask = np.zeros((canvas_image.shape[0], canvas_image.shape[1], 3), np.uint8).astype(np.bool)

    first_point = True
    old_centroid_coord = (0, 0)

    # --------------------------------------------------------------------
    # ---------------------Continuous operation---------------------------
    # --------------------------------------------------------------------
    while True:
        # acquisition of image from camera
        _, camera_image = capture.read()
        camera_image_ucm = copy.deepcopy(camera_image)


        # segmentation of image from camera using the segmentation limits from json file
        segmentation_image = cv2.inRange(camera_image, (limits['B']['min'], limits['G']['min'], limits['R']['min']),
                                         (limits['B']['max'], limits['G']['max'], limits['R']['max']))

        cv2.imshow(segmentation_window, segmentation_image)

        # process de segmentation image in order to show the bigger object, and then predicting if that object is
        # really a object or not

        output = cv2.connectedComponentsWithStats(segmentation_image, connectivity, cv2.CV_32S)

        num_labels = output[0]  # integer with the number of object in the image

        labels = output[1]  # in labels we have an image, and each element has a value equivalent to its label

        stats = output[2]  # in stats we have all data for each object

        centroids = output[3]  # in centroids we have all centroids coordinates for each object

        # finding the object with bigger area

        drawing = True
        maximum_area = 0
        object_index = 1

        # if num_labels == 1 means that there is no object, so we cannot paint!
        if num_labels == 1:
            drawing = False

        for i in range(1, num_labels):

            object_area = stats[i, cv2.CC_STAT_AREA]

            if object_area > maximum_area:
                maximum_area = object_area
                object_index = i

        # if maximum_area <500 the object is too small, so its possible that it is not the phone but noise instead
        if maximum_area < 1000:
            drawing = False

        # extracting biggest object from segmentation limits

        biggest_object = (labels == object_index)
        biggest_object = biggest_object.astype(np.uint8) * 255
        cv2.imshow(painting_object_window, biggest_object)

        # configuration by key's

        key = cv2.waitKey(1)
        if key == ord("r"):
            color = (0, 0, 255)
        elif key == ord("g"):
            color = (0, 255, 0)
        elif key == ord("b"):
            color = (255, 0, 0)
        elif key == ord("n"):
            color = (0, 0, 0)
        elif key == ord("e"):
            color = (255, 255, 255)
        elif key == ord("c"):  # clear canvas
            color = (0, 0, 0)
            canvas_image = create_canvas(ucm_status, capture)
            mask = np.zeros((canvas_image.shape[0], canvas_image.shape[1], 3), np.uint8).astype(np.bool)
        elif key == ord("+"):
            thickness += 1
        elif key == ord("-"):
            if thickness == 1:
                thickness = 1
            else:
                thickness -= 1
        elif key == ord("w"):
            file_name = str(datetime.datetime.now()) + 'canvas.png'
            if ucm_status:
                camera_image_ucm[mask] = canvas_image[mask]
                cv2.imwrite(file_name, camera_image_ucm)
            else:
                cv2.imwrite(file_name, canvas_image)
            print(Fore.GREEN + 'Image saved successfully' + Fore.RESET)
            counter += 1

        elif key == ord("q"):
            break

        # calculating centroid from biggest image (only if drawing is true)

        if drawing:

            centroid_coord = centroids[object_index, :].astype(np.uint)
            centroid_coord = tuple(centroid_coord)

            if first_point:
                old_centroid_coord = centroid_coord
                first_point = False

            # painting the centroid in camera's image and biggest_object
            cv2.circle(biggest_object, centroid_coord, 3, 0, 1)
            cv2.circle(camera_image, centroid_coord, 3, color, -1)

            # painting the biggest object in the camera's image in red
            cv2.add(camera_image, (-70, -70, 100, 0), dst=camera_image, mask=biggest_object)

            cv2.imshow(painting_object_window, biggest_object)
            cv2.imshow(camera_window, camera_image)

            # draw on canvas image
            if usp_status:
                if distance(old_centroid_coord[0], centroid_coord[0], old_centroid_coord[1],
                            old_centroid_coord[1]) > 100:

                    old_centroid_coord = centroid_coord
                    cv2.line(canvas_image, old_centroid_coord, centroid_coord, color, thickness)
                else:
                    cv2.line(canvas_image, old_centroid_coord, centroid_coord, color, thickness)
            else:
                cv2.line(canvas_image, old_centroid_coord, centroid_coord, color, thickness)

            old_centroid_coord = centroid_coord

            if ucm_status:
                # mask white contains all white pixels
                mask_white = cv2.inRange(canvas_image, (254, 254, 254), (255, 255, 255))
                # mask contains all pixels that aren t whites, the useful draw
                mask = 255 - mask_white
                mask = mask.astype(np.bool)
                # camera_image_ucm is the junction between the paint and our image
                camera_image_ucm[mask] = canvas_image[mask]
                camera_image_ucm_2 = copy.deepcopy(camera_image_ucm)
                cv2.circle(camera_image_ucm_2, (20, 20), thickness, color, -1)
                cv2.circle(camera_image_ucm_2, centroid_coord, 8, color, 2)
                cv2.imshow(painting_canvas_window, camera_image_ucm_2)
            else:
                canvas_image2 = copy.deepcopy(canvas_image)
                cv2.circle(canvas_image2, (20, 20), thickness, color, -1)
                cv2.circle(canvas_image2, centroid_coord, 8, color, 2)
                cv2.imshow(painting_canvas_window, canvas_image2)

        else:
            if ucm_status:
                if np.count_nonzero(mask) != 0:
                    camera_image_ucm[mask] = canvas_image[mask]
                cv2.imshow(painting_canvas_window, camera_image_ucm)
            else:
                cv2.imshow(painting_canvas_window, canvas_image)
            cv2.imshow(camera_window, camera_image)

            if chr(cv2.waitKey(1)) == 'q':
                break

    # ---------------------
    # finishing the program
    # ---------------------
    cv2.destroyAllWindows()
    capture.release()


if __name__ == '__main__':
    main()
