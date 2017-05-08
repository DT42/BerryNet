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
const mqtt = require('mqtt');
const request = require('request');
const spawnsync = require('child_process').spawnSync;
const config = require('./config');

const broker = config.brokerHost;
const client = mqtt.connect(broker);
const topicActionLog = config.topicActionLog;
const topicActionInference = config.topicActionInference;
const topicEventCamera = config.topicEventCamera;
const cameraURI = config.ipcameraSnapshot;
const snapshotFile = '/tmp/snapshot.jpg';
const cameraCmd = '/usr/bin/raspistill';
const cameraArgs = ['-vf', '-hf',
  '-w', '1024', '-h', '768',
  '-o', snapshotFile];

function log(m) {
  client.publish(topicActionLog, m);
  console.log(m);
}

client.on('connect', () => {
  client.subscribe(topicEventCamera);
  log(`camera client: connected to ${broker} successfully.`);
});

client.on('message', (t, m) => {
  log(`camera client: on topic ${t}, received message ${m}.`);

  const action = m.toString();
  if (action == 'snapshot_picam') {
    // Take a snapshot from RPi3 camera. The snapshot will be displayed
    // on dashboard.
    spawnsync(cameraCmd, cameraArgs);
    fs.readFile(snapshotFile, function(err, data) {
      if (err) {
        log('camera client: cannot get image.');
      } else {
        log('camera client: publishing image.');
        client.publish(topicActionInference, data);
      }
    });
  } else if (action == 'snapshot_ipcam') {
    // Take a snapshot from IP camera. The snapshot will be sent to
    // configured email address.
    request.get(
      {uri: cameraURI, encoding: null},
      (e, res, body) => {
        if (!e && res.statusCode == 200) {
          log('camera client: publishing image.');
          client.publish(topicActionInference, body);
        } else {
          log('camera client: cannot get image.');
        }
      }
    );
  } else {
    log('camera client: unkown action.');
  }
});
