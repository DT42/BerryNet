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

"""
Deep learning engine template provides unified interfaces for
different backends (e.g. LiteRT, ONNX Runtime, etc.)
"""

import ast
import json
import re
import zipfile

import cv2
import numpy as np


class DLEngine(object):
    def __init__(self):
        self.model_input_cache = []
        self.model_output_cache = []
        self.cache = {
            'model_input': [],
            'model_output': '',
            'model_output_filepath': ''
        }

    def create(self):
        # Hook for initialization that has to happen in the service
        # process, after the engine instance is passed to the service.
        pass

    def process_input(self, tensor):
        return tensor

    def inference(self, tensor):
        output = None
        return output

    def process_output(self, output):
        return output

    def cache_data(self, key, value):
        self.cache[key] = value

    def save_cache(self):
        with open(self.cache['model_output_filepath'], 'w') as f:
            f.write(str(self.cache['model_output']))


def load_labels(path):
    """Load one label per line.

    ImageNet synset lines such as "n01440764 tench, Tinca tinca" are
    reduced to their first name, "tench".
    """
    labels = []
    with open(path, 'r') as f:
        for line in f:
            label = line.strip()
            if re.match(r'n\d{8} ', label):
                label = label.split(' ', 1)[1].split(',')[0].strip()
            labels.append(label)
    return labels


def classification_annotations(scores, labels, top_k):
    """Annotations of the top K classes, highest score first."""
    top_k_index = scores.argsort()[-top_k:][::-1]
    return [{
        'type': 'classification',
        'label': labels[i],
        'confidence': float(scores[i])
    } for i in top_k_index]


def detection_annotations(boxes, classes, scores, num, labels, threshold,
                          img_w, img_h, label_offset=0):
    """Annotations of SSD-style detections.

    Args:
        boxes: Normalized [ymin, xmin, ymax, xmax] boxes.
        classes: Class index of each box; label_offset is added to it to
            get the label index.
        scores: Confidence of each box.
        num: Number of valid detections.
        img_w, img_h: Size of the original image.
    """
    annotations = []
    for i in range(min(int(num), len(scores))):
        if scores[i] < threshold:
            continue
        ymin, xmin, ymax, xmax = boxes[i].tolist()
        annotations.append({
            'label': labels[int(classes[i]) + label_offset],
            'confidence': float(scores[i]),
            'left': int(xmin * img_w),
            'top': int(ymin * img_h),
            'right': int(xmax * img_w),
            'bottom': int(ymax * img_h)
        })
    return annotations


def non_max_suppression(boxes, scores, iou_threshold):
    """Greedy non-maximum suppression.

    Args:
        boxes: [ymin, xmin, ymax, xmax] or [x1, y1, x2, y2] boxes.
        scores: Score of each box.

    Returns:
        Indexes of the kept boxes, highest score first.
    """
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        rest = order[1:]
        ymin = np.maximum(boxes[i, 0], boxes[rest, 0])
        xmin = np.maximum(boxes[i, 1], boxes[rest, 1])
        ymax = np.minimum(boxes[i, 2], boxes[rest, 2])
        xmax = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(ymax - ymin, 0, None) * np.clip(xmax - xmin, 0, None)
        iou = inter / np.maximum(areas[i] + areas[rest] - inter, 1e-9)
        order = rest[iou <= iou_threshold]
    return np.array(keep, dtype=int)


def batched_non_max_suppression(boxes, scores, classes, iou_threshold):
    """Non-maximum suppression of each class.

    Boxes of different classes are moved apart, so that one
    non_max_suppression() call only suppresses boxes of the same class.

    Returns:
        Indexes of the kept boxes, highest score first.
    """
    if len(boxes) == 0:
        return np.array([], dtype=int)
    offsets = classes[:, np.newaxis] * (np.abs(boxes).max() + 1)
    return non_max_suppression(boxes + offsets, scores, iou_threshold)


