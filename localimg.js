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

// Read a local image and send it to inference server.
//
// subscribe
//     dt42/localimg
// publish
//     dt42/inference
//     dt42/log
//
// $ node localimg.js
// $ mosquitto_pub -h localhost -t dt42/localimg -m <imgpath>

'use strict';

const mqtt = require('mqtt')
const request = require('request')
const spawnsync = require('child_process').spawnSync
const fs = require('fs')
const config = require('./config');

const broker = config.brokerHost;
const client = mqtt.connect(broker);
const topicEventLocalImage = config.topicEventLocalImage;
const topicActionLog = config.topicActionLog;
const topicActionInference = config.topicActionInference;

function log(m) {
  client.publish(topicActionLog, m);
  console.log(m);
}

client.on('connect', () => {
  client.subscribe(topicEventLocalImage);
  log(`localimg client: connected to ${broker} successfully.`);
});

client.on('message', (t, m) => {
  log(`camera client: on topic ${t}, received message ${m}.`);

  const imgurl = m.toString();
  // Take a local image as snapshot. The snapshot will be displayed
  // on dashboard.
  fs.readFile(imgurl, function(err, data) {
    if (err) {
      log('localimg client: cannot get image.');
    } else {
      log('localimg client: publishing image.');
      client.publish(topicActionInference, data);
    }
  });
});
