import importlib.util
import os
import tempfile
import unittest

import cv2
import numpy as np

from berrynet.dlmodelmgr import DLModelManager
from berrynet.engine import detection_annotations
from berrynet.engine import load_labels
from tests import data

# LiteRT and ONNX Runtime do not publish wheels for every supported
# Python version.
HAS_LITERT = importlib.util.find_spec('ai_edge_litert') is not None
HAS_ONNX = importlib.util.find_spec('onnxruntime') is not None


def model_meta(testcase, name):
    dlmm = DLModelManager()
    if name not in dlmm.get_model_names():
        testcase.skipTest(
            '{} is not installed, run "python -m tests.data"'.format(name))
    return dlmm.get_model_meta(name)


def read_image(testcase, path):
    if not os.path.isfile(path):
        testcase.skipTest(
            '{} does not exist, run "python -m tests.data"'.format(path))
    return cv2.imread(path)


def run_engine(engine, bgr_array):
    engine.create()
    output = engine.inference(engine.process_input(bgr_array))
    return engine.process_output(output)['annotations']


class TestEngineHelpers(unittest.TestCase):
    def test_load_labels(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt') as f:
            f.write('n01440764 tench, Tinca tinca\n'
                    'n04592741 wing\n'
                    'traffic light\n')
            f.flush()
            self.assertEqual(load_labels(f.name),
                             ['tench', 'wing', 'traffic light'])

    def test_detection_annotations(self):
        boxes = np.array([[0.1, 0.2, 0.5, 0.6],
                          [0.0, 0.0, 1.0, 1.0],
                          [0.2, 0.2, 0.4, 0.4]])
        annotations = detection_annotations(
            boxes, np.array([0, 1, 1]), np.array([0.9, 0.3, 0.8]), 2,
            ['???', 'person', 'bicycle'], 0.5, 200, 100, label_offset=1)
        # The second box is below threshold, and the third one is beyond
        # the number of detections.
        self.assertEqual(annotations, [{
            'label': 'person',
            'confidence': 0.9,
            'left': 40,
            'top': 10,
            'right': 120,
            'bottom': 50
        }])


@unittest.skipUnless(HAS_LITERT, 'LiteRT is not installed')
class TestLiteRTEngines(unittest.TestCase):
    def test_classifier(self):
        from berrynet.engine.litert_engine import LiteRTClassifierEngine

        meta = model_meta(self, 'mobilenet-v1-imagenet-litert')
        engine = LiteRTClassifierEngine(meta['model'], meta['label'])
        annotations = run_engine(engine,
                                 read_image(self, data.GRASSHOPPER_JPG))
        self.assertEqual(len(annotations), 3)
        # The quantized MobileNet v1 ranks cricket (0.66) above
        # grasshopper (0.34).
        self.assertEqual({a['label'] for a in annotations[:2]},
                         {'cricket', 'grasshopper'})
        self.assertGreater(annotations[0]['confidence'] +
                           annotations[1]['confidence'], 0.9)

    def test_detector(self):
        from berrynet.engine.litert_engine import LiteRTDetectorEngine

        meta = model_meta(self, 'ssd-mobilenet-v1-coco-litert')
        engine = LiteRTDetectorEngine(meta['model'], meta['label'])
        annotations = run_engine(engine,
                                 read_image(self, data.dog_jpg_path()))
        self.assertLessEqual({'bicycle', 'car', 'dog'},
                             {a['label'] for a in annotations})

    def test_yolov4_postprocess(self):
        from berrynet.engine.litert_engine import LiteRTYoloV4DetectorEngine

        engine = LiteRTYoloV4DetectorEngine.__new__(LiteRTYoloV4DetectorEngine)
        engine.input_h = engine.input_w = 400
        engine.threshold = 0.25
        engine.iou_threshold = 0.45
        engine.max_detections = 50
        box_xywh = np.array([[[100, 100, 40, 40],
                              [102, 101, 40, 40],
                              [101, 100, 40, 40],
                              [300, 200, 20, 40],
                              [200, 200, 10, 10],
                              [10, 390, 40, 40]]], dtype=np.float32)
        scores = np.array([[[0.9, 0.1],
                            [0.8, 0.1],    # overlaps with box 0
                            [0.1, 0.6],    # overlaps, but another class
                            [0.1, 0.7],
                            [0.2, 0.1],    # below threshold
                            [0.5, 0.1]]],  # beyond the image edges
                          dtype=np.float32)
        boxes, classes, confidences = engine.postprocess(box_xywh, scores)
        np.testing.assert_allclose(confidences, [0.9, 0.7, 0.6, 0.5])
        np.testing.assert_array_equal(classes, [0, 1, 1, 0])
        np.testing.assert_allclose(boxes, [[0.2, 0.2, 0.3, 0.3],
                                           [0.45, 0.725, 0.55, 0.775],
                                           [0.2, 0.2025, 0.3, 0.3025],
                                           [0.925, 0.0, 1.0, 0.075]])


@unittest.skipUnless(HAS_ONNX, 'ONNX Runtime is not installed')
class TestONNXEngines(unittest.TestCase):
    def test_classifier(self):
        from berrynet.engine.onnx_engine import ONNXClassifierEngine

        meta = model_meta(self, 'mobilenet-v2-imagenet-onnx')
        engine = ONNXClassifierEngine(meta['model'], meta['label'])
        annotations = run_engine(engine,
                                 read_image(self, data.GRASSHOPPER_JPG))
        self.assertEqual(len(annotations), 3)
        self.assertEqual(annotations[0]['label'], 'grasshopper')
        self.assertGreater(annotations[0]['confidence'], 0.5)

    def test_detector(self):
        from berrynet.engine.onnx_engine import ONNXDetectorEngine

        meta = model_meta(self, 'ssd-mobilenet-v1-coco-onnx')
        engine = ONNXDetectorEngine(meta['model'], meta['label'])
        annotations = run_engine(engine,
                                 read_image(self, data.dog_jpg_path()))
        self.assertLessEqual({'bicycle', 'car', 'dog'},
                             {a['label'] for a in annotations})
