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

"""Pipeline service with relay engine (default engine).
"""

import cv2
import argparse
import json
import logging
import os
import sys
import time

from datetime import datetime

import numpy as np

from berrynet import logger
from berrynet.bndyda.launcher_berrynet import BerryNetPipelineLauncher
from berrynet.comm import payload
from berrynet.engine import DLEngine
from berrynet.service import EngineService
from dyda_utils import tools


class PipelineEngine(DLEngine):
    def __init__(self, config,
                 dyda_config_path='',
                 warmup_size=(480, 640, 3),
                 disable_warmup=False,
                 benchmark=False,
                 verbosity=0):
        self.launcher = BerryNetPipelineLauncher(
            config,
            dyda_config_path=dyda_config_path,
            verbosity=verbosity, benchmark=benchmark)
        self.pipeline_config = tools.parse_json(config)
        if not disable_warmup:
            self.warmup(shape=warmup_size)

    # def process_input(self, tensor):
    #     return tensor

    def inference(self, tensor, meta={}, base_name=None):
        """
        Args:
            tensor: Image data in BGR format (numpy array)

        Returns:
            Dictionary following generic inference spec and
            pipeline spec (by project).
        """
        return self.launcher.run(tensor, meta=meta, base_name=base_name)
        # return {
        #     'annotations': {
        #         'label': 'dt42',
        #         'confidence': 0.99
        #     }
        # }

    def process_output(self, output):
        return output

    def get_dl_component_config(self, pipeline_config):
        """Get pipeline def list containing only DL components

        Args:
            pipeline_config: pipeline config JSON object

        Returns:
            List of DL components definitions
        """
        dl_comp_config = []
        try:
            pipeline_def = pipeline_config['pipeline_def']
        except KeyError:
            logger.warning('Invalid pipeline config')
            pipeline_def = []
        for comp_config in pipeline_def:
            if ('classifier' in comp_config['name'] or
                    'detector' in comp_config['name']):
                dl_comp_config.append(comp_config)
        return dl_comp_config

    def warmup(self, shape=(480, 640, 3), iteration=5):
        """Warmup pipeline engine

        Use all-zero numpy array as input to warmup pipeline engine.

        Args:
            meta: Metadata of image data
            shape: Warmup image shape in (w, h, c) format
            iteration: How many times to feed in warmup image

        Returns:
            N/A
        """
        logger.debug('Warmup shape: {}'.format(shape))
        input_data = [np.zeros(shape=shape, dtype=np.uint8)] * iteration

        # FIXME: get engines programatically
        dl_comp_config = self.get_dl_component_config(self.pipeline_config)
        for comp_config in dl_comp_config:
            t_start = time.time()

            comp_name = comp_config['name']
            inst = self.launcher.pipeline.pipeline[comp_name]['instance']
            inst.input_data = input_data
            inst.main_process()

            t_duration = time.time() - t_start
            logger.debug('Warmup {0} costs {1} sec'.format(comp_name,
                                                           t_duration))


def duration(t):
    return (datetime.now() - t).microseconds / 1000


class PipelineDummyEngine(DLEngine):
    def inference(self, tensor, meta={}):
        output = None
        return output


