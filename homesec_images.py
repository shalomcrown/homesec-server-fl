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
from Tkinter import *
import thread

try:
    import numpy as np
    import cv2
    import cv
    import matplotlib.pyplot as plt
    from PIL import Image
    from PIL import ImageTk
    from gi.repository import Gtk, GObject, GdkPixbuf
except:
    print """
        Couldn't import some packages. Try the following and then run again:
        sudo apt-get install python-numpy python-opencv  python-matplotlib python-mplexporter python-pil python-pil.imagetk

        And possibly:
        sudo pip install --upgrade pillow

        On RaspberryPi you will also need to run the following:
        sudo modprobe bcm2835-v4l2
    """
    exit(-1)


logger = logging.getLogger(__name__)
scriptPath = os.path.dirname(os.path.realpath(__file__))


class HomesecImage:
    update_image_event = '<<update_images>>'

    def __init__(self):
        self.imageCount = 0
        self.root = None
        self.stop = False
        self.win_gtk = None


    #===========================================================
    def setImagesLogger(self, lg):
        logger = lg


    #=======================================
    #     dateNow = time.strftime('%Y-%m-%d_%H-%M-%S', time.gmtime())

    def takePictureIntoImage(self, camera):
        retval, im = camera.read()
        #xlogger.debug('Image shape %s %s', im.shape, im.dtype)
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
        if self.root:
            logger.debug('Generate event %s', self.update_image_event)
            self.win_tk.event_generate(self.update_image_event, when="tail")
        if self.win_gtk:
            logger.debug('Generate GTK event update-images')
            self.win_gtk.emit("update-images")


        if previousImage is not None:
            logger.info("Have previous file");
            # nextImage = Image.open(nextImageFile)
            # previousImage = Image.open(previousImageFile)
            diff = self.diffCoeff(previousImage, self.nextImage)
            logger.info("Diff is: %f", diff)

            if diff < 0.95:
                fileName = taken_at.strftime('image-%Y-%m-%d_%H:%M:%S.%f_') + str(self.imageCount) + '.jpg'
                fileName = os.path.join(image_dir, fileName)
                self.imageCount = self.imageCount + 1
                logger.debug('Writing file to: %s', fileName)
                cv2.imwrite(fileName, self.nextImage)

        return self.nextImage


    #=======================================
    def imageCycle(self, cycleTime, server_url=None, dbSession=None, image_dir='/tmp/homesec'):
        logger.setLevel(logging.DEBUG)
        logger.info("Starting up")
        previousImage = None
        self.averageImage = np.zeros((480,640,3), np.float32)
        self.cam = cv2.VideoCapture(0)
        self.cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 640)
        self.cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 480)

       # warm camera up
        logger.debug('Camera warm up')
        for i in range(10, 0, -1):
            if self.stop: break
            logger.info('Warming up: %d', i)
            time.sleep(cycleTime)
            self.takePictureIntoImage(self.cam)

        while not self.stop:
            logger.debug('Next image')
            previousImage = self.doNextImage(previousImage, self.cam, server_url, dbSession=dbSession, image_dir=image_dir)
            imageForAverage = np.float32(previousImage) / 255.0
            cv2.accumulateWeighted(imageForAverage, self.averageImage, 0.1)
            logger.debug('Sleep until next image, an average pixel was %s', self.averageImage[240, 320])
            time.sleep(cycleTime)

    #===========================================================
    def display_thread_cv2(self):
        logger.debug('Display thread starting up')
        imageWindowName = 'Homesec image'
        averageImageName = 'Average image'
        cv2.namedWindow(imageWindowName)
        cv2.namedWindow(averageImageName)

        while True:
            self.newImageEvent.wait(0.1)
            if self.newImageEvent.isSet():
                self.newImageEvent.clear()
                logger.debug('Display new image')
                cv2.imshow(imageWindowName, self.nextImage)
                cv2.imshow(averageImageName, self.averageImage)
            cv2.waitKey(1)

    #===========================================================
    class TkApplication(Frame):

        def __init__(self, images=None):
            Frame.__init__(self, images.root)
            self.images = images
            self.bind(HomesecImage.update_image_event, self.update_images)
            self.pack()
            self.createWidgets()

        def quitter(self, *args):
            logger.debug('Quitter called')
            self.quit()

        def createWidgets(self):
            f0 = Frame(self)
            f0.pack(side='top', expand=1, fill='x')

            f1 = Frame(f0)
            f1.pack(side='right', expand=1, fill='x')

            l1 = Label(f1)
            l1['text'] = 'Latest image'
            l1.pack(side="top")
            self.image_label = Label(f1)
            self.image_label.pack(side='bottom')

            f2 = Frame(f0)
            f2.pack(side='left', expand=1, fill='x')
            l2 = Label(f2)
            l2['text'] = 'Average image'
            l2.pack(side="top")
            self.av_image = Label(f2)
            self.av_image.pack(side='bottom')

            quit = Button(self)
            quit['text'] = 'Quit'
            quit.pack(side='bottom')
            quit.bind('<ButtonPress>', self.quitter)


        def setImage(self, cvImage, widget):
            #b,g,r = cv2.split(cvImage)
            #img = cv2.merge((r,g,b))
            #img = np.ubyte(img)
            img = cv2.cvtColor(cvImage, cv2.COLOR_BGR2RGBA)
            im = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=im)
            widget['image']=imgtk
            self.update()

        def update_images(self, *args):
            logger.debug('Update images')
            self.setImage(self.images.nextImage, self.image_label)


    #===========================================================
    def display_thread_tk(self):
        self.root = Tk()
        self.win_tk = self.TkApplication(self)
        self.win_tk.mainloop()
        self.root.destroy()
        self.root = None
        self.images_cleanup()
        thread.interrupt_main()
        print
        os._exit(0)

    #===========================================================



    class GtkWindow(Gtk.Window):
        __gsignals__ = {
            "update-images": (GObject.SIGNAL_RUN_FIRST, None, ()),
            }

        def __init__(self, imagesObject):
            Gtk.Window.__init__(self, title="Hello World")

            self.imagesObject = imagesObject

            grid = Gtk.Grid()
            self.add(grid)
            self.image_average = Gtk.Image()
            grid.attach(self.image_average, 1, 1, 1, 2)

            self.image_original = Gtk.Image()
            grid.attach_next_to(self.image_original, self.image_average, Gtk.PositionType.RIGHT, 1, 2)

            self.button = Gtk.Button(label="Quit")
            self.button.connect("clicked", self.on_button_clicked)
            grid.attach(self.button, 1, 3, 1, 1)

            self.connect("update-images", self.update_images)
            ##self.emit("selection-finished")

        def on_button_clicked(self, widget):
            logger.debug('Quitter called')
            Gtk.main_quit()

        def update_images(self, widget):
            logger.debug('Image updater called')
            img = cv2.cvtColor(self.imagesObject.nextImage, cv2.COLOR_BGR2RGBA)
            width, height = img.size
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(img, GdkPixbuf.Colorspace.RGB,
                                          True, 8, width, height, width * 4)


    def display_thread_gtk(self):
        self.win_gtk = self.GtkWindow(self)
        self.win_gtk.connect("delete-event", Gtk.main_quit)
        self.win_gtk.show_all()
        Gtk.main()
        self.images_cleanup()
        thread.interrupt_main()
        print
        os._exit(0)

    #===========================================================
    def images_cleanup(self):
        logger.debug('Images - cleanup')
        self.stop = True
        self.cameraThread.join()
        self.cam.release()
        cv2.destroyAllWindows()

    #=======================================
    def start_images(self, dbSession=None, server_url=None, image_dir='/tmp/homesec'):
        logger.debug('Start image thread')
        self.newImageEvent = threading.Event()
        self.cameraThread = threading.Thread(target=self.imageCycle, args=(0.5, server_url, dbSession, image_dir))
        atexit.register(self.images_cleanup)

        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        self.cameraThread.daemon = True
        self.cameraThread.start()

        self.displayThread = threading.Thread(target=self.display_thread_gtk)
        self.displayThread.daemon = True
        self.displayThread.start()

#=======================================

if __name__ == "__main__":
    # logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

    HomesecImage().start_images()


