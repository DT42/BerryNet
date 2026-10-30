import io
import json
import unittest
import urllib.error

from datetime import datetime
from datetime import timedelta
from unittest import mock

from berrynet.client import soil_monitor
from berrynet.client.soil_monitor import SensorState
from berrynet.client.soil_monitor import SoilMonitorService
from berrynet.client.soil_monitor import TelegramClient
from berrynet.client.soil_monitor import TelegramError


def report(**kwargs):
    return json.dumps(kwargs).encode('utf-8')


class TestParseSensorReport(unittest.TestCase):
    def test_thirdreality_report(self):
        reading = soil_monitor.parse_sensor_report(report(
            soil_moisture=42.5, temperature=23.1, battery=100,
            linkquality=120, voltage=3000))
        self.assertEqual(reading, {
            'soil_moisture': 42.5,
            'temperature': 23.1,
            'battery': 100,
            'linkquality': 120,
        })

    def test_humidity_fallback(self):
        reading = soil_monitor.parse_sensor_report(report(humidity=55))
        self.assertEqual(reading['soil_moisture'], 55)
        self.assertIsNone(reading['battery'])

    def test_invalid_payload(self):
        self.assertIsNone(soil_monitor.parse_sensor_report(b'online'))
        self.assertIsNone(soil_monitor.parse_sensor_report(b'[1, 2]'))
        self.assertIsNone(soil_monitor.parse_sensor_report(b'\xff'))

    def test_non_numeric_values(self):
        reading = soil_monitor.parse_sensor_report(report(
            soil_moisture='wet', battery=True))
        self.assertIsNone(reading['soil_moisture'])
        self.assertIsNone(reading['battery'])


class TestSensorState(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 30, 8, 0)
        self.sensor = SensorState('soil_1', 'Tomato', dry_threshold=30,
                                  wet_threshold=80, hysteresis=5,
                                  low_battery=20)

    def moisture(self, value):
        return self.sensor.update({'soil_moisture': value}, self.now)

    def test_first_normal_reading_is_silent(self):
        self.assertEqual(self.moisture(50), [])
        self.assertEqual(self.sensor.level, 'ok')

    def test_dry_alert_with_hysteresis(self):
        self.assertEqual(self.moisture(29), ['dry'])
        self.assertEqual(self.moisture(25), [])
        # Still dry until moisture reaches threshold + hysteresis.
        self.assertEqual(self.moisture(33), [])
        self.assertEqual(self.sensor.level, 'dry')
        self.assertEqual(self.moisture(35), ['recovered'])
        self.assertEqual(self.moisture(31), [])
        self.assertEqual(self.moisture(30), ['dry'])

    def test_wet_alert_with_hysteresis(self):
        self.assertEqual(self.moisture(85), ['wet'])
        self.assertEqual(self.moisture(76), [])
        self.assertEqual(self.moisture(75), ['recovered'])

    def test_dry_to_wet(self):
        self.assertEqual(self.moisture(20), ['dry'])
        self.assertEqual(self.moisture(90), ['wet'])

    def test_wet_threshold_disabled(self):
        self.sensor.wet_threshold = None
        self.assertEqual(self.moisture(100), [])

    def test_low_battery_alert_once(self):
        self.assertEqual(self.sensor.update({'battery': 20}, self.now),
                         ['low_battery'])
        self.assertEqual(self.sensor.update({'battery': 18}, self.now), [])
        self.assertEqual(self.sensor.update({'battery': 24}, self.now), [])
        self.assertTrue(self.sensor.battery_low)
        # New battery
        self.assertEqual(self.sensor.update({'battery': 100}, self.now), [])
        self.assertFalse(self.sensor.battery_low)
        self.assertEqual(self.sensor.update({'battery': 15}, self.now),
                         ['low_battery'])

    def test_keep_previous_values(self):
        self.sensor.update({'soil_moisture': 50, 'battery': 90}, self.now)
        self.sensor.update({'soil_moisture': 48, 'battery': None}, self.now)
        self.assertEqual(self.sensor.reading,
                         {'soil_moisture': 48, 'battery': 90})

    def test_offline_and_online(self):
        started = self.now
        self.assertIsNone(self.sensor.check_offline(
            started + timedelta(minutes=59), 3600, started))
        self.assertEqual(self.sensor.check_offline(
            started + timedelta(minutes=61), 3600, started), 61)
        # Alert only once
        self.assertIsNone(self.sensor.check_offline(
            started + timedelta(minutes=120), 3600, started))
        self.assertEqual(self.moisture(50), ['online'])
        self.assertIsNone(self.sensor.check_offline(
            self.now + timedelta(minutes=30), 3600, started))

    def test_offline_disabled(self):
        self.assertIsNone(self.sensor.check_offline(
            self.now + timedelta(days=10), 0, self.now))


