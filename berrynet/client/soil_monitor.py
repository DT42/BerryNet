#!/usr/bin/env python3
#
# Copyright 2026 DT42
#
# This file is part of BerryNet.
#
# BerryNet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BerryNet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BerryNet.  If not, see <http://www.gnu.org/licenses/>.

"""Soil moisture monitor client.

Watches Zigbee soil moisture sensors (e.g. THIRDREALITY Smart Soil Moisture
Sensor Gen2) paired through Zigbee2MQTT and a Zigbee coordinator (e.g.
SONOFF ZBDongle-P), and sends the monitoring results to Telegram.

    soil sensor --Zigbee--> ZBDongle-P --> Zigbee2MQTT
        --MQTT zigbee2mqtt/<sensor>--> bn_soil_monitor
            --> Telegram: alerts, scheduled reports, /status command
            --> MQTT berrynet/data/soilmoisture: other BerryNet components

Telegram is accessed via the Bot HTTP API directly, so this client does not
depend on a specific python-telegram-bot version.
"""

import argparse
import functools
import http.client
import json
import logging
import os
import queue
import threading
import urllib.error
import urllib.request

from datetime import datetime

from berrynet import logger
from berrynet.comm import Communicator


DEFAULT_SETTINGS = {
    'token': None,
    'chat_ids': [],
    'language': 'en',
    'broker_ip': 'localhost',
    'broker_port': 1883,
    'z2m_base_topic': 'zigbee2mqtt',
    'publish_topic': 'berrynet/data/soilmoisture',
    'sensors': [],
    'dry_threshold': 30,
    'wet_threshold': None,
    'hysteresis': 5,
    'low_battery': 20,
    'report_times': [],
    'offline_timeout': 720,
    'notify_every_reading': False,
    'commands': True,
    'telegram_api_url': 'https://api.telegram.org',
}

# Zigbee2MQTT exposes the THIRDREALITY sensor value as soil_moisture.
# Older converters and some other sensors report it as humidity.
MOISTURE_KEYS = ('soil_moisture', 'moisture', 'humidity')

# Battery has to rise this much above the low battery threshold before
# another low battery alert can be sent, e.g. after replacing the battery.
BATTERY_HYSTERESIS = 5

TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_SEND_ATTEMPTS = 3
TELEGRAM_POLL_TIMEOUT = 30
TICK_INTERVAL = 20

STATE_ICONS = {
    'unknown': '⚪',  # white circle
    'ok': '\U0001f7e2',   # green circle
    'dry': '\U0001f7e0',  # orange circle
    'wet': '\U0001f535',  # blue circle
}

MESSAGES = {
    'en': {
        'startup': '\U0001f331 BerryNet soil monitor started, watching {count} sensor(s): {names}',
        'dry': '\U0001f3dc️ {label} is too dry: soil moisture {moisture}% (threshold {threshold}%). Time to water!',
        'wet': '\U0001f4a6 {label} is too wet: soil moisture {moisture}% (threshold {threshold}%).',
        'recovered': '✅ {label} is back to normal: soil moisture {moisture}%.',
        'low_battery': '\U0001faab {label} battery is low: {battery}%.',
        'offline': '\U0001f4f4 {label} has not reported for {minutes} minutes.',
        'online': '\U0001f4f6 {label} is back online.',
        'reading': '\U0001f331 {label}: {details}',
        'report_title': '\U0001f4cb Soil moisture report {time}',
        'no_data': 'no data yet',
        'state_ok': 'normal',
        'state_dry': 'too dry',
        'state_wet': 'too wet',
        'state_offline': 'offline',
        'state_low_battery': 'low battery',
        'help': ('BerryNet soil monitor commands:\n'
                 '/status - Current readings of all sensors\n'
                 '/help - Show this message\n\n'
                 'Your chat id: {chat_id}'),
        'unauthorized': ('This chat (id {chat_id}) is not allowed to read '
                         'sensor data. Add the id to chat_ids of '
                         'bn_soil_monitor.'),
    },
    'zh_TW': {
        'startup': '\U0001f331 BerryNet 土壤監測已啟動，監測 {count} 個感測器：{names}',
        'dry': '\U0001f3dc️ {label} 土壤太乾：濕度 {moisture}%（門檻 {threshold}%），該澆水了！',
        'wet': '\U0001f4a6 {label} 土壤太濕：濕度 {moisture}%（門檻 {threshold}%）',
        'recovered': '✅ {label} 已恢復正常：濕度 {moisture}%',
        'low_battery': '\U0001faab {label} 電量偏低：{battery}%',
        'offline': '\U0001f4f4 {label} 已超過 {minutes} 分鐘沒有回報',
        'online': '\U0001f4f6 {label} 已恢復連線',
        'reading': '\U0001f331 {label}：{details}',
        'report_title': '\U0001f4cb 土壤濕度報告 {time}',
        'no_data': '尚無資料',
        'state_ok': '正常',
        'state_dry': '太乾',
        'state_wet': '太濕',
        'state_offline': '離線',
        'state_low_battery': '電量低',
        'help': ('BerryNet 土壤監測指令：\n'
                 '/status - 查看所有感測器目前數值\n'
                 '/help - 顯示說明\n\n'
                 '你的 chat id：{chat_id}'),
        'unauthorized': ('此聊天室（id {chat_id}）未被授權讀取感測資料，'
                         '請將此 id 加入 bn_soil_monitor 的 chat_ids。'),
    },
}


