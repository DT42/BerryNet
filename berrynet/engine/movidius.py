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
    top_inds = output.argsort()[::-1][:5]
    return [(labels[top_inds[i]], output[top_inds[i]]) for i in range(5)]


def print_inceptionv3_output(output, labels):
    top_inds = output.argsort()[::-1][:5]

    for i in range(5):
        print(top_inds[i], labels[top_inds[i]], output[top_inds[i]])


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
