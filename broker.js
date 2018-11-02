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

const mosca = require('mosca');

// ascoltatore: https://github.com/mcollina/ascoltatori
const ascoltatore = {
  type: 'mongo',
  url: 'mongodb://localhost:27017/mqtt',
  pubsubCollection: 'ascoltatori',
  mongo: {}
};

const settings = {
  port: 1883,
  backend: ascoltatore,
  http: {
    port: 3000,
    bundle: true,
    static: './'
  }
};

const server = new mosca.Server(settings);

server.on('clientConnected', (client) => {
    console.log('client connected', client.id);
});

// fired when a message is received
server.on('published', (packet, client) => {
  console.log('Server published. Avoid showing package content here.');
});

// fired when the mqtt server is ready
server.on('ready', () => {
  console.log('Mosca server is up and running');
});
