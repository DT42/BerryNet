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

"""Movidius inference engine.
"""

from __future__ import print_function

import argparse
import logging

import movidius as mv
from engineservice import EngineService
from engineservice import DLEngine
from dlmodelmgr import DLModelManager


class MovidiusEngine(DLEngine):
    def __init__(self, model, label):
        super(MovidiusEngine, self).__init__()
        self.mvng = mv.MovidiusNeuralGraph(model, label)

    def process_input(self, tensor):
        return mv.process_inceptionv3_input(tensor)

    def inference(self, tensor):
        return self.mvng.inference(tensor)

    def process_output(self, output):
        return mv.process_inceptionv3_output(
                   output,
                   self.mvng.get_labels())

    def save_cache(self):
        with open(self.cache['model_output_filepath'], 'w') as f:
            for i in self.cache['model_output']:
                print("%s (score = %.5f)" % (i[0], i[1]), file=f)


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
    logging.debug('model filepath: ' + args['model'])
    logging.debug('label filepath: ' + args['label'])
    logging.debug('image_dir: ' + args['image_dir'])

    movidius_engine = MovidiusEngine(args['model'], args['label'])
    engine_service = EngineService(args['service_name'], movidius_engine)
    engine_service.run(args)
