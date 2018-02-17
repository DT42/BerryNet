#!/usr/bin/python3

import logging

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

from logzero import setup_logger


logger = setup_logger(name='comm', logfile='/tmp/comm.log')


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
        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    def run(self):
        self.client.connect(
            self.client.comm_config['broker']['address'],
            self.client.comm_config['broker']['port'],
            60)
        self.client.loop_forever()

    def send(self, topic, payload):
        logger.debug('Send message to topic {}'.format(topic))
        #logger.debug('Message payload {}'.format(payload))
        publish.single(topic, payload,
                       hostname=self.client.comm_config['broker']['address'])
