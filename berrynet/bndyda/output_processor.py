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

"""Data collector service.
"""

import argparse
import json
import os

from datetime import datetime
from os.path import join as pjoin

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload


class DataCollectorService(object):
    def __init__(self, comm_config, data_dirpath):
        self.comm_config = comm_config
        self.comm_config['subscribe']['berrynet/engine/mockup/result'] = \
            self.update
        self.comm = Communicator(self.comm_config, debug=True)
        self.data_dirpath = data_dirpath

    def update(self, pl):
        if not os.path.exists(self.data_dirpath):
            try:
                os.mkdir(self.data_dirpath)
            except Exception as e:
                logger.warn('Failed to create {}'.format(self.data_dirpath))
                raise(e)

        payload_json = payload.deserialize_payload(pl.decode('utf-8'))
        jpg_bytes = payload.destringify_jpg(payload_json['bytes'])
        payload_json.pop('bytes')
        logger.debug('inference text result: {}'.format(payload_json))

        timestamp = datetime.now().isoformat()
        with open(pjoin(self.data_dirpath, timestamp + '.jpg'), 'wb') as f:
            f.write(jpg_bytes)
        with open(pjoin(self.data_dirpath, timestamp + '.json'), 'w') as f:
            f.write(json.dumps(payload_json, indent=4))

    def run(self, args):
        """Infinite loop serving inference requests"""
        self.comm.run()


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--data_dirpath',
        default='/tmp/berrynet-data',
        help='Dirpath where to store collected data.'
    )
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
    dc_service = DataCollectorService(comm_config,
                                      args['data_dirpath'])
    dc_service.run(args)


if __name__ == '__main__':
    main()