class FakeTelegram(object):
    def __init__(self):
        self.sent = []

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


class TestSoilMonitorService(unittest.TestCase):
    def setUp(self):
        self.comm_config = {
            'subscribe': {},
            'broker': {'address': 'localhost', 'port': 1883},
            'z2m_base_topic': 'zigbee2mqtt',
        }
        self.sensors = [
            SensorState('soil_1', 'Tomato', dry_threshold=30,
                        low_battery=20),
            SensorState('garden/soil_2', dry_threshold=20, low_battery=20),
        ]
        self.telegram = FakeTelegram()
        self.service = SoilMonitorService(
            self.comm_config, self.sensors, telegram=self.telegram,
            chat_ids=[111], publish_topic='berrynet/data/soilmoisture',
            report_times=['08:00'], offline_timeout=3600)
        self.service.comm = mock.Mock()

    def outbox(self):
        messages = []
        while not self.service.outbox.empty():
            messages.append(self.service.outbox.get())
        return messages

    def test_subscribe_sensor_topics(self):
        self.assertEqual(
            sorted(self.comm_config['subscribe']),
            ['zigbee2mqtt/garden/soil_2', 'zigbee2mqtt/soil_1'])

    def test_dry_alert_and_publish(self):
        handler = self.comm_config['subscribe']['zigbee2mqtt/soil_1']
        handler(report(soil_moisture=25.0, temperature=21.5, battery=80))

        messages = self.outbox()
        self.assertEqual(len(messages), 1)
        chat_id, text = messages[0]
        self.assertEqual(chat_id, 111)
        self.assertIn('Tomato is too dry: soil moisture 25%', text)
        self.assertIn('threshold 30%', text)

        topic, published = self.service.comm.send.call_args[0]
        self.assertEqual(topic, 'berrynet/data/soilmoisture')
        result = json.loads(published)
        self.assertEqual(result['sensor'], 'soil_1')
        self.assertEqual(result['label'], 'Tomato')
        self.assertEqual(result['status'], 'dry')
        self.assertEqual(result['soil_moisture'], 25.0)
        self.assertEqual(result['battery'], 80)
        self.assertFalse(result['battery_low'])

    def test_normal_reading_is_silent(self):
        self.service.update('soil_1', report(soil_moisture=50))
        self.assertEqual(self.outbox(), [])
        self.assertTrue(self.service.comm.send.called)

    def test_publish_disabled(self):
        self.service.publish_topic = ''
        self.service.update('soil_1', report(soil_moisture=50))
        self.assertFalse(self.service.comm.send.called)

    def test_notify_every_reading(self):
        self.service.notify_every_reading = True
        self.service.update('soil_1', report(soil_moisture=50, battery=90))
        (_, text), = self.outbox()
        self.assertIn('Tomato', text)
        self.assertIn('50%', text)
        self.assertIn('90%', text)

    def test_bad_payload_does_not_raise(self):
        self.service.update('soil_1', b'not json')
        self.service.comm.send.side_effect = RuntimeError('broker down')
        self.service.update('soil_1', report(soil_moisture=50))

    def test_status(self):
        self.service.update('soil_1', report(
            soil_moisture=25, temperature=21.5, battery=15))
        text = self.service.render_status(datetime(2026, 10, 30, 9, 0))
        lines = text.split('\n')
        self.assertIn('2026-10-30 09:00', lines[0])
        self.assertIn('Tomato', lines[1])
        self.assertIn('25%', lines[1])
        self.assertIn('21.5', lines[1])
        self.assertIn('too dry', lines[1])
        self.assertIn('low battery', lines[1])
        self.assertIn('garden/soil_2: no data yet', lines[2])

    def test_scheduled_report_once_per_day(self):
        self.service.offline_timeout = 0
        self.service.tick(datetime(2026, 10, 30, 7, 59, 50))
        self.assertEqual(self.outbox(), [])
        self.service.tick(datetime(2026, 10, 30, 8, 0, 10))
        self.service.tick(datetime(2026, 10, 30, 8, 0, 30))
        self.assertEqual(len(self.outbox()), 1)
        self.service.tick(datetime(2026, 10, 31, 8, 0, 5))
        self.assertEqual(len(self.outbox()), 1)

    def test_offline_alert(self):
        started = self.service.started_at
        self.service.tick(started + timedelta(minutes=61))
        texts = [text for _, text in self.outbox()]
        self.assertEqual(len(texts), 2)
        self.assertIn('Tomato has not reported for 61 minutes', texts[0])

    def test_commands(self):
        def command(text, chat_id=111):
            self.service.handle_update({'update_id': 1, 'message': {
                'chat': {'id': chat_id}, 'text': text}})
            return self.outbox()

        (chat_id, text), = command('/help')
        self.assertIn('Your chat id: 111', text)
        (_, text), = command('/status@MyBot')
        self.assertIn('Soil moisture report', text)
        (chat_id, text), = command('/status', chat_id=222)
        self.assertEqual(chat_id, 222)
        self.assertIn('not allowed', text)
        self.assertEqual(command('hello'), [])

    def test_deliver_retry(self):
        self.service.stop_event.wait = mock.Mock()
        self.telegram.send_message = mock.Mock(side_effect=[
            TelegramError('Too Many Requests', 429, 3), None])
        self.assertTrue(self.service.deliver(111, 'hi'))
        self.service.stop_event.wait.assert_called_once_with(3)

    def test_deliver_no_retry_on_client_error(self):
        self.telegram.send_message = mock.Mock(
            side_effect=TelegramError('Bad Request: chat not found', 400))
        self.assertFalse(self.service.deliver(111, 'hi'))
        self.assertEqual(self.telegram.send_message.call_count, 1)

    def test_without_telegram(self):
        service = SoilMonitorService(
            dict(self.comm_config, subscribe={}), self.sensors)
        service.notify('hello')
        self.assertTrue(service.outbox.empty())

    def test_zh_tw(self):
        self.service.messages = soil_monitor.MESSAGES['zh_TW']
        self.service.update('soil_1', report(soil_moisture=10))
        (_, text), = self.outbox()
        self.assertIn('Tomato 土壤太乾：濕度 10%', text)


