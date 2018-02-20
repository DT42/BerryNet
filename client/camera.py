#!/usr/bin/python3

from datetime import datetime

import cv2

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload


def main():
    comm_config = {
        'subscribe': {},
        'broker': {
            'address': 'localhost',
            'port': 1883
        }
    }
    comm = Communicator(comm_config, debug=True)

    duration = lambda t: (datetime.now() - t).microseconds / 1000

    video_mode = False
    if video_mode:
        counter = 0
        capture = cv2.VideoCapture(0)
        while True:
            status, im = capture.read()
            if (status is False):
                logger.warn('ERROR: Failure happened when reading frame')

            t = datetime.now()
            retval, jpg_bytes = cv2.imencode('.jpg', im)
            mqtt_payload = payload.serialize_jpg(jpg_bytes)
            comm.send('data/rgbimage', mqtt_payload)
            logger.debug('send: {} ms'.format(duration(t)))

            counter += 1
            if counter >= 30:
                break
    else:
        # Prepare MQTT payload
        im = cv2.imread('/home/debug/codes/tensorflow/tensorflow/examples/label_image/data/grace_hopper.jpg')
        retval, jpg_bytes = cv2.imencode('.jpg', im)

        t = datetime.now()
        mqtt_payload = payload.serialize_jpg(jpg_bytes)
        logger.debug('payload: {} ms'.format(duration(t)))
        logger.debug('payload size: {}'.format(len(mqtt_payload)))

        # Client publishes payload
        t = datetime.now()
        comm.send('data/rgbimage', mqtt_payload)
        logger.debug('mqtt.publish: {} ms'.format(duration(t)))
        logger.debug('publish at {}'.format(datetime.now().isoformat()))


if __name__ == '__main__':
    main()
