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
import subprocess
import tempfile
import tarfile
import time
import sys
import configparser

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload

class DydaConfigUpdateService(object):
    def __init__(self, comm_config, debug=False):
        self.comm_config = comm_config
        for topic, functor in self.comm_config['subscribe'].items():
            self.comm_config['subscribe'][topic] = self.handleConfig
        self.comm = Communicator(self.comm_config, debug=True)
        idlistConfig = configparser.ConfigParser()
        idlistConfig.read(self.comm_config['idlist'])
        self.idlist = idlistConfig["ID"]

    def sendConfig(self, jsonPayload):
        self.comm.send(self.comm_config['publish'], jsonPayload)
        
    def handleConfig(self, pl):
        payload_json = ""
        try:
            id=pl.decode('utf-8')
            if (id in self.idlist):
                configFilename = self.idlist[id]
                f = open(configFilename)
                payload_json = payload.deserialize_payload(f.read())
                self.sendConfig(payload.serialize_payload(payload_json))
            else:
                logger.warning("ID %s is not in idlist"%(id))
                return
        except Exception as e:
            logger.info(e)

        # output config file
        with open(self.comm_config['configfile'], 'w') as configfile:
            configfile.write(payload.serialize_payload(payload_json))
            configfile.close()

        # restart service
        subprocess.run(["supervisorctl", "restart", "bnpipeline-bndyda"])
            
    def run(self, args):
        """Infinite loop serving inference requests"""
        self.comm.run()

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
        '--topic',
        default='berrynet/config/aikea/update',
        help='topic to listen for the result'
    )
    ap.add_argument(
        '--publish',
        default='berrynet/manager/aikea/config',
        help='topic to publish'
    )
    ap.add_argument(
        '--configfile',
        default='/var/lib/berrynet/dyda.config',
        help='config file path for dyda'
    )
    ap.add_argument(
        '--idlist',
        required=True,
        help='list of id and config file'
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
        },
        'configfile': args['configfile'],
        'idlist': args['idlist']
    }
    config_service = DydaConfigUpdateService(comm_config,
                                        args['debug'])
    config_service.run(args)


if __name__ == '__main__':
    main()
