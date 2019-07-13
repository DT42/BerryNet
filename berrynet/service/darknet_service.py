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

"""Engine service is a bridge between incoming data and inference engine.
"""

import argparse
import logging
import math

import cv2

from berrynet import logger
from berrynet.comm import payload
from berrynet.dlmodelmgr import DLModelManager
from berrynet.engine.darknet_engine import DarknetEngine
from berrynet.service import EngineService
from berrynet.utils import generate_class_color
from berrynet.utils import draw_bb


class DarknetService(EngineService):
    def __init__(self, service_name, engine, comm_config, draw=False):
        super(DarknetService, self).__init__(service_name,
                                                engine,
                                                comm_config)
        self.draw = draw

    def inference(self, pl):
        jpg_json = payload.deserialize_payload(pl.decode('utf-8'))
        jpg_bytes = payload.destringify_jpg(jpg_json['bytes'])

        bgr_array = payload.jpg2bgr(jpg_bytes)

        image_data = self.engine.process_input(bgr_array)
        output = self.engine.inference(image_data)
        model_outputs = self.engine.process_output(output)

        classes = self.engine.classes
        labels = self.engine.labels

        if self.draw is False:
            self.result_hook(self.generalize_result(jpg_json, model_outputs))
        else:
            self.result_hook(
                draw_bb(bgr_array,
                        self.generalize_result(jpg_json, model_outputs),
                        generate_class_color(class_num=classes),
                        labels))

    def result_hook(self, generalized_result):
        logger.debug('result_hook, annotations: {}'.format(generalized_result['annotations']))
        self.comm.send('berrynet/engine/darknet/result',
                       payload.serialize_payload(generalized_result))


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--service_name',
        default='darknet',
        help='Human-readable service name for service management.')
    ap.add_argument(
        '-m', '--model',
        help='Model file path')
    ap.add_argument(
        '-l', '--label',
        help='Label file path')
    ap.add_argument(
        '-p', '--model_package',
        default='',
        help='Model package name. Find model and label file paths automatically.')
    ap.add_argument(
        '--draw',
        action='store_true',
        help='Draw bounding boxes on image in result')
    ap.add_argument(
        '--debug',
        action='store_true',
        help='Debug mode toggle')
    return vars(ap.parse_args())


def main():
    args = parse_args()
    if args['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    if args['model_package'] != '':
        dlmm = DLModelManager()
        meta = dlmm.get_model_meta(args['model_package'])
        args['model'] = meta['model']
        args['label'] = meta['label']
    logger.debug('model filepath: ' + args['model'])
    logger.debug('label filepath: ' + args['label'])

    engine = DarknetEngine(
        config=meta['config']['config'].encode('utf-8'),
        model=args['model'].encode('utf-8'),
        meta=meta['config']['meta'].encode('utf-8')
    )
    comm_config = {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
    engine_service = DarknetService(args['service_name'],
                                    engine,
                                    comm_config,
                                    args['draw'])
    engine_service.run(args)


if __name__ == '__main__':
    main()
