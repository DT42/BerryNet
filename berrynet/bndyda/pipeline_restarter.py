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

"""Pipeline service restarter.

Restart pipeline service after received config update notification.
"""

import argparse
import logging
import subprocess

from berrynet import logger
from berrynet.comm import Communicator


class PipelineRestarterService(object):
    def __init__(self, service_name, comm_config):
        self.service_name = service_name
        self.comm_config = comm_config
        self.comm_config['subscribe']['dlboxapi/config/update'] = \
            self.restart_pipeline
        self.comm = Communicator(self.comm_config, debug=True)

    def restart_pipeline(self, pl):
        logger.debug('Restart pipeline')
        subprocess.call('dlbox-manager restart dlbox-pipeline.service',
                        shell=True)

    def run(self, args):
        """Infinite loop serving pipeline restart requests"""
        self.comm.run()


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

    comm_config = {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
    engine_service = PipelineRestarterService(
        'pipeline service restarter',
        comm_config)
    engine_service.run(args)


if __name__ == '__main__':
    main()
