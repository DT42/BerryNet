#!/usr/bin/python
#
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

import os

import cv2
import numpy as np

from mvnc import mvncapi as mvnc


class MovidiusNeuralGraph(object):
    def __init__(self, graph_filepath, label_filepath):
        # mvnc.SetGlobalOption(mvnc.GlobalOption.LOGLEVEL, 2)
        devices = mvnc.EnumerateDevices()
        if len(devices) == 0:
            raise Exception('No devices found')
        self.device = mvnc.Device(devices[0])
        self.device.OpenDevice()

        # Load graph
        with open(graph_filepath, mode='rb') as f:
            graphfile = f.read()
        self.graph = self.device.AllocateGraph(graphfile)

        # Load labels
        self.labels = []
        with open(label_filepath, 'r') as f:
            for line in f:
                label = line.split('\n')[0]
                if label != 'classes':
                    self.labels.append(label)
            f.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.graph.DeallocateGraph()
        self.device.CloseDevice()

    def inference(self, data):
        self.graph.LoadTensor(data.astype(np.float16), 'user object')
        output, userobj = self.graph.GetResult()
        return output

    def get_graph(self):
        return self.graph

    def get_labels(self):
        return self.labels


def process_inceptionv3_input(img):
    image_size = 299
    mean = 128
    std = 1.0/128

    dx, dy, dz = img.shape
    delta = float(abs(dy - dx))
    if dx > dy:  # crop the x dimension
        img = img[int(0.5*delta):dx-int(0.5*delta), 0:dy]
    else:
        img = img[0:dx, int(0.5*delta):dy-int(0.5*delta)]
    img = cv2.resize(img, (image_size, image_size))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    for i in range(3):
        img[:, :, i] = (img[:, :, i] - mean) * std
    return img


def process_inceptionv3_output(output, labels):
    processed_output = {'annotations': []}
    decimal_digits = 2
    top_k = 5
    top_inds = output.argsort()[::-1][:top_k]
    for i in range(top_k):
        human_string = labels[top_inds[i]]
        score = round(float(output[top_inds[i]]), decimal_digits)
        anno = {
            'type': 'classification',
            'label': human_string,
            'confidence': score
        }
        processed_output['annotations'].append(anno)
    return processed_output
    #return [(labels[top_inds[i]], output[top_inds[i]]) for i in range(5)]


def print_inceptionv3_output(output, labels):
    top_inds = output.argsort()[::-1][:5]

    for i in range(5):
        print(top_inds[i], labels[top_inds[i]], output[top_inds[i]])


def process_mobilenetssd_input(bgr_nparray):
    """Normalize MobileNet SSD input image.

    Args:
        img: Image nparray in BGR color model.

    Returns:
        Pre-processed image nparray in BGR color model.
    """
    img = cv2.resize(bgr_nparray, (300, 300))
    img = img - 127.5
    img = img * 0.007843
    return img


def process_mobilenetssd_output(output, img_w, img_h, labels, threshold=0.1):
    """
    More details about inference result format:
    https://github.com/movidius/ncappzoo/blob/master/caffe/SSD_MobileNet/run.py

    Args:
        output: Inference result returned by Graph.GetResult().
        img_w: Width of input image.
        img_h: Height of input image.
        labels:
        threshold:

    Returns:
        Annotations as dictionary, key is "annotations" and
        value a list of parsed results.

        Example:

            'annotations': [
                {
                    "label": "car",
                    "confidence": 0.93,
                    "left": 100,
                    "top": 100,
                    "right": 200,
                    "bottom": 200
                },
                ...
            ]
    """
    boxnum_index = 0
    result_index = 7
    result_size = 7
    num_valid_boxes = int(output[boxnum_index])
    annotations = []

    for i in range(num_valid_boxes):
        base_index = result_index + result_size * i
        result_objinfo = output[base_index:(base_index + result_size)]

        anno = {}
        anno['label'] = labels[int(result_objinfo[1])]
        anno['confidence'] = float(result_objinfo[2])
        anno['left'] = int(result_objinfo[3] * img_w)
        anno['top'] = int(result_objinfo[4] * img_h)
        anno['right'] = int(result_objinfo[5] * img_w)
        anno['bottom'] = int(result_objinfo[6] * img_h)

        if anno['confidence'] >= threshold:
            annotations.append(anno)

    return {'annotations': annotations}


if __name__ == '__main__':
    graph_filepath = ''  # model filepath
    label_filepath = ''  # label filepath
    path_to_images = ''  # image dirpath
    image_filenames = [os.path.join(path_to_images, image_name)
                       for image_name in []]  # image filename list

    movidius = MovidiusNeuralGraph(graph_filepath, label_filepath)
    labels = movidius.get_labels()

    print(''.join(['*' for i in range(79)]))
    print('inception-v3 on NCS')
    for image_filename in image_filenames:
        img = cv2.imread(image_filename).astype(np.float32)
        img = process_inceptionv3_input(img)
        print(''.join(['*' for i in range(79)]))
        print('Start download to NCS...')
        output = movidius.inference(img)
        print_inceptionv3_output(output, labels)

    print(''.join(['*' for i in range(79)]))
    print('Finished')
