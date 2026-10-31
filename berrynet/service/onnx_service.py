# Copyright 2026 DT42
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

"""ONNX Runtime engine service.
"""

from berrynet.engine.onnx_engine import ONNXClassifierEngine
from berrynet.engine.onnx_engine import ONNXDetectorEngine
from berrynet.engine.onnx_engine import ONNXYoloDetectorEngine
from berrynet.service import ClassifierService
from berrynet.service import DetectorService
from berrynet.service import default_comm_config
from berrynet.service import parse_engine_service_args


def main():
    args = parse_engine_service_args('onnx', ['classifier', 'detector', 'yolo'],
                                     labels_in_model=['yolo'])

    if args['service'] == 'classifier':
        engine = ONNXClassifierEngine(
                     model = args['model'],
                     labels = args['label'],
                     top_k = args['top_k'],
                     num_threads = args['num_threads'])
        service_functor = ClassifierService
    elif args['service'] == 'detector':
        engine = ONNXDetectorEngine(
                     model = args['model'],
                     labels = args['label'],
                     num_threads = args['num_threads'])
        service_functor = DetectorService
    else:
        engine = ONNXYoloDetectorEngine(
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
