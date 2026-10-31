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

"""LiteRT engine service.
"""

from berrynet.engine.litert_engine import LiteRTClassifierEngine
from berrynet.engine.litert_engine import LiteRTDetectorEngine
from berrynet.engine.litert_engine import LiteRTYoloDetectorEngine
from berrynet.engine.litert_engine import LiteRTYoloV4DetectorEngine
from berrynet.service import ClassifierService
from berrynet.service import DetectorService
from berrynet.service import default_comm_config
from berrynet.service import parse_engine_service_args


def main():
    args = parse_engine_service_args(
        'litert', ['classifier', 'detector', 'yolo', 'yolov4'],
        labels_in_model=['yolo'])

    if args['service'] == 'classifier':
        engine = LiteRTClassifierEngine(
                     model = args['model'],
                     labels = args['label'],
                     top_k = args['top_k'],
                     num_threads = args['num_threads'])
        service_functor = ClassifierService
    elif args['service'] == 'detector':
        engine = LiteRTDetectorEngine(
                     model = args['model'],
                     labels = args['label'],
                     num_threads = args['num_threads'])
        service_functor = DetectorService
    elif args['service'] == 'yolo':
        engine = LiteRTYoloDetectorEngine(
                     model = args['model'],
                     labels = args['label'],
                     num_threads = args['num_threads'])
        service_functor = DetectorService
    else:
        engine = LiteRTYoloV4DetectorEngine(
                     model = args['model'],
                     labels = args['label'],
                     num_threads = args['num_threads'])
        service_functor = DetectorService

    engine_service = service_functor(args['service_name'],
                                     engine,
                                     default_comm_config(),
                                     draw=args['draw'])
    engine_service.run(args)


if __name__ == '__main__':
    main()
