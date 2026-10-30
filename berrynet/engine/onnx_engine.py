import logging
import time

from argparse import ArgumentParser

import cv2
import numpy as np
import onnxruntime as ort

from berrynet.engine import DLEngine
from berrynet.engine import classification_annotations
from berrynet.engine import detection_annotations
from berrynet.engine import load_labels
from berrynet import logger


def create_session(model, num_threads):
    options = ort.SessionOptions()
    options.intra_op_num_threads = num_threads
    return ort.InferenceSession(model,
                                sess_options=options,
                                providers=['CPUExecutionProvider'])


def softmax(x):
    e = np.exp(x - np.max(x))
    return e / e.sum()


class ONNXClassifierEngine(DLEngine):
    """Classifier with one float image input, NCHW or NHWC, and one score
    output, e.g. MobileNetV2 of the ONNX Model Zoo.
    """

    def __init__(self, model, labels, top_k=3, num_threads=1,
                 input_size=224,
                 input_mean=(0.485, 0.456, 0.406),
                 input_std=(0.229, 0.224, 0.225)):
        super(ONNXClassifierEngine, self).__init__()

        # Load labels
        self.labels = load_labels(labels)
        self.classes = len(self.labels)

        # Load ONNX model into memory
        self.session = create_session(model, num_threads)
        model_input = self.session.get_inputs()[0]
        self.input_name = model_input.name
        shape = model_input.shape
        self.channels_first = shape[1] == 3
        input_hw = shape[2:4] if self.channels_first else shape[1:3]
        # Dynamic dimensions are names instead of numbers.
        self.input_h, self.input_w = [d if isinstance(d, int) else input_size
                                      for d in input_hw]
        self.input_mean = np.array(input_mean, dtype=np.float32)
        self.input_std = np.array(input_std, dtype=np.float32)
        self.top_k = int(top_k)

    def process_input(self, tensor):
        """Resize and normalize image for network input"""

        self.img_w = tensor.shape[1]
        self.img_h = tensor.shape[0]

        frame = cv2.cvtColor(tensor, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (self.input_w, self.input_h))
        frame = (frame.astype(np.float32) / 255.0 - self.input_mean) \
            / self.input_std
        if self.channels_first:
            frame = frame.transpose(2, 0, 1)
        return np.expand_dims(frame, axis=0).astype(np.float32)

    def inference(self, tensor):
        scores = self.session.run(None, {self.input_name: tensor})[0]
        return {
            'scores': np.squeeze(scores),
        }

    def process_output(self, output):
        scores = output['scores']
        # Turn logits into probabilities.
        if scores.min() < 0 or not np.isclose(scores.sum(), 1.0, atol=1e-3):
            scores = softmax(scores)
        return {
            'annotations': classification_annotations(scores, self.labels,
                                                      self.top_k)
        }


class ONNXDetectorEngine(DLEngine):
    """SSD detector exported from the TensorFlow Object Detection API,
    e.g. SSD-MobileNetV1 of the ONNX Model Zoo.

    It takes an uint8 NHWC image and outputs detection_boxes,
    detection_classes (1-based label indexes), detection_scores and
    num_detections.
    """

    def __init__(self, model, labels, threshold=0.5, num_threads=1,
                 input_size=300):
        super(ONNXDetectorEngine, self).__init__()

        # Load labels
        self.labels = load_labels(labels)
        self.classes = len(self.labels)

        # Load ONNX model into memory
        self.session = create_session(model, num_threads)
        model_input = self.session.get_inputs()[0]
        self.input_name = model_input.name
        input_hw = model_input.shape[1:3]
        # The model resizes images itself, so dynamic dimensions accept
        # any size. Resize to the model's own input size to save time.
        self.input_h, self.input_w = [d if isinstance(d, int) else input_size
                                      for d in input_hw]
        self.output_names = [o.name for o in self.session.get_outputs()]
        self.threshold = threshold

    def process_input(self, tensor):
        """Resize image for network input"""

        self.img_w = tensor.shape[1]
        self.img_h = tensor.shape[0]

        frame = cv2.cvtColor(tensor, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (self.input_w, self.input_h))
        return np.expand_dims(frame, axis=0)

    def inference(self, tensor):
        outputs = self.session.run(None, {self.input_name: tensor})
        outputs = dict(zip(self.output_names, outputs))
        return {
            'boxes': outputs['detection_boxes'],
            'classes': outputs['detection_classes'],
            'scores': outputs['detection_scores'],
            'num': outputs['num_detections']
        }

    def process_output(self, output):
        annotations = detection_annotations(
            output['boxes'][0], output['classes'][0], output['scores'][0],
            output['num'][0], self.labels, self.threshold,
            self.img_w, self.img_h)
        return {'annotations': annotations}


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "-e", "--engine",
        help=("Classifier or Detector engine. "
              "classifier, or detector is acceptable. "
              "(classifier by default)"),
        default="classifier",
        choices=["classifier", "detector"],
        type=str)
    parser.add_argument(
        "-m", "--model",
        help="Path to an .onnx model file.",
        required=True,
        type=str)
    parser.add_argument(
        "-l", "--labels",
        help="Labels mapping file",
        default=None,
        type=str)
    parser.add_argument(
        "--top_k",
        help="Number of top results",
        default=3,
        type=int)
    parser.add_argument(
        "--num_threads",
        help="Number of threads",
        default=1,
        type=int)
    parser.add_argument(
        "-i", "--input",
        help="Path to an image file",
        required=True,
        type=str)
    parser.add_argument(
        "--debug",
        help="Debug mode toggle",
        default=False,
        action="store_true")

    return parser.parse_args()


def main():
    # Example command
    #     $ python3 -m berrynet.engine.onnx_engine -e detector \
    #           -m ssd_mobilenet_v1_12.onnx --labels labelmap.txt \
    #           -i dog.jpg --debug
    args = parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args.engine == 'classifier':
        engine = ONNXClassifierEngine(
                     model = args.model,
                     labels = args.labels,
                     top_k = args.top_k,
                     num_threads = args.num_threads)
    else:
        engine = ONNXDetectorEngine(
                     model = args.model,
                     labels = args.labels,
                     num_threads = args.num_threads)

    for i in range(5):
        bgr_array = cv2.imread(args.input)
        t = time.time()
        image_data = engine.process_input(bgr_array)
        output = engine.inference(image_data)
        model_outputs = engine.process_output(output)
        logger.debug('Inference takes {} s'.format(time.time() - t))

    if args.engine == 'classifier':
        for r in model_outputs['annotations']:
            logger.debug('label: {0}  conf: {1}'.format(
                r['label'],
                r['confidence']
            ))
    else:
        for r in model_outputs['annotations']:
            logger.debug('label: {0}  conf: {1}  ({2}, {3}) ({4}, {5})'.format(
                r['label'],
                r['confidence'],
                r['left'],
                r['top'],
                r['right'],
                r['bottom']
            ))


if __name__ == '__main__':
    main()
