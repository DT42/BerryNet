#!/usr/bin/env python3
#
# Copyright 2018 DT42
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
import numpy as np
import threading
import multiprocessing
import queue
import signal
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import caffe
import hashlib
import urllib.request
import tempfile
import shutil

image_queue = queue.Queue()
sess = None
threads = []
image_dir = '/run/image_dir'
caffe_classifier = None
caffe_labels = []
model_meta_file = '/usr/share/doc/caffe-doc/models/bvlc_reference_caffenet/readme.md'
label_file = '/tmp/synset_words.txt'
pretrained_model = None

def logging(*args):
    print("[%08.3f]" % time.time(), ' '.join(args))

def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)

def load_labels(filename):
    """Read in labels, one label per line."""
    return [line.rstrip() for line in open(filename)]

def read_model_meta_file(meta_file):
    """Read model meta file. The meta file is inside caffe-doc package"""
    # We believe we shouldn't read this file for downloading and checking
    # model. Instead we should package some model if there is free one.
    url = None
    sha1sum = None
    filename = None
    for line in open(meta_file):
        l1 = line.rstrip()
        if (l1.startswith("sha1:")):
            sha1sum = l1[len("sha1:"):].strip()
        if (l1.startswith("caffemodel_url:")):
            url = l1[len("caffemodel_url:"):].strip()
        if (l1.startswith("caffemodel:")):
            filename = l1[len("caffemodel:"):].strip()
        if ((sha1sum != None) and (url != None) and (filename != None)):
            break
    if ((url != None) and (sha1sum != None) and (filename != None)):
        return {'url': url, 'sha1sum': sha1sum, 'filename': filename}
    return None

def sha1sum(filename):
    """calculate sha1sum"""
    BUF_SIZE=1024
    sha1 = hashlib.sha1()
    with open(filename, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

def download_model():
    """Download pretrained model"""
    # Downloading model from network isn't good for Debian. We need to package
    # the model.
    global pretrained_model
    meta_data = read_model_meta_file(model_meta_file)
    if (meta_data is None):
        logging('Cannot load %s'%(meta_data))
        return None
    # FIXME: using /tmp/ will be in-secure.
    pretrained_model = os.path.join('/','tmp',meta_data['filename'])
    if (os.path.isfile(pretrained_model)):
        sha1 = sha1sum(pretrained_model)
        if (sha1 != meta_data['sha1sum']):
            logging('Model %s SHA1 is not equal to %s'%(pretrained_model, meta_data['sha1sum']))
            pretrained_model = None
            return None
        else:
            logging('Model already exists')
            pass
    else:
        logging('Downloading model file from %s'%(meta_data['url']))
        urllib.request.urlretrieve(meta_data['url'], pretrained_model)
        logging('Checking SHA1...')
        sha1 = sha1sum(pretrained_model)
        if (sha1 != meta_data['sha1sum']):
            logging('Model %s SHA1 is not equal to %s'%(pretrained_model, meta_data['sha1sum']))
            pretrained_model = None
            return None
        else:
            logging('Model downloaded')
            pass
    return None

def download_label():
    """Download label file"""
    # Using the scripts inside caffe Debian package to download label file.
    # This could also be wrong. Why we don't package the label file?
    global label_file
    if (os.path.isfile(label_file)):
        logging("Label file exists");
        pass
    else:
        logging("Label file not exists. Downloading...");
        tmpdir = tempfile.mkdtemp()
        s1 = shutil.copy2(os.path.join('/', 'usr', 'share', 'doc', 'caffe-doc',
                                       'data', 'ilsvrc12',
                                       'get_ilsvrc_aux.sh'),
                          tmpdir)
        os.system('sh \'%s\''%(s1));
        # FIXME: using /tmp/ will be in-secure.
        shutil.copy2(os.path.join(tmpdir, 'synset_words.txt'), '/tmp')

def create_classifier(pretrained_model):
    """Creates a model from saved caffemodel file and returns a classifier."""
    # Creates model from saved .caffemodel.

    # The following file are shipped inside caffe-doc Debian package
    model_def = os.path.join("/", "usr", "share", "doc", "caffe-doc",
                             "models","bvlc_reference_caffenet",
                             "deploy.prototxt")
    image_dims = [ 256, 256 ]
    # The following file are shipped inside python3-caffe-cpu Debian package
    mean = np.load(os.path.join('/', 'usr', 'lib', 'python3',
                                'dist-packages', 'caffe', 'imagenet',
                                'ilsvrc_2012_mean.npy'))
    channel_swap = [2, 1, 0]
    raw_scale = 255.0

    caffe.set_mode_cpu()
    classifier = caffe.Classifier(model_def, pretrained_model,
                                  image_dims=image_dims, mean=mean,
                                  raw_scale=raw_scale,
                                  channel_swap=channel_swap)
    return classifier

def server(labels):
    """Infinite loop serving inference requests"""
    global image_queue, sess

    logging(threading.current_thread().getName(), "is running")

    while True:
        input_name = image_queue.get()
        if (input_name.endswith('npy')):
            inputs = np.load(input_name)
        else:
            inputs = [caffe.io.load_image(input_name)]

        predictions = caffe_classifier.predict(inputs, False)
        # make tuples
        predictions_list = predictions[0].tolist()
        data = zip(predictions_list, caffe_labels)
        output_name = input_name+'.txt'
        output_done_name = output_name+'.done'
        output = open(output_name, 'wt')
        for d in sorted(data, reverse=True):
            human_string = d[1]
            score = d[0]
            print("%s (score = %.5f)" % (human_string, score), file=output)
            if (score < 0.00001):
                break
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

if __name__ == '__main__':

    pid = str(os.getpid())
    pidfile = "/tmp/classify_server.pid"

    if os.path.isfile(pidfile):
        logging("%s already exists, exiting" % pidfile)
        sys.exit(1)

    with open(pidfile, 'w') as f:
        f.write(pid)

    # Please read /usr/share/doc/caffe-doc/models/bvlc_reference_caffenet/readme.md
    download_model()
    download_label()
    caffe_labels = load_labels(label_file)
    caffe_classifier = create_classifier(pretrained_model)

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
        for i in range(1):
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