class TestTelegramClient(unittest.TestCase):
    def setUp(self):
        self.client = TelegramClient('123:abc', 'http://bot.api/')

    def response(self, body):
        resp = mock.MagicMock()
        resp.__enter__.return_value.read.return_value = json.dumps(
            body).encode('utf-8')
        return resp

    @mock.patch('urllib.request.urlopen')
    def test_send_message(self, urlopen):
        urlopen.return_value = self.response(
            {'ok': True, 'result': {'message_id': 1}})
        result = self.client.send_message(111, 'x' * 5000)
        self.assertEqual(result, {'message_id': 1})
        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url,
                         'http://bot.api/bot123:abc/sendMessage')
        body = json.loads(request.data.decode('utf-8'))
        self.assertEqual(body['chat_id'], 111)
        self.assertEqual(len(body['text']), 4096)

    @mock.patch('urllib.request.urlopen')
    def test_api_error(self, urlopen):
        body = json.dumps({
            'ok': False, 'error_code': 429,
            'description': 'Too Many Requests: retry after 7',
            'parameters': {'retry_after': 7}}).encode('utf-8')
        urlopen.side_effect = urllib.error.HTTPError(
            'url', 429, 'Too Many Requests', {}, io.BytesIO(body))
        with self.assertRaises(TelegramError) as ctx:
            self.client.send_message(111, 'hi')
        self.assertEqual(ctx.exception.error_code, 429)
        self.assertEqual(ctx.exception.retry_after, 7)
        self.assertTrue(ctx.exception.retryable)

    @mock.patch('urllib.request.urlopen')
    def test_network_error(self, urlopen):
        urlopen.side_effect = urllib.error.URLError('timed out')
        with self.assertRaises(TelegramError) as ctx:
            self.client.get_me()
        self.assertIsNone(ctx.exception.error_code)
        self.assertTrue(ctx.exception.retryable)
        self.assertNotIn('123:abc', str(ctx.exception))


