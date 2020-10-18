#!/usr/bin/env python3
#
# Copyright 2019 DT42
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

import argparse
import json
import io
import logging
import os
import tempfile
import tarfile
import time
import sys

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload


class DydaConfigUpdateClient(object):
    def __init__(self, comm_config, debug=False):
        self.comm_config = comm_config
        for topic, functor in self.comm_config['subscribe'].items():
            self.comm_config['subscribe'][topic] = self.handleResult
        self.comm = Communicator(self.comm_config, debug=True)

    def sendConfig(self, payloadID):
        self.comm.send(self.comm_config['publish'], payloadID)
        
    def handleResult(self, pl):
        try:
            payload_json = payload.deserialize_payload(pl.decode('utf-8'))
            print(payload_json)
            self.comm.stop_nb()
            sys.exit(0)
        except Exception as e:
            logger.info(e)

    def run(self, args):
        """Infinite loop serving inference requests"""
        self.comm.start_nb()
        self.sendConfig(args['payload'])
        time.sleep(1)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--broker-ip',
        default='localhost',
        help='MQTT broker IP.'
    )
    ap.add_argument(
        '--broker-port',
        default=1883,
        type=int,
        help='MQTT broker port.'
    )
    ap.add_argument('--debug',
        action='store_true',
        help='Debug mode toggle'
    )
    ap.add_argument(
        '--payload',
        required=True,
        help='payload ID'
    )
    ap.add_argument(
        '--topic',
        default='berrynet/manager/aikea/config',
        help='topic to listen for the result'
    )
    ap.add_argument(
        '--publish',
        default='berrynet/config/aikea/update',
        help='topic to publish'
    )
    return vars(ap.parse_args())


def main():
    args = parse_args()
    if args['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    comm_config = {
        'subscribe': {
            args['topic']: None
        },
        'publish': args['publish'],
        'broker': {
            'address': args['broker_ip'],
            'port': args['broker_port']
        }
    }
    config_client = DydaConfigUpdateClient(comm_config,
                                        args['debug'])
    config_client.run(args)


if __name__ == '__main__':
    main()
