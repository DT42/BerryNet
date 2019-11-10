#!/usr/bin/env python3
#
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

import argparse
import json
import io
import logging
import os

import telegram.ext
from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload


class TelegramBotService(object):
    def __init__(self, comm_config, token, debug=False):
        self.comm_config = comm_config
        for topic, functor in self.comm_config['subscribe'].items():
            self.comm_config['subscribe'][topic] = eval(functor)
        self.comm = Communicator(self.comm_config, debug=True)
        self.token = token
        self.debug = debug

        # Telegram Updater employs Telegram Dispatcher which dispatches
        # updates to its registered handlers.
        self.updater = telegram.ext.Updater(self.token,
                                            use_context=True)
        self.cameraHandlers = []

    def update(self, pl):
        try:
            payload_json = payload.deserialize_payload(pl.decode('utf-8'))
            jpg_bytes = payload.destringify_jpg(payload_json["bytes"])
            jpg_file_descriptor = io.BytesIO(jpg_bytes)

            for u in self.cameraHandlers:
                if self.updater is None:
                    continue
                logger.info("Send photo to %s" % u)
                self.updater.bot.send_photo(chat_id = u, photo=jpg_file_descriptor)
                pass
        except Exception as e:
            logger.info(e)

    def run(self, args):
        """Infinite loop serving inference requests"""
        self.comm.start_nb()
        self.connect_telegram()

    def connect_telegram(self):
        try:
            self.updater.dispatcher.add_handler(
                telegram.ext.CommandHandler('help', self.handler_help))
            self.updater.dispatcher.add_handler(
                telegram.ext.CommandHandler('hello', self.handler_hello))
            self.updater.dispatcher.add_handler(
                telegram.ext.CommandHandler('camera', self.handler_camera))
            self.updater.start_polling()
        except Exception as e:
            logger.critical(e)

    def handler_help(self, update, context):
        logger.info("Received command `help`")
        update.message.reply_text(
            'I support these commands: help, hello, camera')

    def handler_hello(self, update, context):
        logger.info("Received command `hello`")
        update.message.reply_text(
            'Hello, {}'.format(update.message.from_user.first_name))

    def handler_camera(self, update, context):
        logger.info("Received command `camera`, chat id: %s" % update.message.chat_id)
        # Register the chat-id for receiving images
        if (update.message.chat_id not in self.cameraHandlers):
            self.cameraHandlers.append (update.message.chat_id)
        update.message.reply_text('Dear, I am ready to help send notification')


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--token',
        help='Telegram token got from BotFather.'
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
        '--topic',
        nargs='*',
        default=['berrynet/engine/tflitedetector/result'],
        help='The topic to listen, and can be indicated multiple times.'
    )
    ap.add_argument(
        '--topic-action',
        default='self.update',
        help='The action for the indicated topics.'
    )
    ap.add_argument(
        '--topic-config',
        default=None,
        help='Path of the MQTT topic subscription JSON.'
    )
    ap.add_argument('--debug',
        action='store_true',
        help='Debug mode toggle'
    )
    return vars(ap.parse_args())


def main():
    args = parse_args()
    if args['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Topics and actions can come from two sources: CLI and config file.
    # Setup topic_config by parsing values from the two sources.
    if args['topic_config']:
        with open(args['topic_config']) as f:
            topic_config = json.load(f)
    else:
        topic_config = {}
    topic_config.update({t:args['topic_action'] for t in args['topic']})

    comm_config = {
        'subscribe': topic_config,
        'broker': {
            'address': args['broker_ip'],
            'port': args['broker_port']
        }
    }
    telbot_service = TelegramBotService(comm_config,
                                        args['token'],
                                        args['debug'])
    telbot_service.run(args)


if __name__ == '__main__':
    main()
