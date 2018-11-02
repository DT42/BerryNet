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

"""Dashboard agent service.
"""

import argparse
import json

from os.path import join as pjoin

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload


class DashboardService(object):
    def __init__(self, service_name, comm_config):
        self.service_name = service_name
        self.comm_config = comm_config
        self.comm_config['subscribe']['berrynet/engine/tensorflow/result'] = self.update
        self.comm_config['subscribe']['berrynet/engine/mvclassification/result'] = self.update
        self.comm = Communicator(self.comm_config, debug=True)
        self.basedir = '/usr/local/berrynet/dashboard/www/freeboard'

    def update(self, pl):
        payload_json = payload.deserialize_payload(pl.decode('utf-8'))
        jpg_bytes = payload.destringify_jpg(payload_json['bytes'])
        inference_result = [
            '{0}: {1}<br>'.format(anno['label'], anno['confidence'])
            for anno in payload_json['annotations']
        ]
        logger.debug('inference results: {}'.format(inference_result))

        with open(pjoin(self.basedir, 'snapshot.jpg'), 'wb') as f:
            f.write(jpg_bytes)
        self.comm.send('berrynet/dashboard/snapshot', 'snapshot.jpg')
        self.comm.send('berrynet/dashboard/inferenceResult',
                       json.dumps(inference_result))

    def run(self, args):
        """Infinite loop serving inference requests"""
        self.comm.run()


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--service_name', required=True,
                    help='Engine service name used as PID filename')
    return vars(ap.parse_args())


def main():
    args = parse_args()

    comm_config = {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
    dashboard_service = DashboardService(args['service_name'],
                                         comm_config)
    dashboard_service.run(args)


if __name__ == '__main__':
    main()
