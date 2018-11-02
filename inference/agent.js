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
const path = require('path');
const moment = require('moment');
const mqtt = require('mqtt');
const im = require('imagemagick');
const config = require('../config');

const broker = config.brokerHost;
const client = mqtt.connect(broker);
const topicActionLog = config.topicActionLog;
const topicActionInference = config.topicActionInference;
const topicDashboardSnapshot = config.topicDashboardSnapshot;
const topicDashboardInferenceResult = config.topicDashboardInferenceResult;
const topicJSONInferenceResult = config.topicJSONInferenceResult;
const topicNotifyLINE = config.topicNotifyLINE;
const inferenceEngine = config.inferenceEngine;

function log(m) {
  client.publish(topicActionLog, m);
  console.log(m);
}

function saveBufferToImage(b, filepath) {
  fs.writeFile(filepath, b, (e) => {
    if (e)
      log(`inference client: cannot save buffer to image.`);
    else
      log(`inference client: saved buffer to image ${filepath} successfully.`);
  });
}

const parseDarknet = function(str) {
  const elements = str.split(' ');
  // label might consists of multiple words, e.g. cell phone.
  const label = elements.slice(0, elements.length - 5).join(' ');
  let [confidence, x, y, width, height] = elements.slice(elements.length - 5);
  let result = {
    label: label,
    confidence: parseFloat(confidence),
    top: parseInt(y),
    bottom: parseInt(y) + parseInt(height),
    left: parseInt(x),
    right: parseInt(x) + parseInt(width)
  };
  return result
}

const darknetToJSON = function(data) {
  let dataStrList = data.toString().replace(/\n$/, '').split('\n');
  let jsonResult = [];
  for (let i in dataStrList) {
    let item = `${dataStrList[i]}`;
    jsonResult.push(parseDarknet(item));
  }
  return jsonResult;
};

client.on('connect', () => {
  client.subscribe(topicActionInference);
  log(`inference client: connected to ${broker} successfully.`);
});

client.on('message', (t, m) => {
  const size = m.length;
  const now = moment().format('YYYYMMDD-HHmmss');
  const inference_server_img_dir = __dirname + '/image';
  const snapshot = `snapshot-${now}.jpg`;
  const snapshot_path = path.join(inference_server_img_dir, snapshot);
  const donefile_path = snapshot_path + '.done';
  const resultfile_path = snapshot_path + '.txt';
  const resultdonefile_path = snapshot_path + '.txt.done';
  const dashboard_image_path = __dirname + '/../dashboard/www/freeboard/snapshot.jpg';

  log(`inference client: on topic ${t}, received ${size} bytes.`);

  // Save snapshot and create its done file.  Classifier/detector will
  // be triggered after snapshot done file is created.
  saveBufferToImage(m, snapshot_path);
  fs.closeSync(fs.openSync(donefile_path, 'w'));
  log('Image done file ' + donefile_path + ' is ready.');

  // Listen to classifier/detector's result done file.  When result done
  // file (.txt.done) is created, result is available.
  var watcher = fs.watch(inference_server_img_dir, (eventType, filename) => {
    if (eventType === 'rename') {
      if (filename === (snapshot + '.txt.done')) {
        fs.readFile(resultfile_path, (err, result) => {
          if (err) throw err

          watcher.close();

          if (inferenceEngine === 'classifier') {
            fs.writeFile(dashboard_image_path, m, (err, written, buffer) => {
              console.log('Written snapshot to dashboard image directory: ' + dashboard_image_path);
              client.publish(topicDashboardSnapshot, 'snapshot.jpg');
            })
            client.publish(topicDashboardInferenceResult,
              result.toString().replace(/(\n)+/g, '<br />'));
          } else if (inferenceEngine === 'detector') {
            console.log('Snapshot is created by detector, only notify dashboard to update.');
            client.publish(topicDashboardSnapshot, 'snapshot.jpg');
            client.publish(topicDashboardInferenceResult,
              result.toString().replace(/(\n)+/g, '<br />'));
            client.publish(topicJSONInferenceResult,
              JSON.stringify(darknetToJSON(result)));

            // Delete intermediate files.
            //
            // Note: Data collector will not be affected. It retrieves data from
            //   * topicActionInference: contains snapshot raw data
            //   * topicDashboardSnapshot: to copy snapshot with bounding boxes
            //   * topicDashboardInferenceResult: contains inference result string
            fs.unlink(snapshot_path, (e) => {});
            fs.unlink(resultfile_path, (e) => {});
            fs.unlink(resultdonefile_path, (e) => {});
          } else {
            console.log('Unknown owner ' + inferenceEngine);
          }

          client.publish(topicNotifyLINE, dashboard_image_path);
        })
      } else {
        console.log('rename event for ' +
                    filename +
                    ', but it is not inference result done file.');
      }
    } else {
      console.log(eventType + ' event for ' + filename + ', ignore it.');
    }
  });
});
