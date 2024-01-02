import base64
import json
import re
import time
import bs4
import cv2
from flask import request
import httpx
import numpy as np
from cv2.typing import MatLike
from constants import flask_app

from constants import BAD_REQUEST

class Worker:
    THRESHOLD: int = 30
    WIDTH: int = 1324
    HEIGHT: int = 563

    img: MatLike
    canny: MatLike
    min_dist: int

    image_hash: str

    b64image: str
    def __init__(self, b64image: str) -> None:
        self.b64image = b64image
        pass

    def make_request(self) -> bool:
        base64_string = self.b64image
        if ',' in base64_string:
            header, base64_string = base64_string.split(',', 1)
            
        image_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(image_data, np.uint8)

        # Read image
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # img = cv2.imread('py/image.png')
        hh, ww = img.shape[:2]

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Gaussian filter
        gray = cv2.GaussianBlur(gray, ksize=(7,7), sigmaX=0, sigmaY=0)

        # get canny edges
        canny = cv2.Canny(gray, 20, 200)

        min_dist = int(ww/20)

        self.img = img
        self.canny = canny
        self.min_dist = min_dist
        return True

    def find_circle(self):
        # param2: lower = more lenient
        # Was at 50 from script i stole, now at 30, it seems to be pretty nice without falseflags
        circles = cv2.HoughCircles(self.canny, cv2.HOUGH_GRADIENT, 1, minDist=self.min_dist, param1=200, param2=self.THRESHOLD, minRadius=20, maxRadius=40)
        done = False
        tries = 0
        adapted_threshold = self.THRESHOLD
        while not done:
            try:
                num = circles[0]
                if len(num) > 1:
                    tries += 1
                    adapted_threshold += 1
                    print(f"New try higher (try {tries} threshold {adapted_threshold})")
                    circles = cv2.HoughCircles(self.canny, cv2.HOUGH_GRADIENT, 1, minDist=self.min_dist, param1=200, param2=adapted_threshold, minRadius=20, maxRadius=40)
                    continue
                print("Done !")
                done = True
            except:
                tries += 1
                adapted_threshold -= 2
                print(f"New try lower (try {tries} threshold {adapted_threshold})")
                circles = cv2.HoughCircles(self.canny, cv2.HOUGH_GRADIENT, 1, minDist=self.min_dist, param1=200, param2=adapted_threshold, minRadius=20, maxRadius=40)


        return circles
        # try:
        #     circles[0]
        # except:
        #     result = img.copy()
        #     cv2.imwrite('py/play2FAIL.png', result)
        #     print("FAILED !")
        #     return False

    def do_all(self):
        res = self.make_request()
        while not res:
            print("Res failed, retrying")
            res = self.make_request()
        t = time.time_ns()
        print("request done!")
        circles = self.find_circle()

        # draw circles
        # result = self.img.copy()
        # for circle in circles[0]:
        #     # draw the circle in the output image
        #     (x,y,r) = circle
        #     x = int(x)
        #     y = int(y)
        #     r = int(r)
        #     print(circle)
        #     cv2.circle(result, (x, y), r, (0, 0, 255), 2)
        #     cv2.line(result, (x-10, y), (x+10, y),(255, 255, 255), 5)
        #     cv2.line(result, (x, y-10), (x, y+10),(255, 255, 255), 5)

        # print(len(circles))
        

        # save results
        # cv2.imwrite('py/play1.png', self.canny)
        # cv2.imwrite('py/play2.png', result)
        endt = time.time_ns()
        print(f"Grabbing done! ({(endt-t)/1000000000}s)")
        return circles[0][0]


@flask_app.route("/epicImageFinder", methods=["POST"])
def find_circle_image():
    try:
        data = request.json
        image = data.get("b64image")
        if not image:
            return BAD_REQUEST
        
        res = Worker(image).do_all()
        return [int(res[0]), int(res[1]), int(res[2])] # 3rd item is the radius, we don't care about it

    except Exception as e:
        return BAD_REQUEST
