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

"""Engine service is a bridge between incoming data and inference engine.
"""

import argparse
import logging
import math

import cv2

from berrynet import logger
from berrynet.comm import payload
from berrynet.dlmodelmgr import DLModelManager
from berrynet.engine.darknet_engine import DarknetEngine
from berrynet.service import EngineService


def generate_class_color(class_num=20):
    """Generate a RGB color set based on given class number.

    Args:
        class_num: Default is VOC dataset class number.

    Returns:
        A tuple containing RGB colors.
    """
    colors = [(1, 0, 1), (0, 0, 1), (0, 1, 1),
              (0, 1, 0), (1, 1, 0), (1, 0, 0)]
    const = 1234567  # only for offset calculation

    colorset = []
    for cls_i in range(class_num):
        offset = cls_i * const % class_num

        ratio = (float(offset) / class_num) * (len(colors) - 1)
        i = math.floor(ratio)
        j = math.ceil(ratio)
        ratio -= i

        rgb = []
        for ch_i in range(3):
            r = (1 - ratio) * colors[i][ch_i] + ratio * colors[j][ch_i]
            rgb.append(math.ceil(r * 255))
        colorset.append(tuple(rgb[::-1]))
    return tuple(colorset)


def draw_bb(bgr_nparr, infres, class_colors, labels):
    """Draw bounding boxes on an image.

    Args:
        bgr_nparr: image data in numpy array format
        infres: Darkflow inference results
        class_colors: Bounding box color candidates, list of RGB tuples.

    Returens:
        Generalized result whose image data is drew w/ bounding boxes.
    """
    for res in infres['annotations']:
        left = int(res['left'])
        top = int(res['top'])
        right = int(res['right'])
        bottom = int(res['bottom'])
        label = res['label']
        color = class_colors[labels.index(label)]
        confidence = res['confidence']
        imgHeight, imgWidth, _ = bgr_nparr.shape
        thick = int((imgHeight + imgWidth) // 300)

        cv2.rectangle(bgr_nparr,(left, top), (right, bottom), color, thick)
        cv2.putText(bgr_nparr, label, (left, top - 12), 0, 1e-3 * imgHeight,
            color, thick//3)
    #cv2.imwrite('prediction.jpg', bgr_nparr)
    infres['bytes'] = payload.stringify_jpg(
                                    cv2.imencode('.jpg', bgr_nparr)[1])
    return infres


class DarknetService(EngineService):
    def __init__(self, service_name, engine, comm_config, draw=False):
        super(DarknetService, self).__init__(service_name,
                                                engine,
                                                comm_config)
        self.draw = draw

    def inference(self, pl):
        jpg_json = payload.deserialize_payload(pl.decode('utf-8'))
        jpg_bytes = payload.destringify_jpg(jpg_json['bytes'])

        bgr_array = payload.jpg2bgr(jpg_bytes)

        image_data = self.engine.process_input(bgr_array)
        output = self.engine.inference(image_data)
        model_outputs = self.engine.process_output(output)

        classes = self.engine.classes
        labels = self.engine.labels

        if self.draw is False:
            self.result_hook(self.generalize_result(jpg_json, model_outputs))
        else:
            self.result_hook(
                draw_bb(bgr_array,
                        self.generalize_result(jpg_json, model_outputs),
                        generate_class_color(class_num=classes),
                        labels))

    def result_hook(self, generalized_result):
        logger.debug('result_hook, annotations: {}'.format(generalized_result['annotations']))
        self.comm.send('berrynet/engine/darknet/result',
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
    ap.add_argument('--service_name',
                    default='darknet',
                    help='Engine service name used as PID filename')
    ap.add_argument('--num_top_predictions', default=5,
                    help='Display this many predictions')
    ap.add_argument('--draw',
                    action='store_true',
                    help='Draw bounding boxes on image in result')
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
    #logger.debug('model filepath: ' + args['model'])
    #logger.debug('label filepath: ' + args['label'])

    engine = DarknetEngine(
        config=b'/usr/share/dlmodels/tinyyolovoc-20170816/tiny-yolo-voc.cfg',
        model=b'/usr/share/dlmodels/tinyyolovoc-20170816/tiny-yolo-voc.weights',
        meta=b'/usr/share/dlmodels/tinyyolovoc-20170816/voc.data'
    )
    comm_config = {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
    engine_service = DarknetService(args['service_name'],
                                    engine,
                                    comm_config,
                                    args['draw'])
    engine_service.run(args)


if __name__ == '__main__':
    main()
