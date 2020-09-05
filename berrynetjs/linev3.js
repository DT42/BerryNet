// Copyright 2017 DT42 Inc.
//
// This file is part of BerryNet.
//
// BerryNet is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// BerryNet is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with BerryNet.  If not, see <http://www.gnu.org/licenses/>.

'use strict';

const mqtt = require('mqtt');
const line = require('@line/bot-sdk');
const imgur = require('imgur');
const config = require('./config');

const broker = config.brokerHost;
const client = mqtt.connect(broker);
const topicActionLog = config.topicActionLog;
const topicInferenceResult = 'berrynet/engine/darknet/result'
//const topicInferenceResult = 'berrynet/data/rgbimage'
const targetUserID = config.LINETargetUserID;

// create LINE SDK config
const LINEConfig = {
  channelAccessToken: config.LINEChannelAccessToken,
  channelSecret: config.LINEChannelSecret,
};

// create LINE SDK client
const LINEClient = new line.Client(LINEConfig);

function log(m) {
  client.publish(topicActionLog, m)
  console.log(m)
}

/**
 * Debugging utility to display inference result content.
 *
 * @param {Object} result Inference result in JSON format
 */
function debugPrintInferenceResult(result) {
  // modify result will cause side effect because of calling by reference
  const b64str = result["bytes"]
  delete result["bytes"]
  result["annotations"] = {
    "type": "detection",
    "label": "dog",
    "confidence": 0.95,
    "left": 10,
    "top": 10,
    "right": 50,
    "bottom": 50
  }
  console.log(result)
  result["bytes"] = b64str
}

/**
 * Send text and image in the inference result to LINE client.
 *
 * @param {Object} result Inference result in JSON format
 */
function notifyLine(result) {
  //debugPrintInferenceResult(result)

  // Send base64-encoded image in result
  imgur.uploadBase64(result["bytes"])
    .then((json) => {
      var imgurLink = json.data.link;
      imgurLink = imgurLink.replace('http:\/\/', 'https:\/\/')
      log(`An image has been uploaded to imgur. link: ${imgurLink}`)

      // Image can only be delivered via 'https://' URL, 'http://' doesn't work
      LINEClient.pushMessage(targetUserID, { type: 'image',
                                             originalContentUrl: imgurLink,
                                             previewImageUrl: imgurLink })
        .then((v) => {
          log(`A message sent to ${targetUserID} successfully.`)
        })
        .catch((err) => {
          log(`An error occurred, ${err}.`)
        });
    })
    .catch((err) => {
      log(`An error occurred. ${err}`)
    })

  // Send annotations in result
  LINEClient.pushMessage(targetUserID,
                         {
                           type: 'text',
                           text: JSON.stringify(result["annotations"])
                         })
}

client.on('connect', () => {
  client.subscribe(topicInferenceResult)
  log(`client connected to ${broker} successfully.`)
})

client.on('message', (t, m) => {
  const size = m.length
  log(`client on topic ${t}, received ${size} bytes.`)

  notifyLine(JSON.parse(m.toString()))
})
