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
const cv = require('opencv');

const broker = config.brokerHost;
const client = mqtt.connect(broker);
const topicActionLog = config.topicActionLog;
const topicActionInference = config.topicActionInference;
const topicEventCamera = config.topicEventCamera;
const cameraURI = config.ipcameraSnapshot;
const snapshotFile = '/tmp/snapshot.jpg';
const snapshotWidth = config.boardcameraImageWidth;
const snapshotHeight = config.boardcameraImageHeight;
const cameraCmd = '/usr/bin/raspistill';
const cameraArgs = ['-vf', '-hf',
  '-w', snapshotWidth,
  '-h', snapshotHeight,
  '-o', snapshotFile];
const usbCameraCmd = '/usr/bin/fswebcam';
const usbCameraArgs = ['-r', snapshotWidth + 'x' + snapshotHeight,
  '--no-banner', '-D', '0.5', snapshotFile];
const fps = 30;
var cameraIntervalID = null;
var cameraInterval = 1000.0 / fps;
var cameraCV = null;
var frameCounter = 0;

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
    /* NOTE: We use V4L2 to support RPi camera, so RPi camera's usage is
     *       the same as USB camera. Both RPi and USB cameras are called
     *       "board camera".
     *
     *       This action is obsoleted and will be removed in the future.
     */

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
  } else if (action == 'snapshot_boardcam') {
    // Take a snapshot from USB camera.
    spawnsync(usbCameraCmd, usbCameraArgs);
    fs.readFile(snapshotFile, function(err, data) {
      if (err) {
        log('camera client: cannot get image.');
      } else {
        log('camera client: publishing image.');
        client.publish(topicActionInference, data);
      }
    });
  } else if (action == 'stream_boardcam_start') {
    if ((!cameraCV) && (!cameraIntervalID)) {
      cameraCV = new cv.VideoCapture(0);
      cameraCV.setWidth(snapshotWidth);
      cameraCV.setHeight(snapshotHeight);
      cameraIntervalID = setInterval(function() {
        cameraCV.read(function(err, im) {
          if (err) {
            throw err;
          }
          if (frameCounter < fps * 2) {
            frameCounter++;
          } else {
            frameCounter = 0;
            im.save(snapshotFile);
            fs.readFile(snapshotFile, function(err, data) {
              if (err) {
                log('camera client: cannot get image.');
              } else {
                log('camera client: publishing image.');
                client.publish(topicActionInference, data);
              }
            });
          }
          im.release();
        });
      }, cameraInterval);
    }
  } else if (action == 'stream_boardcam_stop') {
    if (cameraCV) {
      cameraCV.release();
      cameraCV = null;
    }
    if (cameraIntervalID) {
      clearInterval(cameraIntervalID);
      cameraIntervalID = null;
    }
  } else if (action == 'stream_nest_ipcam_start') {
    if (!cameraIntervalID) {
      cameraIntervalID = setInterval(function() {
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
      }, cameraInterval);
    }
  } else if (action == 'stream_nest_ipcam_stop') {
    if (cameraIntervalID) {
      clearInterval(cameraIntervalID);
      cameraIntervalID = null;
    }
  } else {
    log('camera client: unknown action.');
  }
});