class TestSettings(unittest.TestCase):
    def args(self, **kwargs):
        args = {key: None for key in soil_monitor.DEFAULT_SETTINGS}
        args.update({'config': None, 'debug': False})
        args.update(kwargs)
        return args

    def test_cli_overrides_config(self):
        config = {
            'token': '123:abc',
            'chat_ids': ['111', '@channel'],
            'dry_threshold': 25,
            'report_times': ['8:00'],
            'sensors': ['soil_1'],
        }
        with mock.patch('builtins.open',
                        mock.mock_open(read_data=json.dumps(config))):
            settings = soil_monitor.load_settings(
                self.args(config='soil.json', dry_threshold=35.0))
        self.assertEqual(settings['token'], '123:abc')
        self.assertEqual(settings['chat_ids'], [111, '@channel'])
        self.assertEqual(settings['dry_threshold'], 35.0)
        self.assertEqual(settings['report_times'], ['08:00'])
        self.assertEqual(settings['broker_port'], 1883)

    def test_token_from_env(self):
        with mock.patch.dict('os.environ',
                             {'BERRYNET_TELEGRAM_TOKEN': '9:xyz'}):
            settings = soil_monitor.load_settings(self.args())
        self.assertEqual(settings['token'], '9:xyz')

    def test_invalid_settings(self):
        with self.assertRaises(ValueError):
            soil_monitor.load_settings(self.args(report_times=['25:00']))
        with self.assertRaises(ValueError):
            soil_monitor.load_settings(self.args(language='xx'))

    def test_create_sensors(self):
        settings = dict(soil_monitor.DEFAULT_SETTINGS, sensors=[
            'soil_1',
            {'name': 'soil_2', 'label': 'Monstera', 'dry_threshold': 20,
             'wet_threshold': 70},
        ])
        sensor_1, sensor_2 = soil_monitor.create_sensors(settings)
        self.assertEqual(sensor_1.label, 'soil_1')
        self.assertEqual(sensor_1.dry_threshold, 30)
        self.assertIsNone(sensor_1.wet_threshold)
        self.assertEqual(sensor_2.label, 'Monstera')
        self.assertEqual(sensor_2.dry_threshold, 20)
        self.assertEqual(sensor_2.wet_threshold, 70)

    def test_create_sensors_errors(self):
        with self.assertRaises(ValueError):
            soil_monitor.create_sensors(dict(soil_monitor.DEFAULT_SETTINGS))
        with self.assertRaises(ValueError):
            soil_monitor.create_sensors(dict(
                soil_monitor.DEFAULT_SETTINGS,
                sensors=[{'name': 's', 'dry_threshold': 50,
                          'wet_threshold': 40}]))


if __name__ == '__main__':
    unittest.main()
