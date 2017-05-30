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

// Usage:
// ./mail.js <sender account> <sender password> <recipient mail address>
// This app assumes the user uses gmail.
// You may need to configure "Allow Less Secure Apps" in your Gmail account.

'use strict';

const fs = require('fs');
const path = require('path');
const moment = require('moment');
const mqtt = require('mqtt');
const line = require('@line/bot-sdk');
const imgur = require('imgur');
const config = require('./config');

const broker = config.brokerHost;
const client = mqtt.connect(broker);
const topicActionLog = config.topicActionLog;
const topicNotifyLINE = config.topicNotifyLINE;
const channelID = config.LINEChannelID;

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

function saveBufferToImage(b, filepath) {
  fs.writeFile(filepath, b, (e) => {
    if (e)
      log(`LINE client: cannot save buffer to image.`);
    else
      log(`LINE client: saved buffer to image ${filepath} successfully.`);
  });
}

client.on('connect', () => {
  client.subscribe(topicNotifyLINE);
  log(`LINE client: connected to ${broker} successfully.`);
});

client.on('message', (t, m) => {
  const size = m.length;
  log(`LINE client: on topic ${t}, received ${size} bytes.`)

  // save image to file and upload it to imgur for display in LINE message
  const now = moment().format('YYYYMMDD-HHmmss');
  const snapshot = `snapshot-${now}.jpg`
  const snapshot_path = path.join('/tmp', snapshot)
  saveBufferToImage(m, snapshot_path);
  imgur.uploadFile(snapshot_path)
    .then((json) => {
      var imgur_link = json.data.link;
      imgur_link = imgur_link.replace('http:\/\/', 'https:\/\/');
      log(`LINE client: An image has been uploaded to imgur. link: ${imgur_link}`);

      // Image can only be delivered via 'https://' URL, 'http://' doesn't work 
      LINEClient.pushMessage(channelID, [{ type: 'text', 
                                           text: now },
                                         { type: 'image', 
                                           originalContentUrl: imgur_link,
                                           previewImageUrl: imgur_link }
                                        ])
        .then((v) => {
          log(`LINE client: message sent to ${channelID} successfully.`);
        })
        .catch((err) => {
          log(`LINE client: an error occurred, ${err}.`);
        });
    })
    .catch((err) => {
      log(`LINE client: an error occurred. ${err}`);
    });
});
