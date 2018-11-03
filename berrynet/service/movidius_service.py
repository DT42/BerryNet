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

import argparse
import logging

from datetime import datetime

from berrynet import logger
from berrynet.comm import payload
from berrynet.dlmodelmgr import DLModelManager
from berrynet.engine.movidius_engine import MovidiusEngine
from berrynet.engine.movidius_engine import MovidiusMobileNetSSDEngine
from berrynet.service import EngineService
from berrynet.utils import draw_bb
from berrynet.utils import generate_class_color


class MovidiusClassificationService(EngineService):
    def __init__(self, service_name, engine, comm_config):
        super(MovidiusClassificationService, self).__init__(service_name,
                                                            engine,
                                                            comm_config)

    def result_hook(self, generalized_result):
        logger.debug('result_hook, annotations: {}'.format(generalized_result['annotations']))
        self.comm.send('berrynet/engine/mvclassification/result',
                       payload.serialize_payload(generalized_result))


class MovidiusMobileNetSSDService(EngineService):
    def __init__(self, service_name, engine, comm_config, draw=False):
        super(MovidiusMobileNetSSDService, self).__init__(service_name,
                                                          engine,
                                                          comm_config)
        self.draw = draw

    def inference(self, pl):
        duration = lambda t: (datetime.now() - t).microseconds / 1000

        t = datetime.now()
        logger.debug('payload size: {}'.format(len(pl)))
        logger.debug('payload type: {}'.format(type(pl)))
        jpg_json = payload.deserialize_payload(pl.decode('utf-8'))
        jpg_bytes = payload.destringify_jpg(jpg_json['bytes'])
        logger.debug('destringify_jpg: {} ms'.format(duration(t)))

        t = datetime.now()
        bgr_array = payload.jpg2bgr(jpg_bytes)
        logger.debug('jpg2bgr: {} ms'.format(duration(t)))

        t = datetime.now()
        image_data = self.engine.process_input(bgr_array)
        output = self.engine.inference(image_data)
        model_outputs = self.engine.process_output(output)
        logger.debug('Result: {}'.format(model_outputs))
        logger.debug('Detection takes {} ms'.format(duration(t)))

        classes = self.engine.classes
        labels = self.engine.labels

        logger.debug('draw = {}'.format(self.draw))
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
        self.comm.send('berrynet/engine/mvmobilenetssd/result',
                       payload.serialize_payload(generalized_result))


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
                    help='Valid value: Classification, MobileNetSSD')
    ap.add_argument('--num_top_predictions', default=5,
                    help='Display this many predictions')
    ap.add_argument('--draw',
                    action='store_true',
                    help='Draw bounding boxes on image in result')
    ap.add_argument('--debug',
                    action='store_true',
                    help='Debug mode toggle')
    return vars(ap.parse_args())


def main():
    # Test Movidius engine
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

    comm_config = {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
    if args['service_name'] == 'Classification':
        mvng = MovidiusEngine(args['model'], args['label'])
        service_functor = MovidiusClassificationService
    elif args['service_name'] == 'MobileNetSSD':
        mvng = MovidiusMobileNetSSDEngine(args['model'], args['label'])
        service_functor = MovidiusMobileNetSSDService
    else:
        logger.critical('Legal service names are Classification, MobileNetSSD')
    engine_service = service_functor(args['service_name'],
                                     mvng,
                                     comm_config,
                                     draw=args['draw'])
    engine_service.run(args)


if __name__ == '__main__':
    main()
