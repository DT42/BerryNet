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

import telegram.ext
import logging
import paho.mqtt.client
import base64
import json
import tempfile
import os
import io

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload


# fill telegram bot token here.
telegramToken = "000000000:AABBCCDDEEFFAA-AABBAACCAADDAAEEFFFF"

if ("TELEGRAM_TOKEN" in os.environ):
    telegramToken = os.environ["TELEGRAM_TOKEN"]

updater = None
cameraHandlers = []


def hello(update, context):
    logging.info("Hello called")
    update.message.reply_text(
        'hello, {}'.format(update.message.from_user.first_name))


def camera(update, context):
    logging.info("camera called id: %s" % update.message.chat_id)
    # Register the chat-id for receiving images
    if (update.message.chat_id not in cameraHandlers):
        cameraHandlers.append (update.message.chat_id)


def on_connect(client, userdata, rc, _):
    # Subscribe bn_camera
    client.subscribe("berrynet/engine/darknet/result")


def on_message(client, userdata, msg):
    logging.info("MQTT message Topic: %s"%msg.topic)
    msg_json = payload.deserialize_payload(msg.payload);
    rawJPG = payload.destringify_jpg(msg_json["bytes"])
    photo1 = io.BytesIO(rawJPG)

    for u in cameraHandlers:
        if updater is None:
            continue
        logging.info("Send photo to %s"%u)
        updater.bot.send_photo(chat_id = u, photo=photo1)
        pass


# Setup logging format
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Connect to MQTT broker
mqttClient = paho.mqtt.client.Client()
mqttClient.on_connect = on_connect
mqttClient.on_message = on_message
mqttClient.connect("localhost")

mqttClient.loop_start()

# Connect to telegram
updater = telegram.ext.Updater(telegramToken,
                               use_context=True)

updater.dispatcher.add_handler(telegram.ext.CommandHandler('hello', hello))
updater.dispatcher.add_handler(telegram.ext.CommandHandler('camera', camera))

updater.start_polling()
