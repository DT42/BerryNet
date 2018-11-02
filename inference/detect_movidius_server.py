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

import argparse
import multiprocessing
import os
import signal
import sys
import threading
import time

from datetime import datetime

import cv2
import movidius as mv
import numpy as np
import Queue

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


image_queue = Queue.Queue()
threads = []
mvng = None
SystemSnapshot = '/usr/local/berrynet/dashboard/www/freeboard/snapshot.jpg'


def logging(*args):
    print("[%08.3f]" % time.time(), ' '.join(args))


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


def server():
    """Infinite loop serving inference requests"""

    global image_queue
    global mvng

    logging(threading.current_thread().getName(), "is running")

    while True:
        input_name = image_queue.get()
        image_data = cv2.imread(input_name)
        processed_data = mv.process_yolo_input(image_data)

        t_start = datetime.now()
        output = mvng.inference(processed_data)
        t_end = datetime.now()
        t_inference = t_end - t_start
        logging('inference time: {} ms'.format(t_inference.total_seconds() * 1000))
        interpreted_output = mv.interpret_yolo_output(output,
                                                      image_data.shape[1],
                                                      image_data.shape[0])
        yolo_outputs = mv.process_yolo_output(image_data,
                                              interpreted_output,
                                              SystemSnapshot)

        output_name = input_name + '.txt'
        output_done_name = output_name + '.done'
        mv.save_yolo_output_text(output_name, yolo_outputs)
        touch(output_done_name)
        logging(input_name, " detected!")


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


def main(args):
    global threads

    # Create a server thread for each CPU core
    cpu_count = multiprocessing.cpu_count()
    for i in xrange(cpu_count/4):
        threads.append(
            threading.Thread(target=server,
                             name='Server thread %d' % i))
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True, help='Model file path')
    ap.add_argument('--label', required=True, help='Label file path')
    ap.add_argument('--image_dir', required=True, help='Path to image file')
    ap.add_argument('--num_top_predictions', default=5,
                    help='Display this many predictions')
    return vars(ap.parse_args())


if __name__ == '__main__':
    args = parse_args()

    mvng = mv.MovidiusNeuralGraph(args['model'], args['label'])

    pid = str(os.getpid())
    pidfile = "/tmp/detect_movidius_server.pid"

    if os.path.isfile(pidfile):
        logging("%s already exists, exiting" % pidfile)
        sys.exit(1)

    with open(pidfile, 'w') as f:
        f.write(pid)

    logging("model filepath: ", args['model'])
    logging("label filepath: ", args['label'])
    logging("image_dir: ", args['image_dir'])

    # workaround the issue that SIGINT cannot be received (fork a child to
    # avoid blocking the main process in Thread.join()
    child_pid = os.fork()
    if child_pid == 0:  # child
        # observer handles event in a different thread
        observer = Observer()
        observer.schedule(EventHandler(['*.jpg.done']), path=args['image_dir'])
        observer.start()
        main(args)
    else:  # parent
        try:
            os.wait()
        except KeyboardInterrupt:
            os.kill(child_pid, signal.SIGKILL)
            os.unlink(pidfile)
