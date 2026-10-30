import sys
import unittest

from unittest import mock

import cv2
import numpy as np

from berrynet.client import camera


def jpg(value):
    im = np.full((12, 16, 3), value, dtype=np.uint8)
    return cv2.imencode('.jpg', im)[1].tobytes()


class ChunkedStdout(object):
    """Pipe returning a few bytes per read, to split JPEG frames."""

    def __init__(self, data, chunk_size=7):
        self.data = data
        self.chunk_size = chunk_size

    def read1(self, size):
        chunk = self.data[:min(size, self.chunk_size)]
        self.data = self.data[len(chunk):]
        return chunk


class TestRpicamCapture(unittest.TestCase):
    def test_read_mjpeg_stream(self):
        stream = b'garbage' + jpg(50) + jpg(200)
        with mock.patch('subprocess.Popen') as popen:
            popen.return_value.stdout = ChunkedStdout(stream)
            capture = camera.open_capture('picamera')

        command = popen.call_args.args[0]
        self.assertEqual(command[0], 'rpicam-vid')
        self.assertIn('mjpeg', command)
        self.assertEqual(capture.get(cv2.CAP_PROP_FPS), 30)
        for value in (50, 200):
            self.assertTrue(capture.grab())
            status, im = capture.retrieve()
            self.assertTrue(status)
            self.assertEqual(im.shape, (12, 16, 3))
            self.assertAlmostEqual(float(im.mean()), value, delta=2)
        self.assertFalse(capture.grab())
        self.assertEqual(capture.retrieve(), (False, None))

        capture.release()
        popen.return_value.terminate.assert_called_once_with()


class TestOpenCapture(unittest.TestCase):
    def test_video_capture_sources(self):
        with mock.patch('cv2.VideoCapture') as video_capture:
            camera.open_capture('0')
            camera.open_capture('rtsp://camera/stream')
        self.assertEqual(video_capture.call_args_list,
                         [mock.call(0), mock.call('rtsp://camera/stream')])


class Stop(Exception):
    pass


class FakeCapture(object):
    def __init__(self, retrieve_results, max_grabs=100):
        self.retrieve_results = retrieve_results
        self.grabs = 0
        self.max_grabs = max_grabs

    def get(self, prop):
        return 30

    def grab(self):
        self.grabs += 1
        if self.grabs > self.max_grabs:
            raise Stop()
        return True

    def retrieve(self):
        return self.retrieve_results.pop(0)

    def release(self):
        pass


class TestCameraStream(unittest.TestCase):
    def test_send_every_interval_and_recover(self):
        im = np.zeros((12, 16, 3), dtype=np.uint8)
        capture = FakeCapture([(True, im), (False, None), (True, im),
                               (True, im)])
        sent = []

        def send(topic, mqtt_payload):
            sent.append(topic)
            if len(sent) == 3:
                raise Stop()

        argv = ['bn_camera', '--fps', '10']
        with mock.patch.object(sys, 'argv', argv), \
                mock.patch.object(camera, 'Communicator') as communicator, \
                mock.patch.object(camera, 'open_capture',
                                  return_value=capture) as open_capture, \
                mock.patch('time.sleep'):
            communicator.return_value.send.side_effect = send
            with self.assertRaises(Stop):
                camera.main()

        # 30 FPS camera and 10 FPS output: send every third frame, and
        # reopen the camera once after the failed frame.
        self.assertEqual(sent, ['berrynet/data/rgbimage'] * 3)
        self.assertEqual(capture.grabs, 12)
        self.assertEqual(open_capture.call_count, 2)
