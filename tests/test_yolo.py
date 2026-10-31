import importlib
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile

import numpy as np

from berrynet.engine import letterbox
from berrynet.engine import tflite_ultralytics_labels
from berrynet.engine import ultralytics_labels
from berrynet.engine import yolo_annotations
from berrynet.engine import yolo_detections

HAS_LITERT = importlib.util.find_spec('ai_edge_litert') is not None
HAS_ONNX = importlib.util.find_spec('onnxruntime') is not None


def end2end_output(rows):
    """YOLO26 output: (1, 300, 6) of [x1, y1, x2, y2, score, class]."""
    output = np.zeros((1, 300, 6), dtype=np.float32)
    output[0, :len(rows)] = rows
    return output


class TestYoloHelpers(unittest.TestCase):
    def test_letterbox(self):
        bgr_array = np.zeros((100, 200, 3), dtype=np.uint8)
        bgr_array[:, :, 0] = 255  # blue
        rgb, scale, pad = letterbox(bgr_array, 640, 640)
        self.assertEqual(rgb.shape, (640, 640, 3))
        self.assertEqual(scale, 3.2)
        self.assertEqual(pad, (0, 160))
        np.testing.assert_array_equal(rgb[0, 0], [114, 114, 114])
        np.testing.assert_array_equal(rgb[320, 320], [0, 0, 255])
        np.testing.assert_array_equal(rgb[639, 639], [114, 114, 114])

    def test_end2end_output(self):
        output = end2end_output([[10, 20, 110, 220, 0.6, 16],
                                 [300, 300, 400, 400, 0.9, 1],
                                 [0, 0, 50, 50, 0.2, 0]])  # below threshold
        boxes, classes, scores = yolo_detections(output, 640, 640, 0.25, 0.7)
        np.testing.assert_allclose(scores, [0.9, 0.6])
        np.testing.assert_array_equal(classes, [1, 16])
        np.testing.assert_allclose(boxes, [[300, 300, 400, 400],
                                           [10, 20, 110, 220]])

    def test_dequantized_end2end_classes(self):
        output = end2end_output([[10, 20, 110, 220, 0.6, 15.98]])
        boxes, classes, scores = yolo_detections(output, 640, 640, 0.25, 0.7)
        np.testing.assert_array_equal(classes, [16])

    def test_normalized_end2end_output(self):
        output = end2end_output([[0.1, 0.2, 0.5, 0.6, 0.8, 2]])
        boxes, classes, scores = yolo_detections(output, 320, 640, 0.25, 0.7)
        np.testing.assert_allclose(boxes, [[64, 64, 320, 192]], rtol=1e-5)

    def test_raw_output(self):
        # YOLO11 and YOLOv8 output: (1, 4 + classes, anchors) of
        # [x, y, w, h, scores of each class].
        anchors = np.array([[100, 100, 40, 40, 0.9, 0.1, 0.0],
                            [102, 101, 40, 40, 0.8, 0.1, 0.0],  # overlaps
                            [101, 100, 40, 40, 0.1, 0.6, 0.0],  # other class
                            [300, 200, 20, 40, 0.1, 0.0, 0.7],
                            [200, 200, 10, 10, 0.2, 0.1, 0.1]],  # low score
                           dtype=np.float32)
        output = anchors.T[np.newaxis]
        boxes, classes, scores = yolo_detections(output, 640, 640, 0.25, 0.7)
        np.testing.assert_allclose(scores, [0.9, 0.7, 0.6])
        np.testing.assert_array_equal(classes, [0, 2, 1])
        np.testing.assert_allclose(boxes, [[80, 80, 120, 120],
                                           [290, 180, 310, 220],
                                           [81, 80, 121, 120]])

    def test_annotations_in_original_image(self):
        # A 200x100 image letterboxed into 640x640, see test_letterbox.
        boxes = np.array([[64, 192, 320, 352], [-10, 100, 700, 600]],
                         dtype=np.float32)
        annotations = yolo_annotations(boxes, np.array([1, 0]),
                                       np.array([0.9, 0.5]),
                                       ['person', 'bicycle'], 3.2, (0, 160),
                                       200, 100)
        self.assertEqual(annotations, [
            {'label': 'bicycle', 'confidence': 0.9,
             'left': 20, 'top': 10, 'right': 100, 'bottom': 60},
            # Clipped to the image
            {'label': 'person', 'confidence': 0.5,
             'left': 0, 'top': 0, 'right': 200, 'bottom': 100},
        ])

    def test_ultralytics_labels(self):
        self.assertEqual(ultralytics_labels("{0: 'person', 1: 'bicycle'}"),
                         ['person', 'bicycle'])
        names = {str(i): 'class{}'.format(i) for i in range(12)}
        self.assertEqual(ultralytics_labels(names)[10], 'class10')
        # Labels stay at their class indexes.
        self.assertEqual(ultralytics_labels({0: 'cat', 2: 'dog'}),
                         ['cat', '1', 'dog'])

    def test_tflite_ultralytics_labels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model = os.path.join(tmpdir, 'yolo.tflite')
            with open(model, 'wb') as f:
                f.write(b'\x1c\x00\x00\x00TFL3 model data')
            with zipfile.ZipFile(model, 'a') as archive:
                archive.writestr('metadata.json', json.dumps(
                    {'names': {'0': 'person', '1': 'bicycle'}}))
            self.assertEqual(tflite_ultralytics_labels(model),
                             ['person', 'bicycle'])

    def test_tflite_without_ultralytics_labels(self):
        with tempfile.NamedTemporaryFile(suffix='.tflite') as f:
            f.write(b'\x1c\x00\x00\x00TFL3 model data')
            f.flush()
            with self.assertRaisesRegex(ValueError, 'give a label file'):
                tflite_ultralytics_labels(f.name)


