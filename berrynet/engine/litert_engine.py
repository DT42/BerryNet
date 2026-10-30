import logging
import time

from argparse import ArgumentParser

import cv2
import numpy as np

from ai_edge_litert.interpreter import Interpreter

from berrynet.engine import DLEngine
from berrynet.engine import classification_annotations
from berrynet.engine import detection_annotations
from berrynet.engine import load_labels
from berrynet import logger


class LiteRTDetectorEngine(DLEngine):
    """SSD detector, e.g. COCO SSD MobileNet v1."""

    def __init__(self, model, labels, threshold=0.5, num_threads=1):
        super(LiteRTDetectorEngine, self).__init__()

        # Load labels
        self.labels = load_labels(labels)
        self.classes = len(self.labels)

        # Load LiteRT model into memory
        self.interpreter = Interpreter(
            model_path=model,
            num_threads=num_threads)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_dtype = self.input_details[0]['dtype']
        _, self.input_h, self.input_w, _ = self.input_details[0]['shape']
        self.threshold = threshold

    def process_input(self, tensor):
        """Resize and normalize image for network input"""

        self.img_w = tensor.shape[1]
        self.img_h = tensor.shape[0]

        frame = cv2.cvtColor(tensor, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (self.input_w, self.input_h))
        frame = np.expand_dims(frame, axis=0)
        if self.input_dtype == np.float32:
            frame = (2.0 / 255.0) * frame - 1.0
            frame = frame.astype('float32')
        else:
            # default data type returned by cv2.imread is np.unit8
            pass
        return frame

    def inference(self, tensor):
        self.interpreter.set_tensor(self.input_details[0]['index'], tensor)
        self.interpreter.invoke()

        # get results
        boxes = self.interpreter.get_tensor(
            self.output_details[0]['index'])
        classes = self.interpreter.get_tensor(
            self.output_details[1]['index'])
        scores = self.interpreter.get_tensor(
            self.output_details[2]['index'])
        num = self.interpreter.get_tensor(
            self.output_details[3]['index'])
        return {
            'boxes': boxes,
            'classes': classes,
            'scores': scores,
            'num': num
        }

    def process_output(self, output):
        # Class indexes are 0-based, but the first label is the background.
        annotations = detection_annotations(
            output['boxes'][0], output['classes'][0], output['scores'][0],
            output['num'][0], self.labels, self.threshold,
            self.img_w, self.img_h, label_offset=1)
        return {'annotations': annotations}


class LiteRTClassifierEngine(DLEngine):
    def __init__(self, model, labels, top_k=3, num_threads=1,
                 input_mean=127.5, input_std=127.5):
        super(LiteRTClassifierEngine, self).__init__()

        # Load labels
        self.labels = load_labels(labels)
        self.classes = len(self.labels)

        # Load LiteRT model into memory
        self.interpreter = Interpreter(
            model_path=model,
            num_threads=num_threads)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.floating_model = False
        if self.input_details[0]['dtype'] == np.float32:
            self.floating_model = True
        self.input_mean = input_mean
        self.input_std = input_std
        self.top_k = int(top_k)

    def process_input(self, tensor):
        """Resize and normalize image for network input"""

        self.img_w = tensor.shape[1]
        self.img_h = tensor.shape[0]

        frame = cv2.cvtColor(tensor, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (self.input_details[0]['shape'][2],
                                   self.input_details[0]['shape'][1]))
        frame = np.expand_dims(frame, axis=0)
        if self.floating_model:
            frame = (np.float32(frame) - self.input_mean) / self.input_std
        return frame

    def inference(self, tensor):
        self.interpreter.set_tensor(self.input_details[0]['index'], tensor)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        results = np.squeeze(output_data)
        return {
            'scores': results,
        }

    def process_output(self, output):
        scores = output['scores'].astype(np.float32)
        if not self.floating_model:
            scores /= 255.0
        return {
            'annotations': classification_annotations(scores, self.labels,
                                                      self.top_k)
        }


def non_max_suppression(boxes, scores, iou_threshold):
    """Greedy non-maximum suppression.

    Args:
        boxes: [ymin, xmin, ymax, xmax] boxes.
        scores: Score of each box.

    Returns:
        Indexes of the kept boxes, highest score first.
    """
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        rest = order[1:]
        ymin = np.maximum(boxes[i, 0], boxes[rest, 0])
        xmin = np.maximum(boxes[i, 1], boxes[rest, 1])
        ymax = np.minimum(boxes[i, 2], boxes[rest, 2])
        xmax = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(ymax - ymin, 0, None) * np.clip(xmax - xmin, 0, None)
        iou = inter / np.maximum(areas[i] + areas[rest] - inter, 1e-9)
        order = rest[iou <= iou_threshold]
    return np.array(keep, dtype=int)


