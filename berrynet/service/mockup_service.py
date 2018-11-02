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

"""Mockup service with relay engine (default engine).
"""

import argparse
import json
import logging
import os

from berrynet import logger
from berrynet.comm import payload
from berrynet.engine import DLEngine
from berrynet.service import EngineService


class MockupEngine(DLEngine):
    def inference(self, tensor):
        return {
            'annotations': {
                'label': 'dt42',
                'confidence': 0.99
            }
        }


class MockupService(EngineService):
    def __init__(self, service_name, engine, comm_config):
        super().__init__(service_name,
                         engine,
                         comm_config)
        if not os.path.exists('/tmp/mockup'):
            os.mkdir('/tmp/mockup')

    #def generalize_result(self, eng_input, eng_output):
    #    logger.debug()
    #    eng_input.update(eng_output)
    #    return eng_input

    def result_hook(self, generalized_result):
        gr = generalized_result
        jpg_bytes = payload.destringify_jpg(gr.pop('bytes'))
        logger.debug('generalized result (readable only): {}'.format(gr))
        with open('/tmp/mockup/{}.jpg'.format(gr['timestamp']), 'wb') as f:
            f.write(jpg_bytes)
        with open('/tmp/mockup/{}.json'.format(gr['timestamp']), 'w') as f:
            f.write(json.dumps(gr, indent=4))


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--debug',
                    action='store_true',
                    help='Debug mode toggle')
    return vars(ap.parse_args())


def main():
    args = parse_args()
    if args['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    eng = MockupEngine()
    comm_config = {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
    engine_service = MockupService('mockup service', eng, comm_config)
    engine_service.run(args)


if __name__ == '__main__':
    main()
