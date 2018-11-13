#!/usr/bin/env python

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

"""Data collector with UI showing inference result for human
"""

import argparse
import json
import os
import sys
import threading
import tkinter as tk

from datetime import datetime
from os.path import join as pjoin

import cv2
import numpy as np

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload
from PIL import Image
from PIL import ImageTk


class DataCollectorService(object):
    def __init__(self, comm_config, data_dirpath):
        self.comm_config = comm_config
        for topic, functor in self.comm_config['subscribe'].items():
            self.comm_config['subscribe'][topic] = eval(functor)
        #self.comm_config['subscribe']['berrynet/data/rgbimage'] = self.update
        self.comm_config['subscribe']['berrynet/engine/pipeline/result'] = self.save_pipeline_result
        self.comm = Communicator(self.comm_config, debug=True)
        self.data_dirpath = data_dirpath

    def update(self, pl):
        payload_json = payload.deserialize_payload(pl.decode('utf-8'))

        # update UI with the latest inference result
        self.ui.update(payload_json, 'bytes')

        if self.data_dirpath:
            if not os.path.exists(self.data_dirpath):
                try:
                    os.mkdir(self.data_dirpath)
                except Exception as e:
                    logger.warn('Failed to create {}'.format(self.data_dirpath))
                    raise(e)

            jpg_bytes = payload.destringify_jpg(payload_json['bytes'])
            payload_json.pop('bytes')
            logger.debug('inference text result: {}'.format(payload_json))

            timestamp = datetime.now().isoformat()
            with open(pjoin(self.data_dirpath, timestamp + '.jpg'), 'wb') as f:
                f.write(jpg_bytes)
            with open(pjoin(self.data_dirpath, timestamp + '.json'), 'w') as f:
                f.write(json.dumps(payload_json, indent=4))

    def save_pipeline_result(self, pl):
        payload_json = payload.deserialize_payload(pl.decode('utf-8'))

        # update UI with the latest inference result
        self.ui.update(payload_json, 'image_blob')

        if self.data_dirpath:
            if not os.path.exists(self.data_dirpath):
                try:
                    os.mkdir(self.data_dirpath)
                except Exception as e:
                    logger.warn('Failed to create {}'.format(self.data_dirpath))
                    raise(e)

            jpg_bytes = payload.destringify_jpg(payload_json['image_blob'])
            payload_json.pop('image_blob')
            logger.debug('inference text result: {}'.format(payload_json))

            timestamp = datetime.now().isoformat()
            with open(pjoin(self.data_dirpath, timestamp + '.jpg'), 'wb') as f:
                f.write(jpg_bytes)
            with open(pjoin(self.data_dirpath, timestamp + '.json'), 'w') as f:
                f.write(json.dumps(payload_json, indent=4))

    def send_snapshot_trigger(self):
        payload = {}
        payload['timestamp'] = datetime.now().isoformat()
        mqtt_payload = json.dumps(payload)
        self.comm.send('berrynet/trigger/controller/snapshot', mqtt_payload)

    def run(self, args):
        """Infinite loop serving inference requests"""
        self.comm.run()


