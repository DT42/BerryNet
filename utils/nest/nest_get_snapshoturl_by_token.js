var Client = require('node-rest-client').Client;

var ACCESSTOKEN='';
const NEST_API_URL = 'https://developer-api.nest.com';

function usage() {
    if (process.argv.length >= 2) {
	console.log("Usage: "+process.argv[0]+" "+process.argv[1]+" <access_token>");
    } else if (process.argv.length >= 1) {
	console.log("Usage: "+process.argv[0]+" <access_token>");
    } else {
	console.log("Usage: node nest_get_snapshoturl_by_token.js <access_token>");
    }
}

if (process.argv.length <= 2) {
    usage();
    process.exit(0);
}

ACCESSTOKEN=process.argv[2];

var client = new Client();
var args = {
        headers: {
	    "Authorization": 'Bearer ' + ACCESSTOKEN
	}
};

client.get(NEST_API_URL, args, function (data, response) {
    var cameras=data.devices.cameras;

    for (i=0; i<Object.keys(cameras).length; i++) {
	var cameraID = Object.keys(cameras)[i];
	var snapshotURL = cameras[cameraID].snapshot_url;
	var webURL = cameras[cameraID].web_url;
	console.log(cameraID+" snapshot_url: "+snapshotURL);
	console.log(cameraID+" web_url: "+webURL);
    }
});
