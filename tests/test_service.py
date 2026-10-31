import json
import os
import sys
import tempfile
import unittest

from unittest import mock

import cv2
import numpy as np

from berrynet.comm import payload
from berrynet.engine import DLEngine
from berrynet.service import ClassifierService
from berrynet.service import DetectorService
from berrynet.service import default_comm_config
from berrynet.service import parse_engine_service_args


class StubEngine(DLEngine):
    labels = ['???', 'dog']
    classes = 2

    def __init__(self, annotations):
        super(StubEngine, self).__init__()
        self.annotations = annotations

    def process_output(self, output):
        return {'annotations': self.annotations}


def image_payload():
    bgr_array = np.zeros((60, 80, 3), dtype=np.uint8)
    jpg_bytes = cv2.imencode('.jpg', bgr_array)[1].tobytes()
    return payload.serialize_jpg(jpg_bytes).encode('utf-8')


class TestEngineServices(unittest.TestCase):
    def run_service(self, service_class, annotations, draw):
        service = service_class('stub', StubEngine(annotations),
                                default_comm_config(), draw=draw)
        with mock.patch.object(service.comm, 'send') as send:
            service.inference(image_payload())
        topic, message = send.call_args.args
        return topic, payload.deserialize_payload(message)

    def test_classifier_service(self):
        annotations = [{'type': 'classification', 'label': 'dog',
                        'confidence': 0.9}]
        for draw in (False, True):
            topic, result = self.run_service(ClassifierService, annotations,
                                             draw)
            self.assertEqual(topic, 'berrynet/engine/stub/result')
            self.assertEqual(result['annotations'], annotations)
            jpg_bytes = payload.destringify_jpg(result['bytes'])
            self.assertEqual(payload.jpg2bgr(jpg_bytes).shape, (60, 80, 3))

    def test_detector_service(self):
        annotations = [{'label': 'dog', 'confidence': 0.9, 'left': 10,
                        'top': 10, 'right': 40, 'bottom': 50}]
        for draw in (False, True):
            topic, result = self.run_service(DetectorService, annotations,
                                             draw)
            self.assertEqual(topic, 'berrynet/engine/stub/result')
            self.assertEqual(result['annotations'], annotations)
            jpg_bytes = payload.destringify_jpg(result['bytes'])
            self.assertEqual(payload.jpg2bgr(jpg_bytes).shape, (60, 80, 3))


class TestEngineServiceArgs(unittest.TestCase):
    def parse(self, *argv):
        with mock.patch.object(sys, 'argv', ['bn_litert'] + list(argv)):
            return parse_engine_service_args('litert',
                                             ['classifier', 'detector'])

    def test_model_package(self):
        with tempfile.TemporaryDirectory() as basedir:
            os.mkdir(os.path.join(basedir, 'package'))
            with open(os.path.join(basedir, 'package', 'meta.json'), 'w') as f:
                json.dump({'model': 'model.tflite', 'label': 'labels.txt',
                           'config': {}}, f)
            with mock.patch.dict(os.environ, {'BERRYNET_MODEL_DIR': basedir}):
                args = self.parse('--service', 'detector',
                                  '--model_package', 'package')
        self.assertEqual(args['service_name'], 'litertdetector')
        self.assertEqual(args['model'],
                         os.path.join(basedir, 'package', 'model.tflite'))
        self.assertEqual(args['label'],
                         os.path.join(basedir, 'package', 'labels.txt'))

    def test_model_files(self):
        args = self.parse('--service_name', 'cam1', '-m', 'model.tflite',
                          '-l', 'labels.txt')
        self.assertEqual(args['service'], 'classifier')
        self.assertEqual(args['service_name'], 'cam1')
        self.assertEqual(args['model'], 'model.tflite')

    def test_model_is_required(self):
        with mock.patch('sys.stderr'):
            with self.assertRaises(SystemExit):
                self.parse('-m', 'model.tflite')

    def test_labels_in_model(self):
        argv = ['bn_litert', '--service', 'yolo', '-m', 'yolo26n.tflite']
        with mock.patch.object(sys, 'argv', argv):
            args = parse_engine_service_args('litert', ['detector', 'yolo'],
                                             labels_in_model=['yolo'])
        self.assertEqual(args['service_name'], 'litertyolo')
        self.assertIsNone(args['label'])
        argv = ['bn_litert', '--service', 'yolo']
        with mock.patch.object(sys, 'argv', argv), mock.patch('sys.stderr'):
            with self.assertRaises(SystemExit):
                parse_engine_service_args('litert', ['detector', 'yolo'],
                                          labels_in_model=['yolo'])
