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
import numpy as np
import threading
import multiprocessing
import tensorflow as tf
import Queue
import signal
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

FLAGS = tf.app.flags.FLAGS
image_queue = Queue.Queue()
sess = None
threads = []

# classify_image_graph_def.pb:
#   Binary representation of the GraphDef protocol buffer.
# imagenet_synset_to_human_label_map.txt:
#   Map from synset ID to a human readable string.
# imagenet_2012_challenge_label_map_proto.pbtxt:
#   Text representation of a protocol buffer mapping a label to synset ID.
tf.app.flags.DEFINE_string(
    'model_dir', 'model',
    """Path to output_graph.pb and output_labels.txt.""")
tf.app.flags.DEFINE_string('image_dir', 'image',
                           """Path to image file.""")
tf.app.flags.DEFINE_string('output_layer', 'softmax:0',
                           """Name of the result operation""")
tf.app.flags.DEFINE_string('input_layer', 'DecodeJpeg/contents:0',
                           """Name of the input operation""")
tf.app.flags.DEFINE_integer('num_top_predictions', 5,
                            """Display this many predictions.""")


def logging(*args):
    print("[%08.3f]" % time.time(), ' '.join(args))

def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)

def load_labels(filename):
    """Read in labels, one label per line."""
    return [line.rstrip() for line in tf.gfile.FastGFile(filename)]


def create_graph():
    """Creates a graph from saved GraphDef file and returns a saver."""
    # Creates graph from saved graph_def.pb.
    with tf.gfile.FastGFile(os.path.join(
        FLAGS.model_dir, 'output_graph.pb'), 'rb') as f:
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(f.read())
        _ = tf.import_graph_def(graph_def, name='')


def server(labels):
    """Infinite loop serving inference requests"""

    global image_queue, sess

    logging(threading.current_thread().getName(), "is running")

    with sess.as_default():
        # Some useful tensors:
        # 'softmax:0': A tensor containing the normalized prediction across
        #   1000 labels.
        # 'pool_3:0': A tensor containing the next-to-last layer containing 2048
        #   float description of the image.
        # 'DecodeJpeg/contents:0': A tensor containing a string providing JPEG
        #   encoding of the image.

        while True:
            input_name = image_queue.get()
            image_data = tf.gfile.FastGFile(input_name, 'rb').read()

            predictions = sess.run(FLAGS.output_layer,
                                   {FLAGS.input_layer: image_data})
            predictions = np.squeeze(predictions)
            top_k = predictions.argsort()[-FLAGS.num_top_predictions:][::-1]

            output_name = input_name+'.txt'
            output_done_name = output_name+'.done'
            output = open(output_name, 'w')
            for node_id in top_k:
                human_string = labels[node_id]
                score = predictions[node_id]
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
 
    global sess, threads

    # Creates graph from saved GraphDef.
    create_graph()

    # Reuse the same session for all threads processing requests
    sess = tf.Session()
    # Creates node ID --> English string lookup.
    labels = load_labels(os.path.join(FLAGS.model_dir, 'output_labels.txt'))

    # Create a server thread for each CPU core
    cpu_count = multiprocessing.cpu_count()
    for i in xrange(cpu_count/4):
        threads.append(threading.Thread(target=server,
                                        name='Server thread %d' % i,
                                        args=(labels,)))
    for t in threads: t.start()
    for t in threads: t.join()
 

if __name__ == '__main__':
    pid = str(os.getpid())
    pidfile = "/tmp/classify_server.pid"

    if os.path.isfile(pidfile):
        logging("%s already exists, exiting" % pidfile)
        sys.exit(1)

    with open(pidfile, 'w') as f:
        f.write(pid)

    logging("model_dir: ", FLAGS.model_dir)
    logging("image_dir: ", FLAGS.image_dir)

    # workaround the issue that SIGINT cannot be received (fork a child to 
    # avoid blocking the main process in Thread.join()
    child_pid = os.fork()
    if child_pid == 0:
        # child
        # observer handles event in a different thread
        observer = Observer()
        observer.schedule(EventHandler(['*.jpg.done']), path=FLAGS.image_dir)
        observer.start()
        tf.app.run()
    else:
        # parent
        try:
            os.wait()
        except KeyboardInterrupt:
            os.kill(child_pid, signal.SIGKILL)
            os.unlink(pidfile)
