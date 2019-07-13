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
from berrynet.engine.openvino_engine import OpenVINOClassifierEngine
from berrynet.engine.openvino_engine import OpenVINODetectorEngine
from berrynet.service import EngineService
from berrynet.utils import draw_bb
from berrynet.utils import generate_class_color


class OpenVINOClassifierService(EngineService):
    def __init__(self, service_name, engine, comm_config, draw=False):
        super(OpenVINOClassifierService, self).__init__(service_name,
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

        #classes = self.engine.classes
        #labels = self.engine.labels

        logger.debug('draw = {}'.format(self.draw))
        if self.draw is False:
            self.result_hook(self.generalize_result(jpg_json, model_outputs))
        else:
            #self.result_hook(
            #    draw_bb(bgr_array,
            #            self.generalize_result(jpg_json, model_outputs),
            #            generate_class_color(class_num=classes),
            #            labels))
            self.result_hook(self.generalize_result(jpg_json, model_outputs))

    def result_hook(self, generalized_result):
        logger.debug('result_hook, annotations: {}'.format(generalized_result['annotations']))
        self.comm.send('berrynet/engine/ovclassifier/result',
                       payload.serialize_payload(generalized_result))


class OpenVINODetectorService(EngineService):
    def __init__(self, service_name, engine, comm_config, draw=False):
        super(OpenVINODetectorService, self).__init__(service_name,
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

        classes = len(self.engine.labels_map)
        labels = self.engine.labels_map

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
        self.comm.send('berrynet/engine/ovdetector/result',
                       payload.serialize_payload(generalized_result))


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '-s', '--service',
        help=('Classifier or Detector service. '
              'classifier, or detector is acceptable. '
              '(classifier by default)'),
        default='classifier',
        type=str)
    ap.add_argument(
        '--service_name',
        default='openvino_classifier',
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
        '--top_k',
        help='Display top K classification results.',
        default=3,
        type=int)
    ap.add_argument(
        '-d', '--device',
        help='Specify the target device to infer on; CPU, GPU, FPGA or MYRIAD is acceptable. Sample will look for a suitable plugin for device specified (CPU by default)',
        default='CPU',
        type=str)
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
    # Test OpenVINO classifier engine
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

    if args['service'] == 'classifier':
        engine = OpenVINOClassifierEngine(
                     model = args['model'],
                     labels = args['label'],
                     top_k = args['top_k'],
                     device = args['device'])
        service_functor = OpenVINOClassifierService
    elif args['service'] == 'detector':
        engine = OpenVINODetectorEngine(
                     model = args['model'],
                     labels = args['label'],
                     device = args['device'])
        service_functor = OpenVINODetectorService
    else:
        raise Exception('Illegal service {}, it should be '
                        'classifier or detector'.format(args['service']))

    engine_service = service_functor(args['service_name'],
                                     engine,
                                     comm_config,
                                     draw=args['draw'])
    engine_service.run(args)


if __name__ == '__main__':
    main()
