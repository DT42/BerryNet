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
import os
import time

from datetime import datetime

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload
from berrynet.dlmodelmgr import DLModelManager
from berrynet.utils import draw_bb
from berrynet.utils import draw_label
from berrynet.utils import generate_class_color


class EngineService(object):
    def __init__(self, service_name, engine, comm_config):
        self.service_name = service_name
        self.engine = engine
        self.comm_config = comm_config
        for topic, functor in self.comm_config['subscribe'].items():
            self.comm_config['subscribe'][topic] = eval(functor)
        self.comm_config['subscribe']['berrynet/data/rgbimage'] = self.inference
        self.comm = Communicator(self.comm_config, debug=True)

    def inference(self, pl):
        duration = lambda t: (datetime.now() - t).microseconds / 1000

        t = datetime.now()
        logger.debug('payload size: {}'.format(len(pl)))
        logger.debug('payload type: {}'.format(type(pl)))
        jpg_json = payload.deserialize_payload(pl.decode('utf-8'))
        jpg_bytes = payload.destringify_jpg(jpg_json['bytes'])
        logger.debug('destringify_jpg: {} ms'.format(duration(t)))

        t = datetime.now()
        rgb_array = payload.jpg2rgb(jpg_bytes)
        logger.debug('jpg2rgb: {} ms'.format(duration(t)))

        t = datetime.now()
        image_data = self.engine.process_input(rgb_array)
        output = self.engine.inference(image_data)
        model_outputs = self.engine.process_output(output)
        logger.debug('Result: {}'.format(model_outputs))
        logger.debug('Classification takes {} ms'.format(duration(t)))

        #self.engine.cache_data('model_output', model_outputs)
        #self.engine.cache_data('model_output_filepath', output_name)
        #self.engine.save_cache()

        self.result_hook(self.generalize_result(jpg_json, model_outputs))

    def generalize_result(self, eng_input, eng_output):
        eng_input.update(eng_output)
        return eng_input

    def result_hook(self, generalized_result):
        logger.debug('base result_hook')

    def run(self, args):
        """Infinite loop serving inference requests"""
        self.engine.create()
        self.comm.run()


class ClassifierService(EngineService):
    """Classify images and publish the results to
    berrynet/engine/<service_name>/result.
    """

    def __init__(self, service_name, engine, comm_config, draw=False):
        super(ClassifierService, self).__init__(service_name,
                                                engine,
                                                comm_config)
        self.draw = draw
        self.result_topic = 'berrynet/engine/{}/result'.format(service_name)

    def inference(self, pl):
        t0 = time.time()
        logger.debug('payload size: {}'.format(len(pl)))
        jpg_json = payload.deserialize_payload(pl.decode('utf-8'))
        jpg_bytes = payload.destringify_jpg(jpg_json['bytes'])
        bgr_array = payload.jpg2bgr(jpg_bytes)
        logger.debug('Payload decoding takes {} s'.format(time.time() - t0))

        t1 = time.time()
        image_data = self.engine.process_input(bgr_array)
        output = self.engine.inference(image_data)
        model_outputs = self.engine.process_output(output)
        logger.debug('Result: {}'.format(model_outputs))
        logger.debug('Inference takes {} s'.format(time.time() - t1))

        result = self.generalize_result(jpg_json, model_outputs)
        logger.debug('draw = {}'.format(self.draw))
        if self.draw:
            result = self.draw_result(bgr_array, result)
        self.result_hook(result)

    def draw_result(self, bgr_array, result):
        return draw_label(bgr_array, result, (0, 255, 0))

    def result_hook(self, generalized_result):
        logger.debug('result_hook, annotations: {}'.format(
            generalized_result['annotations']))
        self.comm.send(self.result_topic,
                       payload.serialize_payload(generalized_result))


class DetectorService(ClassifierService):
    """Detect objects in images and publish the results to
    berrynet/engine/<service_name>/result.
    """

    def draw_result(self, bgr_array, result):
        return draw_bb(bgr_array,
                       result,
                       generate_class_color(class_num=self.engine.classes),
                       self.engine.labels)


def parse_engine_service_args(backend, services, labels_in_model=()):
    """Parse command line arguments of an engine service.

    Args:
        backend: Backend name, e.g. litert.
        services: Accepted service types, the first one is the default.
        labels_in_model: Service types whose models contain their labels,
            so --label is optional.

    Returns:
        Dict of arguments, with model and label resolved from the model
        package if one is given.
    """
    ap = argparse.ArgumentParser(
        description='{} engine service.'.format(backend))
    ap.add_argument(
        '-s', '--service',
        choices=services,
        default=services[0],
        help='Engine service type. ({} by default)'.format(services[0]))
    ap.add_argument(
        '--service_name',
        help=('Human-readable service name for service management. '
              'Results are published to berrynet/engine/<service_name>/result. '
              '(<backend><service> by default, e.g. {}detector)'.format(
                  backend)))
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
        '--num_threads',
        default=1,
        help="Number of threads for running inference.",
        type=int)
    ap.add_argument(
        '--draw',
        action='store_true',
        help='Draw bounding boxes or labels on image in result')
    ap.add_argument(
        '--debug',
        action='store_true',
        help='Debug mode toggle')
    args = vars(ap.parse_args())

    if args['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    if args['service_name'] is None:
        args['service_name'] = backend + args['service']
    if args['model_package'] != '':
        meta = DLModelManager().get_model_meta(args['model_package'])
        args['model'] = meta['model']
        args['label'] = meta['label']
    if args['service'] in labels_in_model:
        if not args['model']:
            ap.error('--model_package or --model is required')
    elif not (args['model'] and args['label']):
        ap.error('--model_package, or both --model and --label are required')
    logger.debug('model filepath: ' + args['model'])
    logger.debug('label filepath: {}'.format(args['label']))
    return args


def default_comm_config():
    return {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