class UI(object):
    def __init__(self, dc_service, dc_kwargs):
        # Create data collector attributes
        self.dc_service = dc_service
        self.dc_kwargs = dc_kwargs
        self.dc_service.ui = self

        # Create UI attributes
        self.window = tk.Tk()
        self.window.title('BerryNet Inference Dashboard')
        self.window.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.canvas_w = dc_kwargs['image_width']
        self.canvas_h = dc_kwargs['image_height']
        self.crowd_factor = 3

        # Add label: inference result text
        self.result = tk.Label(self.window,
                               text='TBD',
                               font=('Courier New', 10),
                               justify=tk.LEFT)
        #self.result.pack(expand=True, side=tk.LEFT)
        self.result.grid(row=0, column=0, padx=10)
        #self.result.columnconfigure(1, weight=2)

        # Add canvas: inference result image
        #self.canvas = tk.Canvas(self.window, width=1920, height=1080)
        self.canvas = tk.Canvas(self.window)
        self.photo = ImageTk.PhotoImage(
                         image=Image.fromarray(
                             np.zeros((self.canvas_h, self.canvas_w, 3), dtype=np.uint8)))
        self.image_id = self.canvas.create_image(
                            0, 0, image=self.photo, anchor=tk.NW)
        #self.canvas.pack(side=tk.LEFT)
        self.canvas.grid(row=0, column=1, rowspan=2, columnspan=4, sticky='nesw')

        # Add button: snapshot trigger
        self.snapshot_button = tk.Button(self.window,
                                         text='Query',
                                         command=self.snapshot)
        #self.snapshot_button.pack(expand=True)
        self.snapshot_button.grid(row=1, column=0)

        # Add button and label: threshold controller
        self.threshold = tk.Label(self.window,
                               text=self.crowd_factor,
                               font=('Courier New', 10),
                               justify=tk.LEFT)
        self.threshold.grid(row=1, column=1)

        self.snapshot_button = tk.Button(self.window,
                                         text='+',
                                         command=self.increase_threshold)
        self.snapshot_button.grid(row=1, column=2)

        self.snapshot_button = tk.Button(self.window,
                                         text='-',
                                         command=self.decrease_threshold)
        self.snapshot_button.grid(row=1, column=3)

        # Create data collector thread
        t = threading.Thread(name='Data Collector',
                             target=self.dc_service.run,
                             args=(self.dc_kwargs,))
        t.start()

        # Start the main UI program
        self.window.mainloop()

    def update(self, data, imgkey='bytes'):
        '''
        Args:
            data: Inference result loaded from JSON object
        '''
        # Retrieve result image
        jpg_bytes = payload.destringify_jpg(data[imgkey])
        img = payload.jpg2rgb(jpg_bytes)

        # Retrieve result text, and update text area
        data.pop(imgkey)
        result_text = self.process_output(data)
        if 'safely' in result_text:
            text_color = 'blue'
        else:
            text_color = 'red'
        self.result.config(text=result_text, fg=text_color)

        # update image area
        resized_img = Image.fromarray(img).resize((self.canvas_h, self.canvas_w))
        self.photo = ImageTk.PhotoImage(image=resized_img)
        win_w = self.photo.width() + self.result.winfo_width()
        win_h = self.photo.height() + self.snapshot_button.winfo_height()
        self.window.geometry('{}x{}'.format(win_w, win_h))
        self.canvas.itemconfig(self.image_id, image=self.photo)

    def snapshot(self):
        self.dc_service.send_snapshot_trigger()

    def increase_threshold(self):
        self.crowd_factor += 1
        self.threshold.config(text=self.crowd_factor)

    def decrease_threshold(self):
        self.crowd_factor -= 1
        self.threshold.config(text=self.crowd_factor)

    def process_output(self, output):
        '''
        Args:
            output: Inference result, JSON object

        Returns:
            Stringified JSON data.
        '''
        if 'annotations' in output.keys():
            count = 0
            for obj in output['annotations']:
                if obj['label'] == 'person':
                    count += 1
                #logger.info('label = {}'.format(k))
            msg = '{} persons at the corner\n\n'.format(count)
            if count > self.crowd_factor:
                msg += 'Too crowded,\nsuggest to go straight'
            else:
                msg += 'You can turn right safely'
            return msg
        else:
            return json.dumps(output, indent=4)

    def on_closing(self):
        self.dc_service.comm.disconnect()
        self.window.destroy()


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--data-dirpath',
        default=None,
        help='Dirpath where to store collected data.'
    )
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
    ap.add_argument(
        '--image-width',
        type=int,
        default=300,
        help='Image display width in pixel.'
    )
    ap.add_argument(
        '--image-height',
        type=int,
        default=300,
        help='Image display height in pixel.'
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
    dc_service = DataCollectorService(comm_config,
                                      args['data_dirpath'])
    UI(dc_service, args)


if __name__ == '__main__':
    main()
