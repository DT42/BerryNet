const readline = require('readline');
var qs = require("querystring");
var http = require("https");
const EventSource = require('eventsource');
const uuidv1 = require('node-uuid');

/* Please modify the following 3 const variables by the value provided
   from Nest credentials */
const PRODUCTID='904b7e35-33c8-45c6-8fd1-f5807b68f8e6';
const PRODUCTSECRET='QoXA0ALsxxIUDk78N8eSPwF0m';
const AUTHORIZATIONURL='https://home.nest.com/login/oauth2?client_id=PRODUCTID&state=STATE';

var CLIENTSTATE=uuidv1().replace(/-/g,'');
var PINCODE='';
var ACCESSTOKEN='';

console.log(AUTHORIZATIONURL.replace('STATE',CLIENTSTATE).replace('PRODUCTID',PRODUCTID));

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

rl.question('PINCODE? ', (answer) => {
    PINCODE = answer;

    var options = {
	"method": "POST",
	"hostname": "api.home.nest.com",
	"port": null,
	"path": "/oauth2/access_token",
	"headers": {
	    "content-type": "application/x-www-form-urlencoded"
	}
    };

    var req = http.request(options, function (res) {
	var chunks = [];
	
	res.on("data", function (chunk) {
	    chunks.push(chunk);
	});

	res.on("end", function () {
	    var body = Buffer.concat(chunks);
	    var bodyStr = body.toString();
	    
	    ACCESSTOKEN=JSON.parse(bodyStr);

	    var token = ACCESSTOKEN.access_token;
	    console.log("token="+token);
	    
	});
    });
    
    req.write(qs.stringify({ code: PINCODE,
			     client_id: PRODUCTID,
			     client_secret: PRODUCTSECRET,
			     grant_type: 'authorization_code' }));
    req.end();
    rl.close();
});

