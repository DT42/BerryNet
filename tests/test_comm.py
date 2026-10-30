import unittest
from unittest import mock

from berrynet.comm import Communicator


class TestCommunicator(unittest.TestCase):
    def setUp(self):
        self.handler = mock.Mock()
        self.comm = Communicator({
            'broker': {'address': 'localhost', 'port': 1883},
            'subscribe': {'foo': self.handler},
        })

    def test_on_connect_subscribes_topics(self):
        client = self.comm.client
        with mock.patch.object(client, 'subscribe') as subscribe:
            # paho-mqtt 1.x callback signature
            client.on_connect(client, None, {}, 0)
            # paho-mqtt 2.x CallbackAPIVersion.VERSION2 signature
            client.on_connect(client, None, {}, 0, None)
        subscribe.assert_has_calls([mock.call('foo'), mock.call('foo')])

    def test_on_message_dispatches_payload(self):
        client = self.comm.client
        msg = mock.Mock(topic='foo', payload=b'data')
        client.on_message(client, None, msg)
        self.handler.assert_called_once_with(b'data')