def letterbox(bgr_array, height, width):
    """Resize an image into height x width keeping its aspect ratio, and
    pad the borders with gray, the same as Ultralytics YOLO.

    Returns:
        RGB image, scale, and (left, top) padding.
    """
    img_h, img_w = bgr_array.shape[:2]
    scale = min(height / img_h, width / img_w)
    new_w, new_h = int(round(img_w * scale)), int(round(img_h * scale))
    pad_w, pad_h = (width - new_w) / 2, (height - new_h) / 2
    top, bottom = int(round(pad_h - 0.1)), int(round(pad_h + 0.1))
    left, right = int(round(pad_w - 0.1)), int(round(pad_w + 0.1))
    rgb = cv2.cvtColor(bgr_array, cv2.COLOR_BGR2RGB)
    if (new_w, new_h) != (img_w, img_h):
        rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    rgb = cv2.copyMakeBorder(rgb, top, bottom, left, right,
                             cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return rgb, scale, (left, top)


def yolo_detections(output, input_h, input_w, threshold, iou_threshold,
                    max_detections=300):
    """Decode the output of an Ultralytics YOLO detector.

    End-to-end models such as YOLO26 output (1, detections, 6) after NMS,
    as [x1, y1, x2, y2, score, class]. Models such as YOLO11 and YOLOv8
    output (1, 4 + classes, anchors) before NMS, as [x, y, w, h, scores of
    each class]. Coordinates are in input pixels, or normalized to [0, 1].

    Returns:
        [x1, y1, x2, y2] boxes in input pixels, class indexes and scores,
        highest score first.
    """
    pred = output[0].astype(np.float32)
    if pred.shape[1] == 6 and pred.shape[0] != 6:
        boxes, scores, classes = pred[:, :4], pred[:, 4], pred[:, 5]
        keep = scores >= threshold
        boxes, scores = boxes[keep], scores[keep]
        # Round dequantized class indexes of quantized models.
        classes = np.rint(classes[keep]).astype(int)
    else:
        pred = pred.T
        classes = pred[:, 4:].argmax(axis=1)
        scores = pred[:, 4:].max(axis=1)
        keep = scores >= threshold
        xywh, classes, scores = pred[keep, :4], classes[keep], scores[keep]
        boxes = np.concatenate([xywh[:, :2] - xywh[:, 2:] / 2,
                                xywh[:, :2] + xywh[:, 2:] / 2], axis=1)
        keep = batched_non_max_suppression(boxes, scores, classes,
                                           iou_threshold)
        boxes, classes, scores = boxes[keep], classes[keep], scores[keep]
    order = scores.argsort()[::-1][:max_detections]
    boxes, classes, scores = boxes[order], classes[order], scores[order]
    if boxes.size and boxes.max() <= 2.0:
        boxes = boxes * np.array([input_w, input_h, input_w, input_h],
                                 dtype=np.float32)
    return boxes, classes, scores


def yolo_annotations(boxes, classes, scores, labels, scale, pad, img_w,
                     img_h):
    """Annotations of YOLO detections, mapped from the letterboxed input
    back to the original image.
    """
    annotations = []
    for box, class_id, score in zip(boxes, classes, scores):
        x1, y1, x2, y2 = box.tolist()
        left, top = pad
        annotations.append({
            'label': labels[int(class_id)],
            'confidence': float(score),
            'left': int(np.clip((x1 - left) / scale, 0, img_w)),
            'top': int(np.clip((y1 - top) / scale, 0, img_h)),
            'right': int(np.clip((x2 - left) / scale, 0, img_w)),
            'bottom': int(np.clip((y2 - top) / scale, 0, img_h))
        })
    return annotations


def ultralytics_labels(names):
    """Labels from the class names in Ultralytics model metadata, a dict
    or its string representation such as "{0: 'person', 1: 'bicycle'}".
    """
    if isinstance(names, str):
        names = ast.literal_eval(names)
    names = {int(k): v for k, v in names.items()}
    # Keep labels at their class indexes even if some are missing.
    return [names.get(i, str(i)) for i in range(max(names) + 1)]


def tflite_ultralytics_labels(model):
    """Labels from the metadata.json which Ultralytics appends to its
    exported .tflite models.
    """
    try:
        with zipfile.ZipFile(model) as archive:
            metadata = json.loads(archive.read('metadata.json'))
        return ultralytics_labels(metadata['names'])
    except (zipfile.BadZipFile, KeyError) as e:
        raise ValueError('{} has no class names of Ultralytics, give a label '
                         'file instead'.format(model)) from e
