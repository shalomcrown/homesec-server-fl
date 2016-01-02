#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time
import ConfigParser
import os
import smtplib
import threading
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart



try:
    import numpy as np
    import cv2
    import cv
except:
    print """
        Couldn't import some packages. Try the following and then run again:
        sudo apt-get install python-numpy python-opencv
        sudo modprobe bcm2835-v4l2
    """
    exit(-1)



logger = logging.getLogger('homesec')

#=======================================
#     dateNow = time.strftime('%Y-%m-%d_%H-%M-%S', time.gmtime())

def takePictureIntoImage(camera):
#     camSurf = camera.get_image()
#     data = pygame.image.tostring( camSurf, 'RGBA')
#     image = Image.fromstring('RGBA', camSurf.get_size(), data)

    retval, im = camera.read()
    return im


#=======================================
def normalizeComponent(histogram, offset, length):
    pass

#=======================================

def normalizeHistogram(histogram):
    componentLength = len(histogram) / 3

    for component in range(1, 3):
        normalizeComponent(histogram, componentLength * component, componentLength)

#=======================================

def diffCoeff(im1, im2):
    "Calculate the root-mean-square difference between two images"
    hsv1 = cv2.cvtColor(im1,cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(im2,cv2.COLOR_BGR2HSV)

    h1 = cv2.calcHist([hsv1], [0, 1], None, [180, 256], [0, 180, 0, 256])
    h2 = cv2.calcHist([hsv2], [0, 1], None, [180, 256], [0, 180, 0, 256])

#     h1rgb = cv2.calcHist([im1], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])
#     h2rgb = cv2.calcHist([im2], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])

    #cv2.normalize(h1,h1,0,255,cv2.NORM_MINMAX)
    #cv2.normalize(h2,h2,0,255,cv2.NORM_MINMAX)

#     cv2.normalize(h1rgb,h1rgb,0,255,cv2.NORM_MINMAX)
#     cv2.normalize(h2rgb,h2rgb,0,255,cv2.NORM_MINMAX)

    rms = cv2.compareHist(h1, h2, 0)
#     rms = cv2.compareHist(h1rgb, h2rgb, 0)

    return rms

#=======================================

def doNextImage(previousImage, camera, loginDetails):
    logger.info("Next image")
    nextImage = takePictureIntoImage(camera)

    if previousImage is not None:
        logger.info("Have previous file");
        # nextImage = Image.open(nextImageFile)
        # previousImage = Image.open(previousImageFile)
        diff = diffCoeff(previousImage, nextImage)
        logger.info("Diff is: %f", diff)

        if diff < 0.99:
            pass

    return nextImage


#=======================================
def imageCycle(cycleTime, server_url = None):
    previousImage = None
    cam = cv2.VideoCapture(0)
    cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 480)

    #cv2.namedWindow('Homesec image')

    # warm camera up
    logger.debug('Camera warm up')
    for i in range(10,0,-1):
        logger.info('Warming up: %d', i)
        time.sleep(cycleTime)
        takePictureIntoImage(cam)


    while True:
        logger.debug('Next image')
        previousImage = doNextImage(previousImage, cam, server_url)
        #cv2.imshow('Homesec image', previousImage);
        #cv2.waitKey(500)
        logger.debug('Sleep until next image')
        time.sleep(cycleTime)

#=======================================

def start_images(server_url = None):
    th = threading.Thread(target=imageCycle, args=(0.5, server_url))
    th.start()


#=======================================

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

    logger.info("Starting up")
    imageCycle(0.5)


