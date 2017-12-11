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

"""Movidius inference engine.
"""

import argparse

import movidius as mv
from engineservice import EngineService


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True,
                    help='Model file path')
    ap.add_argument('--label', required=True,
                    help='Label file path')
    ap.add_argument('--image_dir', required=True,
                    help='Path to image file')
    ap.add_argument('--service_name', required=True,
                    help='Engine service name used as PID filename')
    ap.add_argument('--num_top_predictions', default=5,
                    help='Display this many predictions')
    return vars(ap.parse_args())


if __name__ == '__main__':
    args = parse_args()
    mvng = mv.MovidiusNeuralGraph(args['model'], args['label'])
    engine_service = EngineService(args['service_name'], mvng)
    engine_service.run(args)
