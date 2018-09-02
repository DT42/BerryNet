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

"""Framebuffer dashboard.
"""

import argparse
import json
import os
import random
import sys
import time

from datetime import datetime
from os.path import join as pjoin

import cv2

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *


class FBDashboardService(object):
    def __init__(self, comm_config, data_dirpath):
        self.comm_config = comm_config
        for topic, functor in self.comm_config['subscribe'].items():
            self.comm_config['subscribe'][topic] = eval(functor)
        self.comm_config['subscribe']['berrynet/engine/tensorflow/result'] = self.update
        self.comm_config['subscribe']['berrynet/engine/pipeline/result'] = self.update
        #self.comm_config['subscribe']['berrynet/data/rgbimage'] = self.update
        self.comm = Communicator(self.comm_config, debug=True)
        self.data_dirpath = data_dirpath
        self.frame = None

    def update(self, pl):
        if not os.path.exists(self.data_dirpath):
            try:
                os.mkdir(self.data_dirpath)
            except Exception as e:
                logger.warn('Failed to create {}'.format(self.data_dirpath))
                raise(e)

        payload_json = payload.deserialize_payload(pl.decode('utf-8'))
        if 'bytes' in payload_json.keys():
            img_k = 'bytes'
        elif 'image_blob' in payload_json.keys():
            img_k = 'image_blob'
        else:
            raise Exception('No image data in MQTT payload')
        jpg_bytes = payload.destringify_jpg(payload_json[img_k])
        payload_json.pop(img_k)
        logger.debug('inference text result: {}'.format(payload_json))

        img = payload.jpg2rgb(jpg_bytes)
        try:
            res = payload_json['annotations']
        except KeyError:
            res = [
                {
                    'label': 'hello',
                    'confidence': 0.42,
                    'left': random.randint(50, 60),
                    'top': random.randint(50, 60),
                    'right': random.randint(300, 400),
                    'bottom': random.randint(300, 400)
                }
            ]
        self.frame = overlay_on_image(img, res)

        #timestamp = datetime.now().isoformat()
        #with open(pjoin(self.data_dirpath, timestamp + '.jpg'), 'wb') as f:
        #    f.write(jpg_bytes)
        #with open(pjoin(self.data_dirpath, timestamp + '.json'), 'w') as f:
        #    f.write(json.dumps(payload_json, indent=4))

    def update_fb(self):
        gl_draw_fbimage(self.frame)

    def run(self, args):
        """Infinite loop serving inference requests"""
        self.comm.start_nb()


def gl_draw_fbimage(rgbimg):
    h, w = rgbimg.shape[:2]

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, rgbimg)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glBegin(GL_QUADS)
    glTexCoord2d(0.0, 1.0)
    glVertex3d(-1.0, -1.0,  0.0)
    glTexCoord2d(1.0, 1.0)
    glVertex3d( 1.0, -1.0,  0.0)
    glTexCoord2d(1.0, 0.0)
    glVertex3d( 1.0,  1.0,  0.0)
    glTexCoord2d(0.0, 0.0)
    glVertex3d(-1.0,  1.0,  0.0)
    glEnd()
    glFlush()
    glutSwapBuffers()


def init():
    glClearColor(0.7, 0.7, 0.7, 0.7)


def idle():
    glutPostRedisplay()


def keyboard(key, x, y):
    key = key.decode('utf-8')
    if key == 'q':
        print("\n\nFinished\n\n")
        sys.exit()


def opencv_frame(src, w=None, h=None, fps=30):
    vidcap = cv2.VideoCapture(src)
    if not vidcap.isOpened():
        print('opened failed')
        sys.exit(errno.ENOENT)

    # set frame w/h if indicated
    if w and h:
        vidcap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        vidcap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

    # set FPS
    rate = int(vidcap.get(cv2.CAP_PROP_FPS))
    if rate > fps or rate < 1:
        print('Illegal data rate {} (1-30)'.format(rate))
        rate = fps
    print('fps: {}'.format(rate))

    # frame generator
    while True:
        success, image = vidcap.read()
        if not success:
            print('Failed to read frame')
            break
        yield image


#Vcap = opencv_frame(0, w=320, h=240)
Vcap = opencv_frame(0)


def draw_box(image, annotations):
    """Draw information of annotations onto image.

    Args:
        image: Image nparray.
        annotations: List of detected object information.

    Returns: Image nparray containing object information on it.
    """
    print('draw_box, annotations: {}'.format(annotations))
    img = image.copy()

    for anno in annotations:
        # draw bounding box
        box_color = (0, 0, 255)
        box_thickness = 1
        cv2.rectangle(img,
                      (anno['left'], anno['top']),
                      (anno['right'], anno['bottom']),
                      box_color,
                      box_thickness)

        # draw label
        label_background_color = box_color
        label_text_color = (255, 255, 255)
        if 'track_id' in anno.keys():
            label = 'ID:{} {}'.format(anno['track_id'], anno['label'])
        else:
            label = anno['label']
        label_text = '{} ({} %)'.format(label,
                                        int(anno['confidence'] * 100))
        label_size = cv2.getTextSize(label_text,
                                     cv2.FONT_HERSHEY_SIMPLEX,
                                     0.5,
                                     1)[0]
        label_left = anno['left']
        label_top = anno['top'] - label_size[1]
        if (label_top < 1):
            label_top = 1
        label_right = label_left + label_size[0]
        label_bottom = label_top + label_size[1]
        cv2.rectangle(img,
                      (label_left - 1, label_top - 1),
                      (label_right + 1, label_bottom + 1),
                      label_background_color,
                      -1)
        cv2.putText(img,
                    label_text,
                    (label_left, label_bottom),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    label_text_color,
                    1)
    return img


def overlay_on_image(display_image, object_info):
    """Modulized version of overlay_on_image function
    """
    if isinstance(object_info, type(None)):
        print('WARNING: object info is None')
        return display_image

    return draw_box(display_image, object_info)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--data-dirpath',
        default='/tmp/berrynet-data',
        help='Dirpath where to store collected data.'
    )
    ap.add_argument(
        '--broker-ip',
        default='localhost',
        help='MQTT broker IP.'
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
            'port': 1883
        }
    }
    fbd_service = FBDashboardService(comm_config,
                                      args['data_dirpath'])
    fbd_service.run(args)

    glutInitWindowPosition(0, 0)
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE)
    glutCreateWindow("BerryNet Result Dashboard, q to quit")
    glutDisplayFunc(fbd_service.update_fb)
    glutKeyboardFunc(keyboard)
    init()
    glutIdleFunc(idle)
    glutMainLoop()


if __name__ == '__main__':
    main()
