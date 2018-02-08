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
import os
import sys
import time

from datetime import datetime

import cv2
import movidius as mv
import numpy as np

mvng = None


def logging(*args):
    print("[%08.3f]" % time.time(), ' '.join(args))


def run(mvng):
    """Infinite loop serving inference requests"""

    logging('detection service is running')

    capture = cv2.VideoCapture(0)
    while True:
        t_start = datetime.now()
        status, image_data = capture.read()
        t_end = datetime.now()
        t_capture = t_end - t_start
        logging('capture time: {} ms'.format(t_capture.total_seconds() * 1000))

        t_start = datetime.now()
        processed_data = mv.process_yolo_input(image_data)
        t_end = datetime.now()
        t_preprocess = t_end - t_start
        logging('preprocess time: {} ms'.format(t_preprocess.total_seconds() * 1000))

        t_start = datetime.now()
        output = mvng.inference(processed_data)
        t_end = datetime.now()
        t_inference = t_end - t_start
        logging('inference time: {} ms'.format(t_inference.total_seconds() * 1000))

        t_start = datetime.now()
        interpreted_output = mv.interpret_yolo_output(output,
                                                      image_data.shape[1],
                                                      image_data.shape[0])
        yolo_outputs = mv.process_yolo_output(image_data,
                                              interpreted_output,
                                              '/tmp/yolo_resutl.jpg')
        t_end = datetime.now()
        t_postprocess = t_end - t_start
        logging('postprocess time: {} ms'.format(t_postprocess.total_seconds() * 1000))

        #output_name = input_name + '.txt'
        #mv.save_yolo_output_text(output_name, yolo_outputs)
        #logging(input_name, " detected!")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True, help='Model file path')
    ap.add_argument('--label', required=True, help='Label file path')
    ap.add_argument('--image_dir', required=True, help='Path to image file')
    #ap.add_argument('--num_top_predictions', default=5,
    #                help='Display this many predictions')
    return vars(ap.parse_args())


if __name__ == '__main__':
    args = parse_args()

    mvng = mv.MovidiusNeuralGraph(args['model'], args['label'])

    logging("model filepath: ", args['model'])
    logging("label filepath: ", args['label'])
    logging("image_dir: ", args['image_dir'])

    # workaround the issue that SIGINT cannot be received (fork a child to
    # avoid blocking the main process in Thread.join()
    child_pid = os.fork()
    if child_pid == 0:  # child
        run(mvng)
    else:  # parent
        try:
            os.wait()
        except KeyboardInterrupt:
            os.kill(child_pid, signal.SIGKILL)
            os.unlink(pidfile)
