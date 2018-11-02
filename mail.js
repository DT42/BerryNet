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

const assert = require('assert');
const emailjs = require('emailjs');
const moment = require('moment');
const mqtt = require('mqtt');

assert(process.argv.length == 5);

const broker = 'mqtt://localhost';
const client = mqtt.connect(broker);
const mail_topic = 'dt42/mail';
const log_topic = 'dt42/log';

const args = process.argv.slice(2);
const account = args[0];
const password = args[1];
const recipient = args[2];

function log(m) {
  client.publish(log_topic, m);
  console.log(m);
}

const server = emailjs.server.connect({
  user: `${account}`,
  password: password,
  host: 'smtp.gmail.com',
  ssl: true,
});

client.on('connect', () => {
  client.subscribe(mail_topic);
  log(`mail client: connected to ${broker} successfully.`);
});

client.on('message', (t, m) => {
  const size = m.length;
  log(`mail client: on topic ${t}, received ${size} bytes.`)

  const now = moment().format('YYYY-MM-DD-HH-mm-ss');
  server.send({
    from: `<${account}>`,
    to: `<${recipient}>`,
    subject: `DT42 MQTT Snapshot at ${now}`,
    text: ' ',
    attachment: [{
      name: 'snapshot.jpg',
      data: m,
    }],
  }, (e, m) => {
    if (e) {
      log(`mail client: an error occurred, ${e}.`);
      return;
    }
    if (m)
      log(`mail client: mail sent to ${recipient} successfully.`);
  });
});
