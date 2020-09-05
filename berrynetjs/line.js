// Copyright 2017 DT42
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
const topicNotifyLINE = config.topicNotifyLINE;
const topicDashboardInferenceResult = config.topicDashboardInferenceResult;
const targetUserID = config.LINETargetUserID;

// create LINE SDK config
const LINEConfig = {
  channelAccessToken: config.LINEChannelAccessToken,
  channelSecret: config.LINEChannelSecret,
};

// create LINE SDK client
const LINEClient = new line.Client(LINEConfig);

function log(m) {
  client.publish(topicActionLog, m);
  console.log(m);
}

client.on('connect', () => {
  client.subscribe(topicNotifyLINE);
  client.subscribe(topicDashboardInferenceResult);
  log(`client connected to ${broker} successfully.`);
});

client.on('message', (t, m) => {
  const size = m.length;
  log(`client on topic ${t}, received ${size} bytes.`)

  if (t === topicDashboardInferenceResult) {
    const result = m.toString();
    LINEClient.pushMessage(targetUserID, { type: 'text', text: result });
    return;
  }

  // save image to file and upload it to imgur for display in LINE message
  const snapshot_path = m.toString();
  imgur.uploadFile(snapshot_path)
    .then((json) => {
      var imgurLink = json.data.link;
      imgurLink = imgurLink.replace('http:\/\/', 'https:\/\/');
      log(`An image has been uploaded to imgur. link: ${imgurLink}`);

      // Image can only be delivered via 'https://' URL, 'http://' doesn't work
      LINEClient.pushMessage(targetUserID, { type: 'image',
                                             originalContentUrl: imgurLink,
                                             previewImageUrl: imgurLink })
        .then((v) => {
          log(`A message sent to ${targetUserID} successfully.`);
        })
        .catch((err) => {
          log(`An error occurred, ${err}.`);
        });
    })
    .catch((err) => {
      log(`An error occurred. ${err}`);
    });
});
