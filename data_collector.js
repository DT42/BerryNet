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
const path = require('path');
const config = require('./config');

const broker = config.brokerHost;
const client = mqtt.connect(broker);
const topicActionLog = config.topicActionLog;
const topicActionInference = config.topicActionInference;
const topicDashboardSnapshot = config.topicDashboardSnapshot;
const topicJSONInferenceResult = config.topicJSONInferenceResult;
const storageDirPath = config.storageDirPath;


/**
 * Log wrapper to publish log message via MQTT and display on console.
 * @param {string} m Log message.
 */
function log(m) {
  client.publish(topicActionLog, m);
  console.log(m);
}

/**
 * Save published MQTT binary data as an image file.
 * @param {object} b The binary data published via MQTT.
 * @param {string} filepath The file path of the saved image.
 */
function saveBufferToImage(b, filepath) {
  fs.writeFile(filepath, b, (e) => {
    if (e)
      log(`log client: cannot save buffer to image.`);
    else
      log(`log client: saved buffer to image successfully.`);
  });
}

/**
 * Get time string in ISO format.
 * @return {string} Time string.
 */
function getTimeString() {
  const d = new Date();
  return d.toISOString();
}

/**
 * Save snapshot, detection image, and detection JSON to data directory.
 * @param {string} topic Subscribed MQTT topic.
 * @param {object} message Snapshot binary | 'snapshot.jpg' | detection JSON.
 */
function callbackSaveData(topic, message) {
  if (topic == topicActionInference) {
    console.log('Get ' + topicActionInference);

    // NOTE: topicActionInference always happens prior other topics.
    callbackSaveData.timeString = getTimeString();
    console.log(callbackSaveData.timeString);
    const snapshotImage = path.join(
      storageDirPath,
      callbackSaveData.timeString + '.jpg');
    saveBufferToImage(message, snapshotImage);
  } else if (topic == topicDashboardSnapshot) {
    console.log('Get ' + topicDashboardSnapshot);

    const detectionImage = path.join(
      storageDirPath,
      callbackSaveData.timeString + '-detection.jpg');
    /*
    fs.readFile(config.snapshot, (err, data) => {
      fs.writeFile(detectionImage, data, (e) => {
        if (e)
          log('Failed to save detection image.');
      });
    });
    */
    fs.createReadStream(config.snapshot)
      .pipe(fs.createWriteStream(detectionImage));
  } else if (topic == topicJSONInferenceResult) {
    console.log('Get ' + topicJSONInferenceResult);

    const detectionJSON = path.join(
      storageDirPath,
      callbackSaveData.timeString + '-detection.json');
    fs.writeFile(detectionJSON, message, (e) => {
      if (e)
        log('Failed to save detection JSON.');
    });
  } else {
    console.log('Unsubscribed topic ' + topic);
  }
}

fs.mkdir(storageDirPath, (e) => {
  if (e)
    log('Failed to create data storage dir.');
});

client.on('connect', () => {
  client.subscribe(topicActionLog);
  client.subscribe(topicActionInference);
  client.subscribe(topicDashboardSnapshot);
  client.subscribe(topicJSONInferenceResult);
  log(`log client: connected to ${broker} successfully.`);
});

client.on('message', callbackSaveData);
