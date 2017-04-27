#!/usr/bin/env node

'use strict';

const exec = require('child_process').exec;
const process = require('process');
const fs = require('fs');

function execCallback(error, stdout, stderr) {
  if (error) {
    console.error(`exec error: ${error}`);
    return;
  }
  console.log(`stdout: ${stdout}`);
  console.log(`stderr: ${stderr}`);
}

//const config = JSON.parse(fs.readFileSync('config.json').toString());
const broker = exec('node broker.js', execCallback);
const cameraAgent = exec('node camera.js', execCallback);
//const eventNotifier = exec('node mail.js ' + config.sender_email + ' ' + config.sender_email_password + ' ' + config.receiver_email, execCallback);
const eventLogger = exec('node journal.js', execCallback);
const webServer = exec('cd dashboard && node server.js', execCallback);
//const dlClassifier = exec('cd inference && python classify_server.py --model_dir=model --image_dir=image', execCallback);
const dlDetector = exec('cd inference/darkflow && python detection_server.py', execCallback);
const inferenceAgent = exec('cd inference && node agent.js', execCallback);
const localImageAgent = exec('node localimg.js', execCallback);
const webBrowser = exec('DISPLAY=:0 sensible-browser http://localhost:8080/index.html#source=dashboard.json', execCallback);

broker.stdout.on('data', function(data) {
  console.log("[broker] " + data);
});

cameraAgent.stdout.on('data', function(data) {
  console.log("[cameraAgent] " + data);
});

//eventNotifier.stdout.on('data', function(data) {
//  console.log('[eventNotifier] ' + data);
//});

eventLogger.stdout.on('data', function(data) {
  console.log('[eventLogger] ' + data);
});

webServer.stdout.on('data', function(data) {
  console.log('[webServer] ' + data);
});

dlDetector.stdout.on('data', function(data) {
  console.log('[detector] ' + data);
});

inferenceAgent.stdout.on('data', function(data) {
  console.log('[inferenceAgent] ' + data);
});

process.on('SIGINT', function() {
  console.log('Get SIGINT');
  broker.kill();
  cameraAgent.kill();
  eventNotifier.kill();
  eventLogger.kill();
  webServer.kill();
  //dlClassifier.kill();
  dlDetector.kill();
  inferenceAgent.kill();
  process.exit(0);
});
