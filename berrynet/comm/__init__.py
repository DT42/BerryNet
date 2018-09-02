#!/usr/bin/python3

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

from berrynet import logger
from logzero import setup_logger


def on_connect(client, userdata, flags, rc):
    logger.debug('Connected with result code ' + str(rc))
    for topic in client.comm_config['subscribe'].keys():
        logger.debug('Subscribe topic {}'.format(topic))
        client.subscribe(topic)


def on_message(client, userdata, msg):
    """Dispatch received message to its bound functor.
    """
    logger.debug('Receive message from topic {}'.format(msg.topic))
    #logger.debug('Message payload {}'.format(msg.payload))
    client.comm_config['subscribe'][msg.topic](msg.payload)


class Communicator(object):
    def __init__(self, comm_config, debug=False):
        self.client = mqtt.Client()
        self.client.comm_config = comm_config
        self.client.on_connect = on_connect
        self.client.on_message = on_message

    def run(self):
        self.client.connect(
            self.client.comm_config['broker']['address'],
            self.client.comm_config['broker']['port'],
            60)
        self.client.loop_forever()

    def start_nb(self):
        self.client.connect(
            self.client.comm_config['broker']['address'],
            self.client.comm_config['broker']['port'],
            60)
        self.client.loop_start()

    def stop_nb(self):
        self.client.loop_stop()

    def send(self, topic, payload):
        logger.debug('Send message to topic {}'.format(topic))
        #logger.debug('Message payload {}'.format(payload))
        publish.single(topic, payload,
                       hostname=self.client.comm_config['broker']['address'])

    def disconnect(self):
        self.client.disconnect()
