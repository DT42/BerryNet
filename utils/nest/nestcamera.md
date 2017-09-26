Nest IP Camera libs
=======================


Nest IP Camera Introduction
------------------------
Nest IP Camera is a really closed product. The setup program
for PC are only supported on Windows and MacOS.
If the camera is not connect to your home WiFi, you have to
use Windows or MacOS to let it connect before usage.

Also the power charger is also important. The camera won't start unless
it connects to its official power charger. So make sure your camera is
connected to WiFi and is running.


APIs
------------------------
There's no way to directly connect to the camera even it is in your local
lan. To access the snapshot from the camera, you have to use their *cloud*
API to obtain it. So basically everything is controlled by their cloud.


Old v2/mobile API
------------------------
This library is inside npm. To install it, just use

~~~
npm install nest-api
~~~

However, this api is obsolete and no documents can be found.
But it still works partially. The way to use this API is provide your
username (normally e-mail address) and your password.

~~~
var NEST_USER='paulliu@dt42.io';
var NEST_PASSWORD='************';
var nestApi = new NestApi(NEST_USER, NEST_PASSWORD);
 
nestApi.login(function(sessionData) {
    console.log(sessionData);
    nestApi.get(function(data) {
        console.log(data);
        nestApi.post({'path':'/v2/mobile/'+sessionData.user+'/quartz/CAMERAID/public_share_enabled', 'body':'true'}, function(data2) {
            console.log(data2);
        });
    });
});
~~~

But the post method seems cannot modify the public_shared_enabled flag.
I haven't try all of them.


v3 API
-------------------------------------------
This is an OAuth Restful API. You need to register your app/product first.
So please go to https://console.developers.nest.com/products
and register a product. The "support URL" field can be http://localhost because
we are not actually a web app.

After that, you'll get 3 credentials.

 1. Product ID
 2. Product Secret
 3. Authorization URL

First, generate proper unique and secure STATE parameter and replace the
STATE in Authorization URL, show that URL to the user.

The user will use that URL in the browser and get a PINCODE to you.

Then use the PINCODE to get a token.

By using that token, you can use all of the Rest APIs.

We wrote 3 small scripts to show how to do this.
First, please replace the credentials provided from Nest into nest_get_token.js

Each time you run nest_get_token.js you'll be shown an URL and waiting you
to enter the PINCODE. You have to use your browser to open that URL and
obtain the PINCODE for the program to continue. The program will later
show you the token after you input the PINCODE.

And then you can run nest_get_snapshoturl_by_token.js and provide the token
obtain from the above to get the snapshoturl.

We also wrote a small script for you to do that. Just run
nest_get_snapshoturl.sh and it will call the two scripts from the above and
give you the snapshoturl of Nest IP camera.


Streaming
---------------
Currently there's no way to obtain the streaming from Nest IP camera.
