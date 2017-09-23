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

const path = require('path');

let config = {};

// system configs
config.projectDir = __dirname;
config.inferenceEngine = 'detector';  // {classifier, detector}

// gateway configs
function padTopicBase(topic) {
  return path.join(config.topicBase, topic);
}

config.snapshot = path.join(
  config.projectDir,
  'dashboard/www/freeboard/snapshot.jpg');
config.brokerHost = 'mqtt://localhost';
config.topicBase = 'berrynet';
config.topicActionLog = padTopicBase('action/log');
config.topicActionInference = padTopicBase('action/inference');
config.topicEventCamera = padTopicBase('event/camera');
config.topicEventLocalImage = padTopicBase('event/localImage');
config.topicNotifyEmail = padTopicBase('notify/email');
config.topicNotifySMS = padTopicBase('notify/sms');
config.topicDashboardLog = padTopicBase('dashboard/log');
config.topicDashboardSnapshot = padTopicBase('dashboard/snapshot');
config.topicDashboardInferenceResult = padTopicBase('dashboard/inferenceResult');

// IP camera
config.ipcameraSnapshot = '';

// data collector configs
config.storageDirPath = '';

// email notification
config.senderEmail = 'SENDER_EMAIL';
config.senderPassword = 'SENDER_PASSWORD';
config.receiverEmail = 'RECEIVER_EMAIL';

// for compatibility
config.sender_email = config.senderEmail;
config.sender_password = config.senderPassword;
config.receiver_email = config.receiverEmail;

// make config importable
module.exports = config;