class PipelineService(EngineService):
    def __init__(self, service_name, engine, comm_config,
                 pid=None,
                 pipeline_config_path=None,
                 disable_engine=False,
                 disable_warmup=False,
                 warmup_size=(480, 640, 3)):
        super().__init__(service_name,
                         engine,
                         comm_config)

        self.pipeline_config_path = pipeline_config_path
        self.dyda_config_path = ''
        self.warmup_size = warmup_size

        self.disable_engine = disable_engine

        if not os.path.exists('/tmp/dlbox-pipeline'):
            os.mkdir('/tmp/dlbox-pipeline')
        self.counter = 0
        self.pid = pid

        logger.debug('Pipeline result topic: berrynet/engine/pipeline/result')

    def inference(self, pl):
        logger.debug('Disable engine: {}'.format(self.disable_engine))
        if self.disable_engine:
            self.dummy_inference(pl)
        else:
            self.dl_inference(pl)

    def dl_inference(self, pl):
        def empty_inference_result(count):
            return [
                {
                    'channel': i,
                    'annotations': []
                }
                for i in range(count)]

        t = datetime.now()
        base_name = None
        logger.debug('counter #{}'.format(self.counter))
        logger.debug('payload size: {}'.format(len(pl)))
        logger.debug('payload type: {}'.format(type(pl)))
        # Unify the type of input payload to a list, so that
        # bnpipeline can process the input in the same way.
        #
        # If the payload is
        #     - a list of items: keep the list
        #     - a single item: convert to a list with an item
        mqtt_payload = payload.deserialize_payload(pl.decode('utf-8'))
        if isinstance(mqtt_payload, list):
            jpg_json = mqtt_payload
        else:
            jpg_json = [mqtt_payload]
            logger.info('Convert input type from {0} to {1}'.format(
                type(mqtt_payload),
                type(jpg_json)))

        jpg_bytes_list = [
            payload.destringify_jpg(img['bytes']) for img in jpg_json]
        metas = [img.get('meta', {}) for img in jpg_json]
        logger.debug('destringify_jpg: {} ms'.format(duration(t)))

        t = datetime.now()
        bgr_arrays = [
            payload.jpg2bgr(jpg_bytes) for jpg_bytes in jpg_bytes_list]
        logger.debug('jpg2bgr: {} ms'.format(duration(t)))

        t = datetime.now()
        # FIXME: Galaxy pipeline may or may not use a list as input, so we
        # check the length here and then choose whether to send a list or not.
        # We may drop it when Galaxy Pipline unite their input.
        if len(bgr_arrays) > 1:
            image_data = self.engine.process_input(bgr_arrays)
        else:
            image_data = self.engine.process_input(bgr_arrays[0])
        # FIXME: Galaxy pipeline doesn't support multiple metadata for multiple
        # images at the moment (which will be needed), so we provide the first
        # metadata here. This commit should be revert when Galaxy pipeline
        # support it: https://gitlab.com/DT42/galaxy42/dt42-trainer/issues/120
        meta_data = metas[0]

        try:
            logger.debug(meta_data)
            output = self.engine.inference(image_data,
                                           meta=meta_data,
                                           base_name=base_name)
            model_outputs = self.engine.process_output(output)
        except IndexError as e:
            # FIXME: workaround for pipeline
            # Pipeline throw IndexError when there's no results, see:
            # https://gitlab.com/DT42/galaxy42/dt42-trainer/issues/86
            # So we catch the exeception, and produce a dummy result
            # to hook. This workaround should be removed after the issue
            # has been fixed.
            model_outputs = empty_inference_result(len(jpg_json))
            logger.warning(('inference results are empty because '
                            'pipeline raised IndexError'))

        if model_outputs is None:
            model_outputs = empty_inference_result(len(jpg_json))
            logger.warning(('inference results are empty because '
                            'severe error happened in pipeline'))

        logger.debug('Result: {}'.format(model_outputs))
        logger.debug('Classification takes {} ms'.format(duration(t)))

        # self.engine.cache_data('model_output', model_outputs)
        # self.engine.cache_data('model_output_filepath', output_name)
        # self.engine.save_cache()

        self.send_result(self.generalize_result(jpg_json, model_outputs))

        self.counter += 1

    def dummy_inference(self, pl):
        logger.debug('dummy_inference is called')

    def switch_mode(self, pl):
        """Switch pipeline service between inference and non-inference modes

        If Pipeline service receives berrynet/data/mode topic with
        "inference" in payload, service will switch to inference mode;

        If "idle" or "learning" in payload, service will switch to
        non-inference mode.

        Pipeline service will create pipeline engine and
        listen to specified topics only in inference mode.

        Args:
            pl: MQTT message payload
                valid value: {'inference', 'idle', 'learning'}

        Returns:
            N/A
        """
        mode = pl.decode('utf-8')
        if mode == 'inference':
            self.disable_engine = False
            self.engine = PipelineEngine(
                              self.pipeline_config_path,
                              dyda_config_path=self.dyda_config_path,
                              disable_warmup=self.disable_warmup,
                              warmup_size=self.warmup_size)
        else:
            self.disable_engine = True
            self.engine = PipelineDummyEngine()

    def deploy(self, pl):
        """Deploy newly retrained model for pipeline engine

        New dyda config filepath is in the payload.

        Args:
            pl: MQTT message payload w/ new dyda config filepath.

        Returns:
            N/A
        """
        dyda_config_path = pl.decode('utf-8')
        self.dyda_config_path = dyda_config_path
        self.comm.send('berrynet/data/deployed', '')
        logger.info(('New model has been deployed, '
                     'dyda config: {}'.format(self.dyda_config_path)))

    def generalize_result(self, eng_input, eng_output):
        # Pipeline returns None if any error happened
        if eng_output is None:
            eng_output = {}

        # If pipeline generate multiple outputs simultaneously
        #
        # In this case, the format of engine output is
        #
        #     {
        #         'annotations': {...},
        #         'bytes': '...'
        #     }
        if all(key in eng_output.keys() for key in ['annotations', 'bytes']):
            logger.debug('Pipeline output type: multiple')
            logger.debug('eng_input type = {0}, len = {1}'.format(type(eng_input), len(eng_input)))

            # FIXME: Re-cap why eng_input is a list and only contains 1 item.
            eng_input = eng_input[0]

            try:
                eng_input['annotations'] = eng_output['annotations']
                logger.debug('output image type: {0}, len: {1}'.format(type(eng_output['bytes']),
                                                                       len(eng_output['bytes'])))
                pipeline_img = eng_output['bytes'][0]
                retval, jpg_bytes = cv2.imencode('.jpg', pipeline_img)
                eng_input['bytes'] = payload.stringify_jpg(jpg_bytes)
            except Exception as e:
                logger.critical(e)
        else:
            logger.debug('Pipeline output type: simple')

            # FIXME: Workaround for spec incompatibility
            # DLBox spec use 'image_blob', but BerryNet use 'bytes', so we have to
            # do a convert here
            if isinstance(eng_output, list):
                inf_output = eng_output[0]
            else:
                inf_output = eng_output
            if len(eng_input) > 1:
                for i in range(len(eng_input)):
                    try:
                        retval, jpg_bytes = cv2.imencode('.jpg', inf_output)
                        eng_input[i]['bytes'] = payload.stringify_jpg(jpg_bytes)
                        #eng_input[i].pop('bytes')
                    except Exception as e:
                        print(e)

            else:
                try:
                    eng_input, = eng_input
                    retval, jpg_bytes = cv2.imencode('.jpg', inf_output)
                    eng_input['bytes'] = payload.stringify_jpg(jpg_bytes)
                    #eng_input.pop('bytes')
                except Exception as e:
                    print(e)

        return eng_input

    def send_result(self, generalized_result):
        # NOTE: There are numpy float in pipeline output, so we use
        # tools.dump_json instead of payload.serialize_payload
        if self.pid is None:
            self.comm.send(
                'berrynet/engine/pipeline/result',
                tools.dump_json(generalized_result))
        else:
            self.comm.send(
                'berrynet/engine/pipeline/result/{}'.format(self.pid),
                tools.dump_json(generalized_result))


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pipeline-id',
                    help=('Indicate pipeline ID which will be attached '
                          'to result topic (optional)'))
    ap.add_argument('--pipeline-config',
                    help='File contains the definition '
                         'of pipeline application')
    ap.add_argument('--debug',
                    action='store_true',
                    help='Debug mode toggle')
    ap.add_argument('--benchmark',
                    action='store_true',
                    help='Benchmark mode toggle')
    ap.add_argument('--broker-ip',
                    default='localhost',
                    help='MQTT broker IP')
    ap.add_argument('--topic-config',
                    default=None,
                    help='Path of the MQTT topic subscription JSON.')
    ap.add_argument('--topic',
                    nargs=2,
                    action='append',
                    default=None,
                    help=('Two params in "<topic> <handler>" format. '
                          'It can be declared multiple times.'))
    ap.add_argument('--disable-engine',
                    action='store_true',
                    help='Service disable engine initially')
    ap.add_argument('--disable-warmup',
                    action='store_true',
                    help='Skip warming up pipeline by black image')
    ap.add_argument('-v', '--verbosity',
                    action='count', default=0,
                    help='Output verbosity')
    ap.add_argument('-w', '--warmup-size',
                    nargs=2,
                    type=int,
                    default=(640, 480),
                    help='Warmup image\'s size, in format "w h", '
                         'e.g., "640 480"')
    return vars(ap.parse_args())