@unittest.skipUnless(HAS_LITERT, 'LiteRT is not installed')
class TestLiteRTYoloDetectorEngine(unittest.TestCase):
    def engine(self, input_shape, dtype=np.float32, quantization=(0.0, 0)):
        from berrynet.engine.litert_engine import LiteRTYoloDetectorEngine

        engine = LiteRTYoloDetectorEngine.__new__(LiteRTYoloDetectorEngine)
        engine.input_details = [{'shape': np.array(input_shape),
                                 'dtype': dtype,
                                 'quantization': quantization}]
        engine.nchw = input_shape[1] == 3
        engine.input_h, engine.input_w = (input_shape[2:4] if engine.nchw
                                          else input_shape[1:3])
        engine.labels = ['person', 'bicycle']
        engine.threshold = 0.25
        engine.iou_threshold = 0.7
        return engine

    def test_process_input(self):
        bgr_array = np.full((100, 200, 3), 255, dtype=np.uint8)
        nchw = self.engine([1, 3, 640, 640]).process_input(bgr_array)
        self.assertEqual(nchw.shape, (1, 3, 640, 640))
        self.assertEqual(nchw.dtype, np.float32)
        self.assertAlmostEqual(float(nchw[0, 0, 320, 320]), 1.0)
        nhwc = self.engine([1, 320, 320, 3]).process_input(bgr_array)
        self.assertEqual(nhwc.shape, (1, 320, 320, 3))
        quantized = self.engine([1, 3, 64, 64], np.int8,
                                (1 / 255, -128)).process_input(bgr_array)
        self.assertEqual(quantized.dtype, np.int8)
        self.assertEqual(int(quantized[0, 0, 32, 32]), 127)
        # Integer input without quantization takes pixel values.
        pixels = self.engine([1, 3, 64, 64], np.uint8).process_input(bgr_array)
        self.assertEqual(int(pixels[0, 0, 32, 32]), 255)

    def test_process_output(self):
        engine = self.engine([1, 3, 640, 640])
        engine.process_input(np.zeros((100, 200, 3), dtype=np.uint8))
        output = end2end_output([[64, 192, 320, 352, 0.9, 1]])
        self.assertEqual(engine.process_output({'output': output}), {
            'annotations': [{'label': 'bicycle',
                             'confidence': float(np.float32(0.9)),
                             'left': 20, 'top': 10, 'right': 100,
                             'bottom': 60}]
        })


@unittest.skipUnless(HAS_ONNX, 'ONNX Runtime is not installed')
class TestONNXYoloDetectorEngine(unittest.TestCase):
    def test_process_input_and_output(self):
        from berrynet.engine.onnx_engine import ONNXYoloDetectorEngine

        engine = ONNXYoloDetectorEngine.__new__(ONNXYoloDetectorEngine)
        engine.input_h = engine.input_w = 640
        engine.input_dtype = np.float32
        engine.labels = ['person', 'bicycle']
        engine.threshold = 0.25
        engine.iou_threshold = 0.7
        tensor = engine.process_input(np.zeros((100, 200, 3), dtype=np.uint8))
        self.assertEqual(tensor.shape, (1, 3, 640, 640))
        self.assertEqual(tensor.dtype, np.float32)
        # Models exported with half precision
        engine.input_dtype = np.float16
        tensor = engine.process_input(np.zeros((100, 200, 3), dtype=np.uint8))
        self.assertEqual(tensor.dtype, np.float16)
        output = end2end_output([[64, 192, 320, 352, 0.9, 1]])
        self.assertEqual(engine.process_output({'output': output}), {
            'annotations': [{'label': 'bicycle',
                             'confidence': float(np.float32(0.9)),
                             'left': 20, 'top': 10, 'right': 100,
                             'bottom': 60}]
        })


# Directory of yolo26n.onnx and yolo26n.tflite exported by Ultralytics, e.g.
#     $ yolo export model=yolo26n.pt format=onnx nms=False
#     $ yolo export model=yolo26n.pt format=litert nms=False
YOLO_MODEL_DIR = os.environ.get('BERRYNET_TEST_YOLO_MODELS', '')


@unittest.skipUnless(YOLO_MODEL_DIR, 'BERRYNET_TEST_YOLO_MODELS is not set')
class TestYoloModels(unittest.TestCase):
    def check_engine(self, module, engine_name, filename, runtime):
        from tests import data

        if not runtime:
            self.skipTest('Runtime of {} is not installed'.format(filename))
        if not os.path.isfile(data.dog_jpg_path()):
            self.skipTest('dog.jpg does not exist, run "python -m tests.data"')
        import cv2

        engine_class = getattr(importlib.import_module(module), engine_name)
        engine = engine_class(os.path.join(YOLO_MODEL_DIR, filename))
        bgr_array = cv2.imread(data.dog_jpg_path())
        output = engine.inference(engine.process_input(bgr_array))
        annotations = engine.process_output(output)['annotations']
        self.assertLessEqual({'bicycle', 'dog', 'truck'},
                             {a['label'] for a in annotations})

    def test_litert(self):
        self.check_engine('berrynet.engine.litert_engine',
                          'LiteRTYoloDetectorEngine', 'yolo26n.tflite',
                          HAS_LITERT)

    def test_onnx(self):
        self.check_engine('berrynet.engine.onnx_engine',
                          'ONNXYoloDetectorEngine', 'yolo26n.onnx', HAS_ONNX)
