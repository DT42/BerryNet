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

"""Engine service is a bridge between incoming data and inference engine.
"""


from __future__ import print_function

import argparse
import logging
import os
import time

from datetime import datetime

import cv2
import numpy as np

from berrynet.comm import Communicator
from berrynet.comm import payload
from berrynet.dlmodelmgr import DLModelManager


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
        # Workaround to posepone TensorFlow initialization.
        # If TF is initialized in __init__, and pass an engine instance
        # to engine service, TF session will stuck in run().
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


class EngineService(object):
    def __init__(self, service_name, engine, comm_config):
        self.service_name = service_name
        self.engine = engine
        self.comm_config = comm_config
        self.comm_config['subscribe']['data/rgbimage'] = self.inference
        self.comm = Communicator(self.comm_config, debug=True)

    def inference(self, pl):
        duration = lambda t: (datetime.now() - t).microseconds / 1000

        t = datetime.now()
        logging.debug('payload size: {}'.format(len(pl)))
        logging.debug('payload type: {}'.format(type(pl)))
        jpg_json = payload.deserialize_jpg(pl.decode('utf-8'))
        jpg_bytes = payload.destringify_jpg(jpg_json['bytes'])
        logging.debug('destringify_jpg: {} ms'.format(duration(t)))

        t = datetime.now()
        rgb_array = payload.jpg2rgb(jpg_bytes)
        logging.debug('jpg2rgb: {} ms'.format(duration(t)))

        t = datetime.now()
        image_data = self.engine.process_input(rgb_array)
        output = self.engine.inference(image_data)
        model_outputs = self.engine.process_output(output)
        logging.debug('Result: {}'.format(model_outputs))
        logging.debug('Classification takes {} ms'.format(duration(t)))

        #self.engine.cache_data('model_output', model_outputs)
        #self.engine.cache_data('model_output_filepath', output_name)
        #self.engine.save_cache()

    def run(self, args):
        """Infinite loop serving inference requests"""
        self.engine.create()
        self.comm.run()


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model',
                    help='Model file path')
    ap.add_argument('--label',
                    help='Label file path')
    ap.add_argument('--model_package',
                    default='',
                    help='Model package name')
    ap.add_argument('--service_name', required=True,
                    help='Engine service name used as PID filename')
    ap.add_argument('--num_top_predictions', default=5,
                    help='Display this many predictions')
    return vars(ap.parse_args())


if __name__ == '__main__':
    # Test Movidius engine
    #import movidius as mv

    #logging.basicConfig(level=logging.DEBUG)
    #args = parse_args()
    #if args['model_package'] != '':
    #    dlmm = DLModelManager()
    #    meta = dlmm.get_model_meta(args['model_package'])
    #    args['model'] = meta['model']
    #    args['label'] = meta['label']
    #logging.debug('model filepath: ' + args['model'])
    #logging.debug('label filepath: ' + args['label'])
    #logging.debug('image_dir: ' + args['image_dir'])

    #mvng = mv.MovidiusNeuralGraph(args['model'], args['label'])
    #engine_service = EngineService(args['service_name'], mvng)
    #engine_service.run(args)

    # Test TensorFlow engine
    from berrynet.engine.tensorflow_engine import TensorFlowEngine

    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    logging.debug('model filepath: ' + args['model'])
    logging.debug('label filepath: ' + args['label'])

    model = 'berrynet/engine/inception_v3_2016_08_28_frozen.pb'
    label = 'berrynet/engine/imagenet_slim_labels.txt'
    jpg_filepath = 'berrynet/engine/grace_hopper.jpg'
    input_layer = 'input:0'
    output_layer = 'InceptionV3/Predictions/Reshape_1:0'

    tfe = TensorFlowEngine(model, label, input_layer, output_layer)
    comm_config = {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
    engine_service = EngineService(args['service_name'],
                                   tfe,
                                   comm_config)
    engine_service.run(args)
