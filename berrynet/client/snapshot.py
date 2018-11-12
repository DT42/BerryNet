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

"""
Snapshot service will listen to a trigger event (MQTT topic),
and send a snapshot retrieved from camera.
"""

import argparse
import json

from datetime import datetime

import cv2

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload


class SnapshotService(object):
    def __init__(self, comm_config):
        self.comm_config = comm_config
        for topic, functor in self.comm_config['subscribe'].items():
            self.comm_config['subscribe'][topic] = eval(functor)
        self.comm_config['subscribe']['berrynet/trigger/controller/snapshot'] = self.snapshot
        self.comm = Communicator(self.comm_config, debug=True)

    def snapshot(self, pl):
        '''Send camera snapshot.

        The functionality is the same as using camera client in file mode.

        The difference is that snapshot client retrieves image from camera
        instead of given filepath.
        '''
        duration = lambda t: (datetime.now() - t).microseconds / 1000

        # WORKAROUND: Prevent VideoCapture from buffering frames.
        #     VideoCapture will buffer frames automatically, and we need
        #     to find a way to disable it.
        self.capture = cv2.VideoCapture(0)
        status, im = self.capture.read()
        if (status is False):
            logger.warn('ERROR: Failure happened when reading frame')

        t = datetime.now()
        retval, jpg_bytes = cv2.imencode('.jpg', im)
        mqtt_payload = payload.serialize_jpg(jpg_bytes)
        self.comm.send('berrynet/data/rgbimage', mqtt_payload)
        logger.debug('send: {} ms'.format(duration(t)))
        self.capture.release()

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
    ap.add_argument(
        '--topic-config',
        default=None,
        help='Path of the MQTT topic subscription JSON.'
    )
    return vars(ap.parse_args())


def main():
    args = parse_args()

    if args['topic_config']:
        with open(args['topic_config']) as f:
            topic_config = json.load(f)
    else:
        topic_config = {}
    comm_config = {
        'subscribe': topic_config,
        'broker': {
            'address': args['broker_ip'],
            'port': args['broker_port']
        }
    }
    dc_service = SnapshotService(comm_config)
    dc_service.run(args)


if __name__ == '__main__':
    main()
