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

"""Simple image classification server with Inception.

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
import os
import sys
import time
from caffe2.proto import caffe2_pb2
import numpy as np
import skimage.io
import skimage.transform
import threading
import multiprocessing
import Queue
import signal
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from caffe2.python import core, workspace
import urllib2

image_dir = '/run/image_dir'
image_queue = Queue.Queue()
sess = None
threads = []

def logging(*args):
    print("[%08.3f]" % time.time(), ' '.join(args))

def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)

def crop_center(img,cropx,cropy):
    y,x,c = img.shape
    startx = x//2-(cropx//2)
    starty = y//2-(cropy//2)
    return img[starty:starty+cropy,startx:startx+cropx]

def rescale(img, input_height, input_width):
    aspect = img.shape[1]/float(img.shape[0])
    if(aspect>1):
        # landscape orientation - wide image
        res = int(aspect * input_height)
        imgScaled = skimage.transform.resize(img, (input_width, res))
    if(aspect<1):
        # portrait orientation - tall image
        res = int(input_width/aspect)
        imgScaled = skimage.transform.resize(img, (res, input_height))
    if(aspect == 1):
        imgScaled = skimage.transform.resize(img, (input_width, input_height))
    return imgScaled

def server(labels):
    """Infinite loop serving inference requests"""

    global image_queue, sess
    CAFFE2_ROOT = "/caffe2"
    CAFFE_MODELS = "/caffe2/caffe2/python/models"
    MODEL = 'squeezenet', 'exec_net.pb', 'predict_net.pb', 'ilsvrc_2012_mean.npy', 227
    codes =  "https://gist.githubusercontent.com/aaronmarkham/cd3a6b6ac071eca6f7b4a6e40e6038aa/raw/9edb4038a37da6b5a44c3b5bc52e448ff09bfe5b/alexnet_codes"

    logging(threading.current_thread().getName(), "is running")
    CAFFE2_ROOT = os.path.expanduser(CAFFE2_ROOT)
    CAFFE_MODELS = os.path.expanduser(CAFFE_MODELS)
    MEAN_FILE = os.path.join(CAFFE_MODELS, MODEL[0], MODEL[3])
    if not os.path.exists(MEAN_FILE):
        mean = 128
    else:
        mean = np.load(MEAN_FILE).mean(1).mean(1)
        mean = mean[:, np.newaxis, np.newaxis]
    INPUT_IMAGE_SIZE = MODEL[4]
    INIT_NET = os.path.join(CAFFE_MODELS, MODEL[0], MODEL[1])
    PREDICT_NET = os.path.join(CAFFE_MODELS, MODEL[0], MODEL[2])

    while True:
        input_name = image_queue.get()
        img = skimage.img_as_float(skimage.io.imread(input_name)).astype(np.float32)
        img = rescale(img, INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE)
        img = crop_center(img, INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE)
            
        img = img.swapaxes(1, 2).swapaxes(0, 1)
        img = img[(2, 1, 0), :, :]
        img = img * 255 - mean
        img = img[np.newaxis, :, :, :].astype(np.float32)

        with open(INIT_NET, 'rb') as f:
            init_net = f.read()
        with open(PREDICT_NET, 'rb') as f:
            predict_net = f.read()
            
        p = workspace.Predictor(init_net, predict_net)
            
        # run the net and return prediction
        results = p.run([img])
        results = np.asarray(results)
        results = np.delete(results, 1)
        index = 0
        highest = 0
        arr = np.empty((0,2), dtype=object)
        arr[:,0] = int(10)
        arr[:,1:] = float(10)
        for i, r in enumerate(results):
            # imagenet index begins with 1!
            i=i+1
            arr = np.append(arr, np.array([[i,r]]), axis=0)
            if (r > highest):
                highest = r
                index = i
        response = urllib2.urlopen(codes)
        output_name = input_name+'.txt'
        output_done_name = output_name+'.done'
        output = open(output_name, 'w')
        for line in response:
            code, result = line.partition(":")[::2]
            if (code.strip() == str(index)):
                human_string = result.strip()[1:-2]
                score = highest
                print("%s (score = %.5f)" % (human_string, score), file=output)
        output.close()
        touch(output_done_name)
        logging(input_name, " classified!")


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
        logging(_msg, event.event_type)

    # ignore all other types of events except 'modified'
    def on_created(self, event):
        self.process(event)


def main(_):
    """Called by Tensorflow"""
 

    # Create a server thread for each CPU core
    cpu_count = multiprocessing.cpu_count()
    for i in xrange(cpu_count/4):
        threads.append(threading.Thread(target=server,
                                        name='Server thread %d' % i,
                                        args=({},)))
    for t in threads: t.start()
    for t in threads: t.join()
 

if __name__ == '__main__':
    global sess, threads

    pid = str(os.getpid())
    pidfile = "/tmp/classify_server.pid"

    if os.path.isfile(pidfile):
        logging("%s already exists, exiting" % pidfile)
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
        observer.schedule(EventHandler(['*.jpg.done']), path=image_dir)
        observer.start()
        # Create a server thread for each CPU core
        cpu_count = multiprocessing.cpu_count()
        for i in xrange(cpu_count/4):
            threads.append(threading.Thread(target=server,
                                            name='Server thread %d' % i,
                                            args=({},)))
        for t in threads: t.start()
        for t in threads: t.join()
    else:
        # parent
        try:
            os.wait()
        except KeyboardInterrupt:
            os.kill(child_pid, signal.SIGKILL)
            os.unlink(pidfile)
