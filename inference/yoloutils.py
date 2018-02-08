import os
import sys
import time

from datetime import datetime

import cv2
import numpy as np

from mvnc import mvncapi as mvnc
from skimage.transform import resize


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


def process_yolo_output(img, results):
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
    cv2.imwrite('/tmp/yolo_result.jpg', img_cp)


def process_yolo_input(rgb_data):
    input_dim = (448, 448)
    tmp_data = rgb_data.copy()
    tmp_data = resize(tmp_data / 255.0, input_dim, 1)
    tmp_data[:, :, (2, 1, 0)]  # BGR2RGB
    input_data = tmp_data.astype(np.float16)
    return input_data


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
        print('\tconfidence = {conf}'.format(conf=str(results[i][5])))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print ("YOLOv1 Tiny example: python3 py_examples/yolo_example.py images/dog.jpg")
        sys.exit()

    network_blob='/home/pi/codes/yoloNCS/graph'
    # configuration NCS
    mvnc.SetGlobalOption(mvnc.GlobalOption.LOG_LEVEL, 2)
    devices = mvnc.EnumerateDevices()
    if len(devices) == 0:
        print('No devices found')
        quit()
    device = mvnc.Device(devices[0])
    device.OpenDevice()
    opt = device.GetDeviceOption(mvnc.DeviceOption.OPTIMISATION_LIST)
    # load blob
    with open(network_blob, mode='rb') as f:
        blob = f.read()
    graph = device.AllocateGraph(blob)
    graph.SetGraphOption(mvnc.GraphOption.ITERATIONS, 1)
    iterations = graph.GetGraphOption(mvnc.GraphOption.ITERATIONS)

    # image preprocess
    img = cv2.imread(sys.argv[1])
    input_data = process_yolo_input(img)

    # start MOD
    start = datetime.now()
    graph.LoadTensor(input_data, 'user object')
    out, userobj = graph.GetResult()
    end = datetime.now()
    elapsedTime = end-start
    print('total time is " milliseconds', elapsedTime.total_seconds()*1000)

    # fc27 instead of fc12 for yolo_small
    results = interpret_yolo_output(out,
                                    img.shape[1],
                                    img.shape[0])
    #print (results)
    #cv2.imshow('YOLO detection',img_cv)
    process_yolo_output(img, results)
    #cv2.waitKey(10000)

    graph.DeallocateGraph()
    device.CloseDevice()
