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

"""TensorFlow inference engine.
"""

from __future__ import print_function

import argparse
import json

import numpy as np
import caffe

from berrynet import logger
#from berrynet.dlmodelmgr import DLModelManager
from berrynet.engine import DLEngine


class CaffeEngine(DLEngine):
    # FIXME: Get model information by model manager
    def __init__(self, model_def, pretrained_model, mean_file, label, image_dims = [256,256], channel_swap=[2,1,0], raw_scale=255.0, top_k=5):
        super(CaffeEngine, self).__init__()

        # Load model
        caffe.set_mode_cpu()
        self.classifier = caffe.Classifier(model_def, pretrained_model, image_dims=image_dims, mean=mean_file, raw_scale=raw_scale, channel_swap=channel_swap)
        
        # Load labels
        self.labels = [line.rstrip() for line in open(label)]

        self.top_k = top_k

    def create(self):
        pass

    def process_input(self, rgb_array):
        self.inputs = rgb_array
        return self.inputs
    
    def inference(self, tensor):
        self.predictions = self.classifier.predict(self.inputs, False)
        return self.predictions

    def process_output(self, output):
        predictions_list = self.predictions[0].tolist()
        data = zip(predictions_list, caffe_labels)
        processed_output = {'annotations': []}
        i=0
        for d in sorted(data, reverse=True):
            human_string = d[1]
            score = d[0]
            anno = {
                'type': 'classification',
                'label': human_string,
                'confidence': score
            }
            processed_output['annotations'].append(anno)
            i = i + 1
            if (i >= self.top_k):
                break
        return processed_output

    def save_cache(self):
        pass