def main():
    # Process CLI arguments
    args = parse_args()
    if args['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args['topic_config']:
        with open(args['topic_config']) as f:
            topic_config = json.load(f)
    else:
        topic_config = {}
    topic_config['berrynet/data/mode'] = 'self.switch_mode'
    topic_config['berrynet/data/deploy'] = 'self.deploy'

    if args['topic'] is not None:
        for t, h in args['topic']:
            topic_config[t] = h

    w, h = args['warmup_size']
    # Setup pipeline service
    if args['disable_engine']:
        eng = PipelineDummyEngine()
    else:
        eng = PipelineEngine(args['pipeline_config'],
                             disable_warmup=args['disable_warmup'],
                             verbosity=args['verbosity'],
                             benchmark=args['benchmark'],
                             warmup_size=(h, w, 3))
    comm_config = {
        'subscribe': topic_config,
        'broker': {
            'address': args['broker_ip'],
            'port': 1883
        }
    }
    engine_service = PipelineService(
        'pipeline service',
        eng,
        comm_config,
        pid=args['pipeline_id'],
        pipeline_config_path=args['pipeline_config'],
        disable_engine=args['disable_engine'],
        disable_warmup=args['disable_warmup'],
        warmup_size=(h, w, 3))

    engine_service.run(args)


if __name__ == '__main__':
    main()
