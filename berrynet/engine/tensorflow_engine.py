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

import cv2
import numpy as np
import tensorflow as tf

from berrynet import logger
#from berrynet.dlmodelmgr import DLModelManager
from berrynet.engine import DLEngine


class TensorFlowEngine(DLEngine):
    # FIXME: Get model information by model manager
    def __init__(self, model, label, input_layer, output_layer, top_k=3):
        super(TensorFlowEngine, self).__init__()

        # Load model
        with tf.gfile.FastGFile(model, 'rb') as f:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(f.read())
            _ = tf.import_graph_def(graph_def, name='')

        # Load labels
        self.labels = [line.rstrip() for line in tf.gfile.FastGFile(label)]

        # Load other configs
        self.input_layer = input_layer
        self.output_layer = output_layer
        self.top_k = top_k

        # NOTE: Do NOT call read_tensor_from_nparray twice to prevent from
        #       recreating unexpected placeholders.
        self.tensor_op = self.read_tensor_from_nparray(
            input_height=299,
            input_width=299,
            input_mean=0,
            input_std=255)

    def create(self):
        # Create session
        self.sess = tf.Session()

    def process_input(self, rgb_array):
        return self.sess.run(self.tensor_op,
                             feed_dict={'inarray:0': rgb_array})

    def inference(self, tensor):
        return self.sess.run(self.output_layer,
                             {self.input_layer: tensor})

    def process_output(self, output):
        processed_output = {'annotations': []}
        decimal_digits = 2
        predictions = np.squeeze(output)
        top_k_index = predictions.argsort()[-self.top_k:][::-1]

        for node_id in top_k_index:
            human_string = self.labels[node_id]
            score = round(float(predictions[node_id]), decimal_digits)
            anno = {
                'type': 'classification',
                'label': human_string,
                'confidence': score
            }
            processed_output['annotations'].append(anno)
            logger.debug('%s (score = %.5f)' % (human_string, score))
        return processed_output

    def save_cache(self):
        pass

    # NOTE: Copied from trainer.component
    def read_tensor_from_nparray(self, input_height=192, input_width=192,
                                 input_mean=0, input_std=255):
        """ Create normalized tensor based on input numpy array """
        image_reader = tf.placeholder(tf.uint8, name='inarray')
        float_caster = tf.cast(image_reader, tf.float32)
        dims_expander = tf.expand_dims(float_caster, 0)
        resized = tf.image.resize_bilinear(dims_expander,
                                           [input_height, input_width])
        normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])
        return normalized
