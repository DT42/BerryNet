// # A Freeboard Plugin for IBM's IoT Foundation service; https://internetofthings.ibmcloud.com/

(function()
{
	// ### Datasource Definition
	//
	// -------------------
	freeboard.loadDatasourcePlugin({
		"type_name"   : "ibm_iotf",
		"display_name": "IBM IoT Foundation",
        "description" : "Receive data from your devices in IBM IoT Foundation.",
		"external_scripts" : [
			"<full address of the paho mqtt javascript client>"
		],
		"settings"    : [
			{
				"name"         : "org_id",
				"display_name" : "Organisation",
				"type"         : "text",
				"description"  : "Your IoT Foundation organisation.",
                "required" : true
			},
			{
				"name"        : "device_id",
				"display_name": "Device",
				"type"        : "text", 
				"description" : "The device id to read data from.\nIf left empty data will be read for all devices in your organisation.",
				"required"    : false
			},
            {
            	"name"        : "api_key",
            	"display_name": "API Key",
            	"description" : "An IoT Foundation API key for your organisation",
            	"type"        : "text",
            	"required"    : true
            },
            {
            	"name"        : "api_auth_token",
            	"display_name": "API Auth Token",
            	"description" : "The Auth Token to match the API key",
            	"type"        : "text",
            	"required"    : true
            }
		],
		// **newInstance(settings, newInstanceCallback, updateCallback)** (required) : A function that will be called when a new instance of this plugin is requested.
		// * **settings** : A javascript object with the initial settings set by the user. The names of the properties in the object will correspond to the setting names defined above.
		// * **newInstanceCallback** : A callback function that you'll call when the new instance of the plugin is ready. This function expects a single argument, which is the new instance of your plugin object.
		// * **updateCallback** : A callback function that you'll call if and when your datasource has an update for freeboard to recalculate. This function expects a single parameter which is a javascript object with the new, updated data. You should hold on to this reference and call it when needed.
		newInstance   : function(settings, newInstanceCallback, updateCallback)
		{
			newInstanceCallback(new iotfDatasourcePlugin(settings, updateCallback));
		}
	});


	// ### Datasource Implementation
	//
	// -------------------
	var iotfDatasourcePlugin = function(settings, updateCallback)
	{
		var self = this;
		var data = {};

		var currentSettings = settings;

		function onConnect() {
			console.log("Connected");
			var topic;
			if (currentSettings.device_id === undefined) {
				topic = 'iot-2/type/+/id/+/evt/+/fmt/json';
			} else {
				topic = 'iot-2/type/+/id/' + currentSettings.device_id + '/evt/+/fmt/json';
			}
			console.log(topic);
			client.subscribe(topic);
		};
		
		function onConnectionLost(responseObject) {
			if (responseObject.errorCode !== 0)
				console.log("onConnectionLost:"+responseObject.errorMessage);
		};

		function onMessageArrived(message) {
			var device = message.destinationName.split('/')[4];
			var msg = JSON.parse(message.payloadString);
			data[device] = msg;
			updateCallback(data);
		};

		// **onSettingsChanged(newSettings)** (required) : A public function we must implement that will be called when a user makes a change to the settings.
		self.onSettingsChanged = function(newSettings)
		{
			client.disconnect();
			data = {};
			currentSettings = newSettings;
			client.connect({onSuccess:onConnect,
							userName: currentSettings.api_key,
							password: currentSettings.api_auth_token,
							useSSL: true});
		}

		// **updateNow()** (required) : A public function we must implement that will be called when the user wants to manually refresh the datasource
		self.updateNow = function()
		{
			// Don't need to do anything here, can't pull an update from MQTT.
		}

		// **onDispose()** (required) : A public function we must implement that will be called when this instance of this plugin is no longer needed. Do anything you need to cleanup after yourself here.
		self.onDispose = function()
		{
			if (client.isConnected()) {
				client.disconnect();
			}
			client = {};
		}

		console.log((new Date().getTime()).toString());
		var client = new Paho.MQTT.Client(currentSettings.org_id + '.messaging.internetofthings.ibmcloud.com',
										8883, currentSettings.api_key + (new Date().getTime()).toString());
		client.onConnectionLost = onConnectionLost;
		client.onMessageArrived = onMessageArrived;
		client.connect({onSuccess:onConnect, 
						userName: currentSettings.api_key, 
						password: currentSettings.api_auth_token,
						useSSL: true});
	}
}());