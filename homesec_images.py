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
import atexit
import datetime

import db_schema

try:
    import numpy as np
    import cv2
    import cv
except:
    print """
        Couldn't import some packages. Try the following and then run again:
        sudo apt-get install python-numpy python-opencv

        On RaspberryPi you will also need to run the following:
        sudo modprobe bcm2835-v4l2
    """
    exit(-1)


logger = logging.getLogger(__name__)



class HomesecImage:
    def __init__(self):
        self.imageCount = 0


    #===========================================================
    def setImagesLogger(self, lg):
        logger = lg


    #=======================================
    #     dateNow = time.strftime('%Y-%m-%d_%H-%M-%S', time.gmtime())

    def takePictureIntoImage(self, camera):
        retval, im = camera.read()
        #logger.debug('Image shape %s', im.shape)
        #print('Image shape %s' % im.shape)
        return im


    #=======================================
    def normalizeComponent(self, histogram, offset, length):
        pass

    #=======================================
    def normalizeHistogram(self, histogram):
        componentLength = len(histogram) / 3

        for component in range(1, 3):
            self.normalizeComponent(histogram, componentLength * component, componentLength)

    #=======================================

    def diffCoeff(self, im1, im2):
        "Calculate the root-mean-square difference between two images"
        hsv1 = cv2.cvtColor(im1, cv2.COLOR_BGR2HSV)
        hsv2 = cv2.cvtColor(im2, cv2.COLOR_BGR2HSV)

        h1 = cv2.calcHist([hsv1], [0, 1], None, [180, 256], [0, 180, 0, 256])
        h2 = cv2.calcHist([hsv2], [0, 1], None, [180, 256], [0, 180, 0, 256])

    #     h1rgb = cv2.calcHist([im1], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])
    #     h2rgb = cv2.calcHist([im2], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])

        # cv2.normalize(h1,h1,0,255,cv2.NORM_MINMAX)
        # cv2.normalize(h2,h2,0,255,cv2.NORM_MINMAX)

    #     cv2.normalize(h1rgb,h1rgb,0,255,cv2.NORM_MINMAX)
    #     cv2.normalize(h2rgb,h2rgb,0,255,cv2.NORM_MINMAX)

        rms = cv2.compareHist(h1, h2, 0)
    #     rms = cv2.compareHist(h1rgb, h2rgb, 0)

        return rms

    #=======================================

    def doNextImage(self, previousImage, camera, loginDetails, dbSession=None, image_dir='/tmp/homesec'):
        logger.info("Next image")
        taken_at = datetime.datetime.utcnow()
        self.nextImage = self.takePictureIntoImage(camera)
        self.newImageEvent.set()
        global imageCount

        if previousImage is not None:
            logger.info("Have previous file");
            # nextImage = Image.open(nextImageFile)
            # previousImage = Image.open(previousImageFile)
            diff = self.diffCoeff(previousImage, self.nextImage)
            logger.info("Diff is: %f", diff)

            if diff < 0.95:
                fileName = taken_at.strftime('image-%Y-%m-%d_%H:%M:%S.%f_') + str(imageCount) + '.jpg'
                fileName = os.path.join(image_dir, fileName)
                imageCount = imageCount + 1
                logger.debug('Writing file to: %s', fileName)
                cv2.imwrite(fileName, self.nextImage)

        return self.nextImage


    #=======================================
    def imageCycle(self, cycleTime, server_url=None, dbSession=None, image_dir='/tmp/homesec'):
        logger.setLevel(logging.DEBUG)
        logger.info("Starting up")
        previousImage = None
        #averageImage = cv2.
        cam = cv2.VideoCapture(0)
        cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 640)
        cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 480)

       # warm camera up
        logger.debug('Camera warm up')
        for i in range(10, 0, -1):
            logger.info('Warming up: %d', i)
            time.sleep(cycleTime)
            self.takePictureIntoImage(cam)


        while True:
            logger.debug('Next image')
            previousImage = self.doNextImage(previousImage, cam, server_url, dbSession=dbSession, image_dir=image_dir)
            logger.debug('Sleep until next image')
            time.sleep(cycleTime)

    #===========================================================
    def display_thread(self):
        logger.debug('Display thread starting up')
        imageWindowName = 'Homesec image'
        averageImageName = 'Average image'
        cv2.namedWindow(imageWindowName)
        cv2.namedWindow(averageImageName)

        while True:
            self.newImageEvent.wait(0.1)
            if self.newImageEvent.isSet():
                logger.debug('Display new image')
                cv2.imshow(imageWindowName, self.nextImage)
            cv2.waitKey(1)

    #===========================================================
    def images_cleanup(self):
        logger.debug('Images - cleanup ****')
        self.cameraThread.cancel()
        self.displayThread.cancel()
        cv2.destroyAllWindows()

    #=======================================
    def start_images(self, dbSession=None, server_url=None, image_dir='/tmp/homesec'):
        logger.debug('Start image thread')
        self.newImageEvent = threading.Event()
        self.cameraThread = threading.Thread(target=self.imageCycle, args=(0.5, server_url, dbSession, image_dir))
        atexit.register(self.images_cleanup)

        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        self.cameraThread.start()

        self.displayThread = threading.Thread(target=self.display_thread)
        self.displayThread.start()

#=======================================

if __name__ == "__main__":
    # logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

    HomesecImage().start_images()