def format_number(value):
    """Format a reading with at most one decimal digit, e.g. 45.0 -> 45."""
    return '{:.1f}'.format(value).rstrip('0').rstrip('.')


def split_message(text, limit=TELEGRAM_MAX_MESSAGE_LENGTH):
    """Split text by lines into messages within Telegram length limit.

    Telegram counts the length in UTF-16 code units, where an emoji
    usually takes two. A single line longer than the limit is cut.
    """
    def utf16(s):
        return s.encode('utf-16-le')

    messages = []
    message = ''
    for line in text.split('\n'):
        # Cutting may split a surrogate pair, which is dropped by 'ignore'.
        line = utf16(line)[:limit * 2].decode('utf-16-le', 'ignore')
        candidate = message + '\n' + line if message else line
        if len(utf16(candidate)) > limit * 2:
            messages.append(message)
            candidate = line
        message = candidate
    messages.append(message)
    return messages


def parse_sensor_report(pl):
    """Parse a Zigbee2MQTT device message into a normalized reading.

    Args:
        pl: MQTT payload (bytes or str) published by Zigbee2MQTT to
            <base_topic>/<friendly_name>.

    Returns:
        A dict with soil_moisture, temperature, battery and linkquality
        (missing values are None), or None if the payload is not a device
        state JSON object.
    """
    try:
        if isinstance(pl, bytes):
            pl = pl.decode('utf-8')
        report = json.loads(pl)
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(report, dict):
        return None

    def number(key):
        value = report.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return value

    moisture = None
    for key in MOISTURE_KEYS:
        moisture = number(key)
        if moisture is not None:
            break
    return {
        'soil_moisture': moisture,
        'temperature': number('temperature'),
        'battery': number('battery'),
        'linkquality': number('linkquality'),
    }