class LiteRTYoloV4DetectorEngine(DLEngine):
    """YOLOv4 detector whose outputs are boxes in (x, y, w, h) input
    pixels and per-class scores, e.g. models converted by
    tensorflow-yolov4-tflite.
    """

    def __init__(self, model, labels, threshold=0.1, num_threads=1,
                 score_threshold=0.25, iou_threshold=0.45,
                 max_detections=50):
        super(LiteRTYoloV4DetectorEngine, self).__init__()

        # Load labels
        self.labels = load_labels(labels)
        self.classes = len(self.labels)

        # Load LiteRT model into memory
        self.interpreter = Interpreter(
            model_path=model,
            num_threads=num_threads)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_dtype = self.input_details[0]['dtype']
        _, self.input_h, self.input_w, _ = self.input_details[0]['shape']
        self.threshold = threshold
        self.score_threshold = score_threshold
        self.iou_threshold = iou_threshold
        self.max_detections = max_detections

    def process_input(self, tensor):
        """Resize and normalize image for network input"""

        self.img_w = tensor.shape[1]
        self.img_h = tensor.shape[0]

        frame = cv2.cvtColor(tensor, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (self.input_w, self.input_h))
        frame = np.expand_dims(frame, axis=0)
        if self.input_dtype == np.float32:
            frame = (1.0 / 255.0) * frame
            frame = frame.astype('float32')
        else:
            # default data type returned by cv2.imread is np.unit8
            pass
        return frame

    def postprocess(self, box_xywh, scores):
        """Filter low scores and run per-class NMS on raw YOLOv4 outputs.

        Args:
            box_xywh: Boxes as (center x, center y, width, height) in
                input pixels.
            scores: Per-class scores of each box.

        Returns:
            Normalized [ymin, xmin, ymax, xmax] boxes, class indexes and
            scores, highest score first.
        """
        box_xywh = box_xywh.reshape(-1, 4)
        scores = scores.reshape(box_xywh.shape[0], -1)
        class_ids = scores.argmax(axis=-1)
        confidences = scores.max(axis=-1)

        mask = confidences >= self.score_threshold
        box_xywh = box_xywh[mask]
        class_ids = class_ids[mask]
        confidences = confidences[mask]

        center_yx = box_xywh[:, 1::-1]
        half_hw = box_xywh[:, :1:-1] / 2.0
        input_hw = np.array([self.input_h, self.input_w], dtype=np.float32)
        boxes = np.concatenate([(center_yx - half_hw) / input_hw,
                                (center_yx + half_hw) / input_hw], axis=-1)

        keep = []
        for class_id in np.unique(class_ids):
            index = np.flatnonzero(class_ids == class_id)
            keep.extend(index[non_max_suppression(
                boxes[index], confidences[index], self.iou_threshold)])
        keep = np.array(keep, dtype=int)
        keep = keep[confidences[keep].argsort()[::-1]][:self.max_detections]
        return boxes[keep], class_ids[keep], confidences[keep]

    def inference(self, tensor):
        self.interpreter.set_tensor(self.input_details[0]['index'], tensor)
        self.interpreter.invoke()

        # get results
        pred = [self.interpreter.get_tensor(self.output_details[i]['index'])
                for i in range(len(self.output_details))]
        boxes, classes, scores = self.postprocess(pred[0], pred[1])
        return {
            'boxes': boxes,
            'classes': classes,
            'scores': scores,
            'num': len(scores)
        }

    def process_output(self, output):
        annotations = detection_annotations(
            output['boxes'], output['classes'], output['scores'],
            output['num'], self.labels, self.threshold,
            self.img_w, self.img_h)
        return {'annotations': annotations}


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "-e", "--engine",
        help=("Classifier, detector or yolov4 engine. "
              "(classifier by default)"),
        default="classifier",
        choices=["classifier", "detector", "yolov4"],
        type=str)
    parser.add_argument(
        "-m", "--model",
        help="Path to a .tflite model file.",
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
    #     $ python3 -m berrynet.engine.litert_engine -e detector \
    #           -m detect.tflite --labels labelmap.txt -i dog.jpg --debug
    args = parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args.engine == 'classifier':
        engine = LiteRTClassifierEngine(
                     model = args.model,
                     labels = args.labels,
                     top_k = args.top_k,
                     num_threads = args.num_threads)
    elif args.engine == 'detector':
        engine = LiteRTDetectorEngine(
                     model = args.model,
                     labels = args.labels,
                     num_threads = args.num_threads)
    else:
        engine = LiteRTYoloV4DetectorEngine(
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
