# Soil Moisture Monitor: Zigbee Sensors to Telegram

`bn_soil_monitor` is a BerryNet client that watches Zigbee soil moisture
sensors and sends the monitoring results to Telegram:

* Alerts when soil is too dry or too wet, and when it recovers
* Low battery and offline (no report) alerts
* Scheduled status reports, e.g. every day at 08:00 and 20:00
* `/status` bot command to check current readings at any time
* Normalized readings are published to BerryNet MQTT topic
  `berrynet/data/soilmoisture`, so other BerryNet components (e.g. Freeboard
  dashboard) can use them

Target hardware:

* Zigbee coordinator: SONOFF ZBDongle-P (Zigbee 3.0 USB Dongle Plus, TI CC2652P)
* Sensor: THIRDREALITY Smart Soil Moisture Sensor Gen2
  ([Zigbee2MQTT model 3RSM0147Z](https://www.zigbee2mqtt.io/devices/3RSM0147Z.html))

## Architecture

```
THIRDREALITY soil sensor x3
        |  Zigbee
        v
SONOFF ZBDongle-P --USB--> Zigbee2MQTT
                               |  MQTT zigbee2mqtt/<sensor>
                               v
                     Mosquitto (BerryNet broker)
                               |
                               v
                        bn_soil_monitor ---> Telegram bot ---> you
                               |
                               |  MQTT berrynet/data/soilmoisture
                               v
               other BerryNet components (dashboard, ...)
```

[Zigbee2MQTT](https://www.zigbee2mqtt.io/) talks to the dongle and sensors,
and publishes every sensor report as JSON to the MQTT broker that BerryNet
already uses. `bn_soil_monitor` only needs MQTT, so it can run on the same
device or anywhere that can reach the broker.

## 1. Install Zigbee2MQTT

1. Plug in the ZBDongle-P and find its serial port:

    ```
    $ ls -l /dev/serial/by-id/
    usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_<id>-if00-port0 -> ../../ttyUSB0
    ```

2. Install Zigbee2MQTT by following the
   [official guide](https://www.zigbee2mqtt.io/guide/installation/).
   Mosquitto is installed by BerryNet `./configure` already.

3. Use [config/zigbee2mqtt/configuration.yaml](../config/zigbee2mqtt/configuration.yaml)
   as the Zigbee2MQTT configuration, and replace the serial port with
   yours. The ZBDongle-P must use `adapter: zstack`.

4. Start Zigbee2MQTT. Its frontend is at `http://<device-ip>:8081`
   (port 8080 is used by BerryNet dashboard).

## 2. Pair the Soil Moisture Sensors

1. Click "Permit join (All)" in Zigbee2MQTT frontend.
2. Put each sensor into pairing mode according to its manual. Zigbee2MQTT
   should recognize it as `3RSM0147Z` by Third Reality.
3. Rename the sensors, e.g. `soil_sensor_1`, `soil_sensor_2` and
   `soil_sensor_3`. The friendly name is the MQTT topic
   `bn_soil_monitor` subscribes to.
4. Check the readings:

    ```
    $ mosquitto_sub -v -t 'zigbee2mqtt/soil_sensor_1'
    zigbee2mqtt/soil_sensor_1 {"battery":100,"linkquality":148,"soil_moisture":42.5,"temperature":23.1}
    ```

The sensor is a sleepy end device and reports only when values change or
periodically, so it may take a while to see a message.

Keep the Zigbee2MQTT `retain` device option disabled. The broker delivers a
retained message again whenever `bn_soil_monitor` (re)connects, and an old
reading would be treated as a new report, e.g. an offline sensor would look
back online.

## 3. Create a Telegram Bot

1. Talk to [@BotFather](https://t.me/BotFather) in Telegram, send `/newbot`
   and get the bot token.
2. Use a bot dedicated to `bn_soil_monitor`. If the token is shared with
   `bn_telegram`, only one of them can receive commands (Telegram replies
   409 Conflict); run `bn_soil_monitor` with `--no-commands` in that case.

## 4. Run bn_soil_monitor

`bn_soil_monitor` is installed by BerryNet `./configure` like the other
`bn_*` commands (into `/opt/berrynet/venv`, linked to `/usr/local/bin`).
It only depends on `paho-mqtt` and `logzero`; in a development environment
created by `uv sync`, run it with `uv run bn_soil_monitor`.

1. Copy the example config and fill in the bot token and sensor names. The
   file contains the bot token, so make it readable by root only:

    ```
    $ sudo mkdir -p /etc/berrynet
    $ sudo cp config/soil-monitor.json /etc/berrynet/soil-monitor.json
    $ sudo chmod 600 /etc/berrynet/soil-monitor.json
    ```

2. Run it in the foreground once:

    ```
    $ sudo bn_soil_monitor --config /etc/berrynet/soil-monitor.json --debug
    ```

3. Send `/start` to your bot in Telegram. The bot replies with your chat id;
   add it to `chat_ids` in the config and restart `bn_soil_monitor`. To
   notify a group, add the bot to the group and send `/start` there (group
   chat ids are negative numbers).

4. Run it with supervisor like other BerryNet components:

    ```
    $ sudo cp config/supervisor/conf.d/berrynet-soil-monitor.conf /etc/supervisor/conf.d/
    $ sudo supervisorctl reread
    $ sudo supervisorctl update
    $ sudo supervisorctl tail soil-monitor stderr
    ```

All settings can also be given by CLI, e.g.

```
$ bn_soil_monitor --token <token> --chat-id 123456789 \
    --sensor soil_sensor_1 soil_sensor_2 soil_sensor_3 \
    --dry-threshold 30 --report-time 08:00 20:00 --language zh_TW
```

The token can also be set by environment variable `BERRYNET_TELEGRAM_TOKEN`,
which overrides the config file. Options taking multiple values can be
repeated, e.g. `--chat-id 111 --chat-id 222`.
Without a token, notifications are only written to the log, which is useful
to verify the Zigbee side first.

## Telegram Messages

| Event | Example (`en`) | Example (`zh_TW`) |
| --- | --- | --- |
| Too dry | 🏜️ Balcony tomato is too dry: soil moisture 28.4% (threshold 30%). Time to water! | 🏜️ 陽台番茄 土壤太乾：濕度 28.4%（門檻 30%），該澆水了！ |
| Too wet | 💦 Balcony tomato is too wet: soil moisture 88% (threshold 85%). | 💦 陽台番茄 土壤太濕：濕度 88%（門檻 85%） |
| Recovered | ✅ Balcony tomato is back to normal: soil moisture 36%. | ✅ 陽台番茄 已恢復正常：濕度 36% |
| Low battery | 🪫 Monstera battery is low: 15%. | 🪫 龜背芋 電量偏低：15% |
| Offline | 📴 Monstera has not reported for 721 minutes. | 📴 龜背芋 已超過 721 分鐘沒有回報 |

Scheduled reports and `/status` look like:

```
📋 Soil moisture report 2026-10-30 08:00
🟢 Balcony tomato: 💧36% 🌡️22°C 🔋100% (07:52)
🟠 Monstera: 💧18% 🌡️21°C 🔋15% ⚠️ too dry, low battery (07:40)
⚪ Succulents: no data yet
```

Bot commands:

* `/status`: current readings of all sensors, only for chats in `chat_ids`
* `/help` or `/start`: command list and the chat id

## Settings

Settings are read from the JSON config (`--config`); CLI arguments override
them.

| Config key | CLI | Default | Description |
| --- | --- | --- | --- |
| `token` | `--token` | | Telegram bot token, or path of a JSON file with `token`. `BERRYNET_TELEGRAM_TOKEN` overrides the config file |
| `chat_ids` | `--chat-id` | `[]` | Chats receiving notifications and allowed to use `/status` |
| `language` | `--language` | `en` | `en` or `zh_TW` |
| `sensors` | `--sensor` | `[]` | Zigbee2MQTT friendly names, or objects with `name`, `label`, `dry_threshold`, `wet_threshold` |
| `dry_threshold` | `--dry-threshold` | `30` | Too dry alert if moisture (%) is at or below it, `null` disables it |
| `wet_threshold` | `--wet-threshold` | `null` | Too wet alert if moisture (%) is at or above it, `null` disables it |
| `hysteresis` | `--hysteresis` | `5` | Moisture (%) has to pass a threshold by this value to recover, preventing repeated alerts |
| `low_battery` | `--low-battery` | `20` | Low battery alert threshold (%) |
| `report_times` | `--report-time` | `[]` | Local times (HH:MM) to send a status report |
| `offline_timeout` | `--offline-timeout` | `720` | Offline alert after these minutes without report, `0` disables it |
| `notify_every_reading` | `--notify-every-reading` | `false` | Send every reading to Telegram |
| `commands` | `--no-commands` | `true` | Answer Telegram bot commands |
| `broker_ip` | `--broker-ip` | `localhost` | MQTT broker IP |
| `broker_port` | `--broker-port` | `1883` | MQTT broker port |
| `z2m_base_topic` | `--z2m-base-topic` | `zigbee2mqtt` | Zigbee2MQTT base topic |
| `publish_topic` | `--publish-topic` | `berrynet/data/soilmoisture` | BerryNet topic of normalized readings, empty string disables it |
| `telegram_api_url` | `--telegram-api-url` | `https://api.telegram.org` | Telegram Bot API server |

Moisture is read from `soil_moisture` reported by Zigbee2MQTT. Older
Zigbee2MQTT versions report this sensor as `humidity`, which is supported
as well. If the readings are off, Zigbee2MQTT device options
`soil_moisture_calibration` and `soil_moisture_precision` can adjust them.

## BerryNet MQTT Output

Every sensor report is published to `berrynet/data/soilmoisture`:

```json
{
    "timestamp": "2026-10-30T08:00:12.345678",
    "sensor": "soil_sensor_1",
    "label": "Balcony tomato",
    "status": "dry",
    "battery_low": false,
    "soil_moisture": 28.4,
    "temperature": 22.1,
    "battery": 100,
    "linkquality": 150
}
```

`status` is one of `unknown`, `ok`, `dry` or `wet`. Freeboard can display
these values with an MQTT datasource subscribing to the topic.