class SensorState(object):
    """Latest reading and alert state of one soil moisture sensor."""

    def __init__(self, name, label=None, dry_threshold=None,
                 wet_threshold=None, hysteresis=5, low_battery=None):
        self.name = name
        self.label = label or name
        self.dry_threshold = dry_threshold
        self.wet_threshold = wet_threshold
        self.hysteresis = hysteresis
        self.low_battery = low_battery

        self.reading = {}
        self.level = 'unknown'
        self.battery_low = False
        self.offline = False
        self.last_seen = None

    def evaluate_level(self, moisture):
        """Classify moisture as ok, dry or wet.

        Hysteresis keeps a dry (wet) sensor in its state until moisture
        rises above (falls below) the threshold by the hysteresis value,
        so a reading oscillating around a threshold does not flood the
        chat with alerts.
        """
        dry = self.dry_threshold
        wet = self.wet_threshold
        if dry is not None and moisture <= dry:
            return 'dry'
        if wet is not None and moisture >= wet:
            return 'wet'
        if (self.level == 'dry' and dry is not None and
                moisture < dry + self.hysteresis):
            return 'dry'
        if (self.level == 'wet' and wet is not None and
                moisture > wet - self.hysteresis):
            return 'wet'
        return 'ok'

    def update(self, reading, now):
        """Store a new reading and return the events it triggers.

        Returns:
            List of event names: dry, wet, recovered, low_battery, online.
        """
        events = []
        self.last_seen = now
        if self.offline:
            self.offline = False
            events.append('online')

        self.reading.update(
            {k: v for k, v in reading.items() if v is not None})

        moisture = reading.get('soil_moisture')
        if moisture is not None:
            previous = self.level
            self.level = self.evaluate_level(moisture)
            if self.level != previous:
                if self.level in ('dry', 'wet'):
                    events.append(self.level)
                elif previous in ('dry', 'wet'):
                    events.append('recovered')

        battery = reading.get('battery')
        if battery is not None and self.low_battery is not None:
            if battery <= self.low_battery:
                if not self.battery_low:
                    self.battery_low = True
                    events.append('low_battery')
            elif battery > self.low_battery + BATTERY_HYSTERESIS:
                self.battery_low = False
        return events

    def check_offline(self, now, timeout, since):
        """Mark the sensor offline if it has been silent for too long.

        Args:
            now: Current datetime.
            timeout: Silence period in seconds, 0 disables the check.
            since: Fallback reference time if the sensor never reported.

        Returns:
            Silent minutes if the sensor just went offline, otherwise None.
        """
        if not timeout or self.offline:
            return None
        reference = self.last_seen or since
        silent = (now - reference).total_seconds()
        if silent > timeout:
            self.offline = True
            return int(silent // 60)
        return None


class TelegramError(Exception):
    def __init__(self, description, error_code=None, retry_after=None):
        super(TelegramError, self).__init__(description)
        self.description = description
        self.error_code = error_code
        self.retry_after = retry_after

    @property
    def retryable(self):
        # Network errors have no error code.
        return (self.error_code is None or self.error_code == 429 or
                self.error_code >= 500)


class TelegramClient(object):
    """Minimal Telegram Bot API client based on urllib."""

    def __init__(self, token, api_url='https://api.telegram.org', timeout=10):
        self.token = token
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout

    def call(self, method, params=None, timeout=None):
        # Do not log the URL, it contains the bot token.
        url = '{}/bot{}/{}'.format(self.api_url, self.token, method)
        request = urllib.request.Request(
            url,
            data=json.dumps(params or {}).encode('utf-8'),
            headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(
                    request, timeout=timeout or self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as e:
            # Bot API returns error details as JSON in the body.
            body = e.read()
        except (OSError, http.client.HTTPException) as e:
            raise TelegramError('Network error: {}'.format(e))

        try:
            result = json.loads(body.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            result = None
        if not isinstance(result, dict):
            raise TelegramError('Invalid response from Telegram')
        if not result.get('ok'):
            raise TelegramError(
                result.get('description', 'Unknown error'),
                result.get('error_code'),
                result.get('parameters', {}).get('retry_after'))
        return result.get('result')

    def get_me(self):
        return self.call('getMe')

    def send_message(self, chat_id, text):
        return self.call('sendMessage', {
            'chat_id': chat_id,
            'text': text,
            'disable_web_page_preview': True,
        })

    def get_updates(self, offset=None, timeout=TELEGRAM_POLL_TIMEOUT):
        params = {'timeout': timeout, 'allowed_updates': ['message']}
        if offset is not None:
            params['offset'] = offset
        return self.call('getUpdates', params, timeout=timeout + 10)


class SoilMonitorService(object):
    def __init__(self, comm_config, sensors, telegram=None, chat_ids=(),
                 language='en', publish_topic='', report_times=(),
                 offline_timeout=0, notify_every_reading=False,
                 enable_commands=True):
        """
        Args:
            comm_config: Communicator config, sensor topics are added to
                its subscribe dict.
            sensors: List of SensorState.
            telegram: TelegramClient, or None to log notifications only.
            chat_ids: Telegram chats receiving notifications and allowed
                to query /status.
            language: Key of MESSAGES.
            publish_topic: BerryNet topic for normalized readings, empty
                string disables publishing.
            report_times: List of HH:MM local times to send a report.
            offline_timeout: Offline alert after this many seconds without
                report, 0 disables it.
            notify_every_reading: Send every reading to Telegram.
            enable_commands: Answer Telegram bot commands.
        """
        self.comm_config = comm_config
        base_topic = comm_config['z2m_base_topic']
        self.sensors = {}
        for sensor in sensors:
            self.sensors[sensor.name] = sensor
            topic = '{}/{}'.format(base_topic, sensor.name)
            self.comm_config['subscribe'][topic] = functools.partial(
                self.update, sensor.name)
        self.comm = Communicator(self.comm_config, debug=True)

        self.telegram = telegram
        self.chat_ids = list(chat_ids)
        self.messages = MESSAGES[language]
        self.publish_topic = publish_topic
        self.report_times = set(report_times)
        self.offline_timeout = offline_timeout
        self.notify_every_reading = notify_every_reading
        self.enable_commands = enable_commands

        self.lock = threading.Lock()
        self.outbox = queue.Queue()
        self.stop_event = threading.Event()
        self.started_at = datetime.now()
        self.last_report_key = None
        self.bot_username = None

    def msg(self, key, **kwargs):
        return self.messages[key].format(**kwargs)

    def update(self, sensor_name, pl):
        """Handle a Zigbee2MQTT report of a sensor."""
        # An exception raised here would stop the MQTT network loop.
        try:
            self._update(sensor_name, pl)
        except Exception as e:
            logger.exception('Failed to handle report of {}: {}'.format(
                sensor_name, e))

    def _update(self, sensor_name, pl):
        reading = parse_sensor_report(pl)
        if reading is None:
            logger.debug('Ignore non-JSON message of {}'.format(sensor_name))
            return
        logger.debug('{} reading: {}'.format(sensor_name, reading))

        now = datetime.now()
        with self.lock:
            sensor = self.sensors[sensor_name]
            events = sensor.update(reading, now)
            result = self.generalize(sensor, now)
            details = self.format_details(sensor)

        for event in events:
            logger.info('{} event: {}'.format(sensor_name, event))
            self.notify(self.render_event(sensor, event))
        if self.notify_every_reading:
            self.notify(self.msg('reading', label=sensor.label,
                                 details=details))
        if self.publish_topic:
            # Publish by the connected client instead of Communicator.send,
            # which opens a new connection and blocks the network loop
            # running this callback.
            info = self.comm.client.publish(self.publish_topic,
                                            json.dumps(result))
            if info.rc:
                logger.warning('Failed to publish to {}, error code {}'.format(
                    self.publish_topic, info.rc))

    def generalize(self, sensor, now):
        """Create the payload published to BerryNet."""
        result = {
            'timestamp': now.isoformat(),
            'sensor': sensor.name,
            'label': sensor.label,
            'status': sensor.level,
            'battery_low': sensor.battery_low,
        }
        for key in ('soil_moisture', 'temperature', 'battery',
                    'linkquality'):
            result[key] = sensor.reading.get(key)
        return result

    def render_event(self, sensor, event):
        moisture = sensor.reading.get('soil_moisture')
        battery = sensor.reading.get('battery')
        threshold = (sensor.dry_threshold if event == 'dry'
                     else sensor.wet_threshold)
        return self.msg(
            event,
            label=sensor.label,
            moisture=format_number(moisture) if moisture is not None else '',
            battery=format_number(battery) if battery is not None else '',
            threshold=(format_number(threshold)
                       if threshold is not None else ''))

    def format_details(self, sensor):
        reading = sensor.reading
        if sensor.last_seen is None:
            return self.msg('no_data')

        parts = []
        if reading.get('soil_moisture') is not None:
            parts.append('\U0001f4a7{}%'.format(
                format_number(reading['soil_moisture'])))
        if reading.get('temperature') is not None:
            parts.append('\U0001f321️{}°C'.format(
                format_number(reading['temperature'])))
        if reading.get('battery') is not None:
            parts.append('\U0001f50b{}%'.format(
                format_number(reading['battery'])))
        details = ' '.join(parts)

        notes = []
        if sensor.level in ('dry', 'wet'):
            notes.append(self.msg('state_' + sensor.level))
        if sensor.battery_low:
            notes.append(self.msg('state_low_battery'))
        if sensor.offline:
            notes.append(self.msg('state_offline'))
        if notes:
            details += ' ⚠️ ' + ', '.join(notes)
        return '{} ({})'.format(details, sensor.last_seen.strftime('%H:%M'))

    def render_status(self, now):
        lines = [self.msg('report_title',
                          time=now.strftime('%Y-%m-%d %H:%M'))]
        with self.lock:
            for sensor in self.sensors.values():
                lines.append('{} {}: {}'.format(
                    STATE_ICONS[sensor.level],
                    sensor.label,
                    self.format_details(sensor)))
        return '\n'.join(lines)

    def notify(self, text):
        """Queue a message for all chats."""
        if self.telegram is None or not self.chat_ids:
            logger.info('Notification (not sent): {}'.format(text))
            return
        for chat_id in self.chat_ids:
            self.reply(chat_id, text)

    def reply(self, chat_id, text):
        """Queue a message for a chat."""
        for message in split_message(text):
            self.outbox.put((chat_id, message))

    def deliver(self, chat_id, text):
        """Send a message, retrying on network and rate limit errors."""
        for attempt in range(TELEGRAM_SEND_ATTEMPTS):
            try:
                self.telegram.send_message(chat_id, text)
                logger.debug('Sent message to {}'.format(chat_id))
                return True
            except TelegramError as e:
                logger.warning('Failed to send message to {}: {}'.format(
                    chat_id, e))
                if not e.retryable or attempt == TELEGRAM_SEND_ATTEMPTS - 1:
                    break
                self.stop_event.wait(e.retry_after or 2 ** (attempt + 1))
        logger.error('Drop message to {}: {}'.format(chat_id, text))
        return False

    def _send_loop(self):
        while not self.stop_event.is_set():
            try:
                chat_id, text = self.outbox.get(timeout=1)
            except queue.Empty:
                continue
            try:
                self.deliver(chat_id, text)
            except Exception as e:
                logger.exception('Failed to deliver message: {}'.format(e))

    def handle_update(self, update):
        """Answer a Telegram bot command."""
        message = update.get('message') or {}
        text = message.get('text', '')
        if not text.startswith('/'):
            return
        chat_id = message['chat']['id']
        # Commands in group chats may look like /status@MyBot.
        command, _, bot = text.split()[0].partition('@')
        command = command.lower()
        if bot and self.bot_username and \
                bot.lower() != self.bot_username.lower():
            logger.debug('Ignore command {} for @{}'.format(command, bot))
            return
        logger.info('Received command {} from chat id {}'.format(
            command, chat_id))

        if command in ('/start', '/help'):
            self.reply(chat_id, self.msg('help', chat_id=chat_id))
        elif command == '/status':
            if chat_id in self.chat_ids:
                self.reply(chat_id, self.render_status(datetime.now()))
            else:
                self.reply(chat_id, self.msg('unauthorized', chat_id=chat_id))

    def _poll_loop(self):
        offset = None
        while not self.stop_event.is_set():
            try:
                updates = self.telegram.get_updates(offset)
            except TelegramError as e:
                if e.error_code == 409:
                    logger.warning(
                        'Another program is polling updates with the same '
                        'bot token (e.g. bn_telegram). Use another bot or '
                        'run with --no-commands. ({})'.format(e))
                    self.stop_event.wait(30)
                else:
                    logger.warning('Failed to get updates: {}'.format(e))
                    self.stop_event.wait(e.retry_after or 5)
                continue
            except Exception as e:
                logger.exception('Failed to get updates: {}'.format(e))
                self.stop_event.wait(5)
                continue
            for update in updates:
                offset = update['update_id'] + 1
                try:
                    self.handle_update(update)
                except Exception as e:
                    logger.exception('Failed to handle update: {}'.format(e))

    def tick(self, now):
        """Run periodic jobs: offline check and scheduled reports."""
        with self.lock:
            offline = []
            for sensor in self.sensors.values():
                minutes = sensor.check_offline(
                    now, self.offline_timeout, self.started_at)
                if minutes is not None:
                    offline.append((sensor, minutes))
        for sensor, minutes in offline:
            logger.info('{} event: offline'.format(sensor.name))
            self.notify(self.msg('offline', label=sensor.label,
                                 minutes=minutes))

        hhmm = now.strftime('%H:%M')
        report_key = now.strftime('%Y-%m-%d ') + hhmm
        if hhmm in self.report_times and report_key != self.last_report_key:
            self.last_report_key = report_key
            self.notify(self.render_status(now))

    def start(self):
        self.comm.start_nb()
        if self.telegram is not None:
            try:
                bot = self.telegram.get_me()
                self.bot_username = bot.get('username')
                logger.info('Connected to Telegram bot @{}'.format(
                    self.bot_username))
            except TelegramError as e:
                logger.warning('Failed to verify Telegram bot: {}'.format(e))
            threading.Thread(target=self._send_loop, daemon=True).start()
            if self.enable_commands:
                threading.Thread(target=self._poll_loop, daemon=True).start()
        else:
            logger.warning('Telegram token is not set, '
                           'notifications are only logged.')
        if self.telegram is not None and not self.chat_ids:
            logger.warning('No chat id is set. Send /start to the bot to '
                           'get the chat id, then add it to chat_ids.')
        self.notify(self.msg(
            'startup',
            count=len(self.sensors),
            names=', '.join(s.label for s in self.sensors.values())))

    def stop(self):
        self.stop_event.set()
        while True:
            try:
                chat_id, text = self.outbox.get_nowait()
            except queue.Empty:
                break
            logger.warning('Drop unsent message to {}: {}'.format(
                chat_id, text))
        self.comm.stop_nb()
        self.comm.disconnect()

    def run(self, args=None):
        """Infinite loop serving sensor reports"""
        self.start()
        try:
            while not self.stop_event.is_set():
                self.tick(datetime.now())
                self.stop_event.wait(TICK_INTERVAL)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def normalize_report_time(value):
    """Convert H:MM or HH:MM to HH:MM, raise ValueError if invalid."""
    try:
        return datetime.strptime(value.strip(), '%H:%M').strftime('%H:%M')
    except ValueError:
        raise ValueError(
            'Invalid report time {}, expect HH:MM'.format(value))


def normalize_chat_id(value):
    # Numeric ids may come as strings from CLI, but @channelusername is
    # also accepted by the Bot API.
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def load_token(token):
    """Accept a token, or a JSON file containing it like bn_telegram."""
    if token and os.path.isfile(token):
        with open(token) as f:
            return json.load(f)['token']
    return token


def load_settings(args):
    """Merge default settings, config file and CLI arguments.

    CLI arguments override the config file, which overrides defaults.
    The token is taken from CLI, environment variable
    BERRYNET_TELEGRAM_TOKEN, then the config file.
    """
    settings = dict(DEFAULT_SETTINGS)
    if args.get('config'):
        with open(args['config']) as f:
            file_settings = json.load(f)
        for key in sorted(set(file_settings) - set(DEFAULT_SETTINGS)):
            logger.warning('Unknown setting {} in {}'.format(
                key, args['config']))
        settings.update(file_settings)
    for key, value in args.items():
        if key in DEFAULT_SETTINGS and value is not None:
            settings[key] = value

    env_token = os.environ.get('BERRYNET_TELEGRAM_TOKEN')
    if env_token and not args.get('token'):
        settings['token'] = env_token
    settings['token'] = load_token(settings['token'])
    settings['chat_ids'] = [normalize_chat_id(c)
                            for c in settings['chat_ids']]
    settings['report_times'] = [normalize_report_time(t)
                                for t in settings['report_times']]
    if settings['language'] not in MESSAGES:
        raise ValueError('Unsupported language {}, choose from {}'.format(
            settings['language'], ', '.join(sorted(MESSAGES))))
    return settings


def create_sensors(settings):
    """Create SensorState from sensor names or sensor config dicts."""
    sensors = []
    for item in settings['sensors']:
        if isinstance(item, str):
            item = {'name': item}
        if not item.get('name'):
            raise ValueError('Sensor config without name: {}'.format(item))
        sensor = SensorState(
            item['name'],
            label=item.get('label'),
            dry_threshold=item.get('dry_threshold',
                                   settings['dry_threshold']),
            wet_threshold=item.get('wet_threshold',
                                   settings['wet_threshold']),
            hysteresis=settings['hysteresis'],
            low_battery=settings['low_battery'])
        if (sensor.dry_threshold is not None and
                sensor.wet_threshold is not None and
                sensor.dry_threshold >= sensor.wet_threshold):
            raise ValueError(
                'dry_threshold must be lower than wet_threshold '
                'for sensor {}'.format(sensor.name))
        sensors.append(sensor)
    if not sensors:
        raise ValueError(
            'No sensor is set. Use --sensor <Zigbee2MQTT friendly name> '
            'or "sensors" in the config file.')
    return sensors


def parse_args():
    ap = argparse.ArgumentParser(
        description=('Send soil moisture readings from Zigbee2MQTT '
                     'to Telegram.'))
    ap.add_argument(
        '--config',
        default=None,
        help='Path of the JSON config file. CLI arguments override it.'
    )
    ap.add_argument(
        '--token',
        default=None,
        help=('Telegram token got from BotFather, '
              'or filepath of a JSON config file with token. '
              'Environment variable BERRYNET_TELEGRAM_TOKEN also works.')
    )
    ap.add_argument(
        '--chat-id',
        dest='chat_ids',
        action='append',
        nargs='+',
        default=None,
        help=('Telegram chat id receiving notifications '
              'and allowed to use /status. Can be repeated.')
    )
    ap.add_argument(
        '--language',
        default=None,
        help='Notification language: {} (default: en)'.format(
            ', '.join(sorted(MESSAGES)))
    )
    ap.add_argument(
        '--sensor',
        dest='sensors',
        action='append',
        nargs='+',
        default=None,
        help=('Zigbee2MQTT friendly name of a soil moisture sensor. '
              'Can be repeated.')
    )
    ap.add_argument(
        '--broker-ip',
        default=None,
        help='MQTT broker IP. (default: localhost)'
    )
    ap.add_argument(
        '--broker-port',
        default=None,
        type=int,
        help='MQTT broker port. (default: 1883)'
    )
    ap.add_argument(
        '--z2m-base-topic',
        default=None,
        help='Zigbee2MQTT base topic. (default: zigbee2mqtt)'
    )
    ap.add_argument(
        '--publish-topic',
        default=None,
        help=('BerryNet topic to publish normalized readings, '
              'empty string disables it. '
              '(default: berrynet/data/soilmoisture)')
    )
    ap.add_argument(
        '--dry-threshold',
        default=None,
        type=float,
        help='Alert if soil moisture (%%) is at or below it. (default: 30)'
    )
    ap.add_argument(
        '--wet-threshold',
        default=None,
        type=float,
        help=('Alert if soil moisture (%%) is at or above it. '
              '(default: disabled)')
    )
    ap.add_argument(
        '--hysteresis',
        default=None,
        type=float,
        help=('Moisture (%%) has to pass a threshold by this value to '
              'recover from an alert. (default: 5)')
    )
    ap.add_argument(
        '--low-battery',
        default=None,
        type=float,
        help='Alert if battery (%%) is at or below it. (default: 20)'
    )
    ap.add_argument(
        '--report-time',
        dest='report_times',
        action='append',
        nargs='+',
        default=None,
        help='Send a status report at local time HH:MM, e.g. 08:00 20:00.'
    )
    ap.add_argument(
        '--offline-timeout',
        default=None,
        type=float,
        help=('Alert if a sensor has not reported for these minutes, '
              '0 disables it. (default: 720)')
    )
    ap.add_argument(
        '--notify-every-reading',
        action='store_true',
        default=None,
        help='Send every sensor reading to Telegram.'
    )
    ap.add_argument(
        '--no-commands',
        dest='commands',
        action='store_false',
        default=None,
        help=('Do not answer Telegram commands. Use it if the bot token '
              'is shared with another program polling updates.')
    )
    ap.add_argument(
        '--telegram-api-url',
        default=None,
        help='Telegram Bot API server. (default: https://api.telegram.org)'
    )
    ap.add_argument(
        '--debug',
        action='store_true',
        help='Debug mode toggle'
    )
    args = vars(ap.parse_args())
    # Flatten values of repeated options.
    for key in ('chat_ids', 'sensors', 'report_times'):
        if args[key] is not None:
            args[key] = [v for values in args[key] for v in values]
    return args


def main():
    args = parse_args()
    if args['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    try:
        settings = load_settings(args)
        sensors = create_sensors(settings)
        offline_timeout = settings['offline_timeout'] * 60
    except (OSError, KeyError, ValueError, TypeError, AttributeError) as e:
        # Wrong value types in the config file raise TypeError or
        # AttributeError.
        logger.critical(e)
        raise SystemExit(1)

    comm_config = {
        'subscribe': {},
        'broker': {
            'address': settings['broker_ip'],
            'port': settings['broker_port']
        },
        'z2m_base_topic': settings['z2m_base_topic']
    }
    if settings['token']:
        telegram = TelegramClient(settings['token'],
                                  settings['telegram_api_url'])
    else:
        telegram = None
    service = SoilMonitorService(
        comm_config,
        sensors,
        telegram=telegram,
        chat_ids=settings['chat_ids'],
        language=settings['language'],
        publish_topic=settings['publish_topic'],
        report_times=settings['report_times'],
        offline_timeout=offline_timeout,
        notify_every_reading=settings['notify_every_reading'],
        enable_commands=settings['commands'])
    service.run(args)


if __name__ == '__main__':
    main()
