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

"""Darkflow inference engine.
"""

from __future__ import print_function

import argparse
import logging

import cv2

from darkflow.net.build import TFNet
from engineservice import EngineService
from engineservice import DLEngine
from dlmodelmgr import DLModelManager


# FIXME: Make these variables configurable
SystemSnapshot = '/usr/local/berrynet/dashboard/www/freeboard/snapshot.jpg'


class DarkflowEngine(DLEngine):
    def __init__(self, model, label, config):
        super(DarkflowEngine, self).__init__()
        self.engine_options = {
            'model': config,
            'load': model,
            #'model': "cfg/tiny-yolo.cfg",
            #'load': "bin/tiny-yolo.weights",
            'verbalise': True,
            "threshold": 0.1
        }

    def create(self):
        self.tfnet = TFNet(self.engine_options)

    def inference(self, tensor):
        return self.tfnet.return_predict(tensor)

    def save_cache(self):
        #with open(self.cache['model_output_filepath'], 'w') as f:
        #    f.write(str(self.cache['model_output']))
        drawBoundingBoxes(self.cache['model_input'],
                          #self.cache['model_output_filepath'] + '.jpg',
                          SystemSnapshot,
                          self.cache['model_output'],
                          self.tfnet.meta['colors'])


def drawBoundingBoxes(imageData, imageOutputPath, inferenceResults, colorMap):
    """Draw bounding boxes on an image.

    imageData: image data in numpy array format
    imageOutputPath: output image file path
    inferenceResults: Darkflow inference results
    colorMap: Bounding box color candidates, list of RGB tuples.
    """
    # TODO: return raw data instead of save image
    for res in inferenceResults:
        left = res['topleft']['x']
        top = res['topleft']['y']
        right = res['bottomright']['x']
        bottom = res['bottomright']['y']
        colorIndex = res['coloridx']
        color = colorMap[colorIndex]
        label = res['label']
        confidence = res['confidence']
        imgHeight, imgWidth, _ = imageData.shape
        thick = int((imgHeight + imgWidth) // 300)

        cv2.rectangle(imageData,(left, top), (right, bottom), color, thick)
        cv2.putText(imageData, label, (left, top - 12), 0, 1e-3 * imgHeight,
            color, thick//3)
    cv2.imwrite(imageOutputPath, imageData)
    logging.debug('Save bounding box result image to {}'.format(imageOutputPath))


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model',
                    help='Model file path')
    ap.add_argument('--label',
                    help='Label file path')
    ap.add_argument('--model_package',
                    default='',
                    help='Model package "name-version" naming')
    ap.add_argument('--image_dir', required=True,
                    help='Path to image file')
    ap.add_argument('--service_name', required=True,
                    help='Engine service name used as PID filename')
    ap.add_argument('--num_top_predictions', default=5,
                    help='Display this many predictions')
    return vars(ap.parse_args())


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    if args['model_package'] != '':
        dlmm = DLModelManager()
        meta = dlmm.get_model_meta(args['model_package'])
        args['model'] = meta['model']
        args['label'] = meta['label']
        args['config'] =  meta['config']['graph']
    logging.debug('model filepath: ' + args['model'])
    logging.debug('label filepath: ' + args['label'])
    logging.debug('image_dir: ' + args['image_dir'])

    darkflow_engine = DarkflowEngine(args['model'], args['label'], args['config'])
    engine_service = EngineService(args['service_name'], darkflow_engine)
    engine_service.run(args)

    # this code block works
    #import cv2
    #input_tensor = cv2.imread('/tmp/berrynet/dog.jpg')
    #tensor = darkflow_engine.process_input(input_tensor)
    #output = darkflow_engine.inference(tensor)
    #output = darkflow_engine.process_output(output)
