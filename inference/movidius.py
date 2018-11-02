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
from skimage.transform import resize


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


def interpret_yolo_output(output, img_width, img_height):
    output = output.astype(np.float32)

    classes = [
        'aeroplane', 'bicycle', 'bird', 'boat', 'bottle',
        'bus', 'car', 'cat', 'chair', 'cow',
        'diningtable', 'dog', 'horse', 'motorbike', 'person',
        'pottedplant', 'sheep', 'sofa', 'train','tvmonitor'
    ]
    threshold = 0.2
    iou_threshold = 0.5
    num_class = 20
    num_box = 2
    grid_size = 7
    probs = np.zeros((7, 7, 2, 20))
    class_probs = (np.reshape(output[0:980], (7, 7, 20)))  #.copy()
    scales = (np.reshape(output[980:1078], (7, 7, 2)))  #.copy()
    boxes = (np.reshape(output[1078:], (7, 7, 2, 4)))  #.copy()
    offset = np.transpose(
        np.reshape(np.array([np.arange(7)] * 14), (2, 7, 7)),
        (1, 2, 0)
    )
    #boxes.setflags(write=1)
    boxes[:, :, :, 0] += offset
    boxes[:, :, :, 1] += np.transpose(offset, (1, 0, 2))
    boxes[:, :, :, 0:2] = boxes[:, :, :, 0:2] / 7.0
    boxes[:, :, :, 2] = np.multiply(boxes[:, :, :, 2], boxes[:, :, :, 2])
    boxes[:, :, :, 3] = np.multiply(boxes[:, :, :, 3], boxes[:, :, :, 3])

    boxes[:, :, :, 0] *= img_width
    boxes[:, :, :, 1] *= img_height
    boxes[:, :, :, 2] *= img_width
    boxes[:, :, :, 3] *= img_height

    for i in range(2):
        for j in range(20):
            probs[:, :, i, j] = np.multiply(class_probs[:, :, j],
                                            scales[:, :, i])
    #print (probs)
    filter_mat_probs = np.array(probs >= threshold, dtype='bool')
    filter_mat_boxes = np.nonzero(filter_mat_probs)
    boxes_filtered = boxes[filter_mat_boxes[0],
                           filter_mat_boxes[1],
                           filter_mat_boxes[2]]
    probs_filtered = probs[filter_mat_probs]
    classes_num_filtered = np.argmax(probs, axis=3)[filter_mat_boxes[0],
                                                    filter_mat_boxes[1],
                                                    filter_mat_boxes[2]]

    argsort = np.array(np.argsort(probs_filtered))[::-1]
    boxes_filtered = boxes_filtered[argsort]
    probs_filtered = probs_filtered[argsort]
    classes_num_filtered = classes_num_filtered[argsort]

    for i in range(len(boxes_filtered)):
        if probs_filtered[i] == 0:
            continue
        for j in range(i + 1, len(boxes_filtered)):
            if iou(boxes_filtered[i], boxes_filtered[j]) > iou_threshold:
                probs_filtered[j] = 0.0

    filter_iou = np.array(probs_filtered > 0.0, dtype='bool')
    boxes_filtered = boxes_filtered[filter_iou]
    probs_filtered = probs_filtered[filter_iou]
    classes_num_filtered = classes_num_filtered[filter_iou]

    result = []
    for i in range(len(boxes_filtered)):
        result.append([classes[classes_num_filtered[i]],
                       boxes_filtered[i][0],
                       boxes_filtered[i][1],
                       boxes_filtered[i][2],
                       boxes_filtered[i][3],
                       probs_filtered[i]])

    return result


def iou(box1, box2):
    tb = (min(box1[0] + 0.5 * box1[2], box2[0] + 0.5 * box2[2]) -
          max(box1[0] - 0.5 * box1[2], box2[0] - 0.5 * box2[2]))
    lr = (min(box1[1] + 0.5 * box1[3], box2[1] + 0.5 * box2[3]) -
          max(box1[1] - 0.5 * box1[3], box2[1] - 0.5 * box2[3]))
    if tb < 0 or lr < 0:
        intersection = 0
    else:
        intersection =  tb*lr
    return intersection / (box1[2] * box1[3] + box2[2] * box2[3] - intersection)


def process_yolo_output(img, results, img_filepath):
    img_width = img.shape[1]
    img_height = img.shape[0]
    img_cp = img.copy()

    print_yolo_output(results)

    # draw bounding boxes on input image
    for i in range(len(results)):
        x = int(results[i][1])
        y = int(results[i][2])
        w = int(results[i][3]) // 2
        h = int(results[i][4]) // 2
        xmin = x - w
        xmax = x + w
        ymin = y - h
        ymax = y + h
        if xmin < 0:
            xmin = 0
        if ymin < 0:
            ymin = 0
        if xmax > img_width:
            xmax = img_width
        if ymax > img_height:
            ymax = img_height
        cv2.rectangle(img_cp,
                      (xmin, ymin),
                      (xmax, ymax),
                      (0, 255, 0),
                      2)
        cv2.rectangle(img_cp,
                      (xmin, ymin - 20),
                      (xmax, ymin),
                      (125, 125, 125),
                      -1)
        cv2.putText(img_cp,results[i][0] + ' : %.2f' % results[i][5],
                    (xmin + 5, ymin - 7),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1)
    save_yolo_output_image(img_filepath, img_cp)
    return results


def process_yolo_input(rgb_data):
    from datetime import datetime
    input_dim = (448, 448)

    t_start = datetime.now()
    tmp_data = rgb_data.copy()
    t_end = datetime.now()
    t_pass = t_end - t_start
    print('copy: {} ms'.format(t_pass.total_seconds() * 1000))

    t_start = datetime.now()
    #tmp_data = resize(tmp_data / 255.0, input_dim, 1)  # ~270 ms
    tmp_data = cv2.resize(tmp_data / 255.0, input_dim)  # ~65 ms
    t_end = datetime.now()
    t_pass = t_end - t_start
    print('resize: {} ms'.format(t_pass.total_seconds() * 1000))

    t_start = datetime.now()
    tmp_data[:, :, (2, 1, 0)]  # BGR2RGB
    t_end = datetime.now()
    t_pass = t_end - t_start
    print('BGR2RGB: {} ms'.format(t_pass.total_seconds() * 1000))

    t_start = datetime.now()
    input_data = tmp_data.astype(np.float16)
    t_end = datetime.now()
    t_pass = t_end - t_start
    print('astype: {} ms'.format(t_pass.total_seconds() * 1000))

    return input_data


def save_yolo_output_text(text_filepath, output):
    with open(text_filepath, 'w') as f:
        f.write(str(output))


def save_yolo_output_image(image_filepath, image_data):
    cv2.imwrite(image_filepath, image_data)


def print_yolo_output(output):
    for i in range(len(output)):
        x = int(output[i][1])
        y = int(output[i][2])
        #w = int(output[i][3]) // 2
        #h = int(output[i][4]) // 2
        print('\tclass = {label}'.format(label=output[i][0]))
        print('\t[x, y, w, h] = [{x}, {y}, {w}, {h}]'.format(
            x=str(x),
            y=str(y),
            w=str(int(output[i][3])),
            h=str(int(output[i][4]))))
        print('\tconfidence = {conf}'.format(conf=str(output[i][5])))


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
