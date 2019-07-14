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

"""Darknet inference engine.
"""

from __future__ import print_function

import argparse
import json
import math
import time

import cv2
import numpy as np

from berrynet import logger
#from berrynet.dlmodelmgr import DLModelManager
from berrynet.engine import DLEngine
from ctypes import *


class BOX(Structure):
    _fields_ = [("x", c_float),
                ("y", c_float),
                ("w", c_float),
                ("h", c_float)]

class IMAGE(Structure):
    _fields_ = [("w", c_int),
                ("h", c_int),
                ("c", c_int),
                ("data", POINTER(c_float))]

class METADATA(Structure):
    _fields_ = [("classes", c_int),
                ("names", POINTER(c_char_p))]


lib = CDLL("/usr/lib/libdarknet.so", RTLD_GLOBAL)
lib.network_width.argtypes = [c_void_p]
lib.network_width.restype = c_int
lib.network_height.argtypes = [c_void_p]
lib.network_height.restype = c_int

predict = lib.network_predict
predict.argtypes = [c_void_p, POINTER(c_float)]
predict.restype = POINTER(c_float)

make_image = lib.make_image
make_image.argtypes = [c_int, c_int, c_int]
make_image.restype = IMAGE

make_boxes = lib.make_boxes
make_boxes.argtypes = [c_void_p]
make_boxes.restype = POINTER(BOX)

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [POINTER(c_void_p), c_int]

num_boxes = lib.num_boxes
num_boxes.argtypes = [c_void_p]
num_boxes.restype = c_int

make_probs = lib.make_probs
make_probs.argtypes = [c_void_p]
make_probs.restype = POINTER(POINTER(c_float))

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [c_void_p]

load_net = lib.load_network
load_net.argtypes = [c_char_p, c_char_p, c_int]
load_net.restype = c_void_p

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, c_int, c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [c_char_p, c_int, c_int]
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [c_void_p, IMAGE]
predict_image.restype = POINTER(c_float)

network_detect = lib.network_detect
network_detect.argtypes = [c_void_p, IMAGE, c_float, c_float, c_float, POINTER(BOX), POINTER(POINTER(c_float))]


def c_array(ctype, values):
    arr = (ctype*len(values))()
    arr[:] = values
    return arr


def nparray_to_image(arr):
    """Convert nparray to Darknet image struct.
    Args:
        arr: nparray containing source image in BGR color model.

    Returns:
        Darknet image struct, whose data is a C array
        containing flatten image in BGR color model.
    """
    arr = arr.transpose(2,0,1)
    c = arr.shape[0]
    h = arr.shape[1]
    w = arr.shape[2]
    arr = (arr/255.0).flatten()
    data = c_array(c_float, arr)
    im = IMAGE(w, h, c, data)
    rgbgr_image(im)
    return im


def detect_np(net, meta, np_img, thresh=.3, hier_thresh=.5, nms=.45):
    im = nparray_to_image(np_img)
    boxes = make_boxes(net)
    probs = make_probs(net)
    num = num_boxes(net)
    t_start = time.time()
    network_detect(net, im, thresh, hier_thresh, nms, boxes, probs)
    t_end = time.time()
    logger.debug('inference time: {} s'.format(t_end - t_start))
    res = []
    for j in range(num):
        for i in range(meta.classes):
            if probs[j][i] > 0:
                res.append(
                    {
                        'type': 'detection',
                        'label': meta.names[i].decode('utf-8'),
                        'confidence': probs[j][i],
                        'left': boxes[j].x - (boxes[j].w / 2),
                        'top': boxes[j].y - (boxes[j].h / 2),
                        'right': boxes[j].x + (boxes[j].w / 2),
                        'bottom': boxes[j].y + (boxes[j].h / 2),
                        'id': -1
                    }
                )
    free_ptrs(cast(probs, POINTER(c_void_p)), num)
    return res


class DarknetEngine(DLEngine):
    # FIXME: Get model information by model manager
    def __init__(self, config, model, meta=''):
        super(DarknetEngine, self).__init__()

        self.net = load_net(config, model, 0)
        self.meta = load_meta(meta)
        self.classes = self.meta.classes
        self.labels = [self.meta.names[i].decode('utf-8')
                       for i in range(self.classes)]

        # Warmup
        zero_image = np.zeros(shape=(416, 416, 3), dtype=np.uint8)
        detect_np(self.net, self.meta, zero_image)

    def process_input(self, rgb_array):
        return rgb_array

    def inference(self, tensor):
        return detect_np(self.net, self.meta, tensor)

    def process_output(self, output):
        return {'annotations': output}


if __name__ == '__main__':
    engine = DarknetEngine(
        config=b'/usr/share/dlmodels/tinyyolovoc-20170816/tiny-yolo-voc.cfg',
        model=b'/usr/share/dlmodels/tinyyolovoc-20170816/tiny-yolo-voc.weights',
        meta=b'/usr/share/dlmodels/tinyyolovoc-20170816/voc.data'
    )
    im = cv2.imread('data/dog.jpg')
    for i in range(3):
        r = engine.inference(im)
        print(r)
