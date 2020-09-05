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

const fs = require('fs');
const moment = require('moment');
const mqtt = require('mqtt');
const config = require('./config');

const broker = config.brokerHost;
const client = mqtt.connect(broker);
const topicActionLog = config.topicActionLog;
const topicNotifyEmail = config.topicNotifyEmail;
const topicDashboardLog = config.topicDashboardLog;
const topicDashboardSnapshot = config.topicDashboardSnapshot;
const snapshot = config.snapshot;

let logs = [];

function log(m) {
  client.publish(topicActionLog, m);
  console.log(m);
}

function saveBufferToImage(b, filepath) {
  fs.writeFile(filepath, b, (e) => {
    if (e)
      log(`log client: cannot save buffer to image.`);
    else
      log(`log client: saved buffer to image successfully.`);
  });
}

client.on('connect', () => {
  client.subscribe(topicActionLog);
  client.subscribe(topicNotifyEmail);
  log(`log client: connected to ${broker} successfully.`);
});

client.on('message', (t, m) => {
  // secretly save a copy of the image
  if (t === topicNotifyEmail) {
    const filename = 'snapshot.jpg';
    saveBufferToImage(m, snapshot);
    client.publish(topicDashboardSnapshot, filename);
    return;
  }

  // less stackoverflowy
  if (String(m).match(/^log/))
    return;

  const now = moment().format('YYYY-MM-DD HH:mm:ss');

  logs.push(`[${now}] ` + m);

  if (logs.length > 10)
    logs.unshift();

  client.publish(topicDashboardLog, [].concat(logs).reverse().join('<br>'));
});
