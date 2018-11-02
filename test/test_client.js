var expect = require("chai").expect;
var assert = require("assert");
var mqtt = require("mqtt");
var exec = require("child_process").exec;

function execCallback(error, stdout, stderr) {
  if (error) {
    console.error(`exec error: ${error}`);
    return;
  }
  console.log(`stdout: ${stdout}`);
  console.log(`stderr: ${stderr}`);
}

describe("Broker running test", function() {
  it("ping broker", function(done) {
    this.timeout(5000);

    var broker = exec("node broker.js", execCallback);
    var client = mqtt.connect("mqtt://localhost");

    client.on('connect', function () {
      client.subscribe('presence');
      client.publish('presence', 'Hello mqtt');
    });

    client.on('message', function (topic, message) {
      assert.equal(message.toString(), "Hello mqtt");
      client.end();
    });

    setTimeout(done, 4000);
    broker.kill();
  });
});
