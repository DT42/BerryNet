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

import re


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
