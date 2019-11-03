#!/usr/bin/env python3

import telegram.ext
import logging
import paho.mqtt.client
import base64
import json
import tempfile
import os

# fill telegram bot token here.
telegramToken = "000000000:AABBCCDDEEFFAA-AABBAACCAADDAAEEFFFF"

if ("TELEGRAM_TOKEN" in os.environ):
    telegramToken = os.environ["TELEGRAM_TOKEN"]

updater = None

def hello(update, context):
    logging.info("Hello called")
    update.message.reply_text(
        'hello, {}'.format(update.message.from_user.first_name))

cameraHandlers = []
    
def camera(update, context):
    logging.info("camera called id: %s" % update.message.chat_id)
    # Register the chat-id for receiving images
    if (update.message.chat_id not in cameraHandlers):
        cameraHandlers.append (update.message.chat_id)
    
def on_connect(client, userdata, rc, _):
    # Subscribe bn_camera
    client.subscribe("berrynet/data/rgbimage")

def on_message(client, userdata, msg):
    logging.info("MQTT message Topic: %s"%msg.topic)
    img = json.loads(msg.payload);
    rawJPG = base64.b64decode(img["bytes"])
    for u in cameraHandlers:
        if updater is None:
            continue
        logging.info("Send photo to %s"%u)
        tmpfile, tmpfilename = tempfile.mkstemp()
        os.write(tmpfile, rawJPG)
        os.sync()
        updater.bot.send_photo(chat_id = u, photo=open(tmpfilename, "rb"))
        os.close()
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
