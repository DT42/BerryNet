# Copyright 2017 DT42
#
# This file is part of BerryNet.
#
# BerryNet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BerryNet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BerryNet.  If not, see <http://www.gnu.org/licenses/>.

"""Simple image detection server with Tiny-YOLO.

The server monitors image_dir and run inferences on new images added to the
directory. Every image file should come with another empty file with '.done'
suffix to signal readiness. Inference result of a image can be read from the
'.txt' file of that image after '.txt.done' is spotted.

This is an example the server expects clients to do. Note the order.

# cp cat.jpg /run/image_dir
# touch /run/image_dir/cat.jpg.done

Clients should wait for appearance of 'cat.jpg.txt.done' before getting
result from 'cat.jpg.txt'.
"""

from __future__ import print_function

import logging
import multiprocessing
import os
import Queue
import signal
import sys
import threading
import time

import cv2
import numpy as np

from os.path import join as pjoin
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from darkflow.net.build import TFNet


image_queue = Queue.Queue()

# FIXME: Make these variables configurable
ImageDir = '../image'
SystemSnapshot = '../../dashboard/www/freeboard/snapshot.jpg'


def _logging(*args):
    print("[%08.3f]" % time.time(), ' '.join(args))


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


def drawBoundingBoxes(imageData, imageOutputPath, inferenceResults, colorMap):
    """Draw bounding boxes on an image.

    imageData: image data in numpy array format
    imageOutputPath: output image file path
    inferenceResults: Darkflow inference results
    colorMap: Bounding box color candidates, list of RGB tuples.
    """
    # TODO: return raw data instead of save image
    for res in inferenceResults:
        left = res['topleft']['x']
        top = res['topleft']['y']
        right = res['bottomright']['x']
        bottom = res['bottomright']['y']
        colorIndex = res['coloridx']
        color = colorMap[colorIndex]
        label = res['label']
        confidence = res['confidence']
        imgHeight, imgWidth, _ = imageData.shape
        thick = int((imgHeight + imgWidth) // 300)

        cv2.rectangle(imageData,(left, top), (right, bottom), color, thick)
        cv2.putText(imageData, label, (left, top - 12), 0, 1e-3 * imgHeight,
            color, thick//3)
    cv2.imwrite(imageOutputPath, imageData)
    logging.debug('Save bounding box result image to {}'.format(imageOutputPath))


def server(tfnet):
    """Infinite loop serving inference requests"""

    global image_queue

    _logging(threading.current_thread().getName(), "is running")

    while True:
        input_name = image_queue.get()

        _logging('input image ' + input_name)
        imgcv = cv2.imread(input_name)
        _logging('start inference')
        result = tfnet.return_predict(imgcv)
        _logging('inference result: {}'.format(result))

        # overwrite existing input snapshot by the result image with
        # bounding boxes.
        drawBoundingBoxes(imgcv, SystemSnapshot, result, tfnet.meta['colors'])
        logging.debug('System snapshot path: %s' % pjoin(os.getcwd(), SystemSnapshot))

        output_name = input_name+'.txt'
        output_done_name = output_name+'.done'
        with open(output_name, 'w') as f:
            f.write(str(result))
        touch(output_done_name)
        _logging(input_name, " classified!")


class EventHandler(PatternMatchingEventHandler):
    def process(self, event):
        """
        event.event_type
            'modified' | 'created' | 'moved' | 'deleted'
        event.is_directory
            True | False
        event.src_path
            path/to/observed/file
        """
        # the file will be processed there
        global image_queue

        _msg = event.src_path
        image_queue.put(_msg.rstrip('.done'))
        os.remove(_msg)
        _logging(_msg, event.event_type)

    # ignore all other types of events except 'modified'
    def on_created(self, event):
        self.process(event)


def main():
    options = {
        "model": "cfg/tiny-yolo.cfg",
        "load": "bin/tiny-yolo.weights",
        'verbalise': True,
        #"threshold": 0.1
    }
    tfnet = TFNet(options)
    _logging('model dir: {}'.format(options['load']))
    _logging('config dir: {}'.format(options['model']))

    server(tfnet)


if __name__ == '__main__':
    logging.basicConfig(filename='/tmp/dlDetector.log', level=logging.DEBUG)

    pid = str(os.getpid())
    pidfile = "/tmp/detection_server.pid"

    if os.path.isfile(pidfile):
        _logging("%s already exists, exiting" % pidfile)
        sys.exit(1)

    with open(pidfile, 'w') as f:
        f.write(pid)

    # workaround the issue that SIGINT cannot be received (fork a child to
    # avoid blocking the main process in Thread.join()
    child_pid = os.fork()
    if child_pid == 0:
        # child
        # observer handles event in a different thread
        observer = Observer()
        observer.schedule(EventHandler(['*.jpg.done']), ImageDir)
        observer.start()
        main()
    else:
        # parent
        try:
            os.wait()
        except KeyboardInterrupt:
            os.kill(child_pid, signal.SIGKILL)
            os.unlink(pidfile)
