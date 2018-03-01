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

from berrynet import logger
from berrynet.comm import payload
from berrynet.dlmodelmgr import DLModelManager
from berrynet.engine.movidius_classification_engine import MovidiusEngine
from berrynet.service import EngineService


class MovidiusClassificationService(EngineService):
    def __init__(self, service_name, engine, comm_config):
        super(MovidiusClassificationService, self).__init__(service_name,
                                                            engine,
                                                            comm_config)

    def result_hook(self, generalized_result):
        logger.debug('result_hook, annotations: {}'.format(generalized_result['annotations']))
        self.comm.send('berrynet/engine/mvclassification/result',
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
                    help='Engine service name used as PID filename')
    ap.add_argument('--num_top_predictions', default=5,
                    help='Display this many predictions')
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

    mvng = MovidiusEngine(args['model'], args['label'])
    comm_config = {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
    engine_service = MovidiusClassificationService(args['service_name'],
                                                   mvng,
                                                   comm_config)
    engine_service.run(args)


if __name__ == '__main__':
    main()
