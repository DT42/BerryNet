import logging
import time

from argparse import ArgumentParser
from os import path

import cv2
import numpy as np
import tensorflow as tf

from berrynet.engine import DLEngine
from berrynet import logger


class TFLiteYoloV4DetectorEngine(DLEngine):
    def __init__(self, model, labels, threshold=0.1, num_threads=1):
        """
        Builds Tensorflow graph, load model and labels
        """
        # Load labels
        self.labels = self._load_label(labels)
        self.classes = len(self.labels)

        # Define lite graph and Load Tensorflow Lite model into memory
        self.interpreter = tf.lite.Interpreter(
            model_path=model)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_dtype = self.input_details[0]['dtype']
        self.num_threads = num_threads
        self.threshold = threshold

    def __delete__(self, instance):
        #tf.reset_default_graph()
        #self.sess = tf.InteractiveSession()
        del self.interpreter

    def process_input(self, tensor):
        """Resize and normalize image for network input"""

        self.img_w = tensor.shape[1]
        self.img_h = tensor.shape[0]

        frame = cv2.cvtColor(tensor, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (416, 416))
        frame = np.expand_dims(frame, axis=0)
        if self.input_dtype == np.float32:
            frame = (1.0 / 255.0) * frame
            frame = frame.astype('float32')
        else:
            # default data type returned by cv2.imread is np.unit8
            pass
        return frame

    def filter_boxes(self, box_xywh, scores, score_threshold=0.4, input_shape = tf.constant([416,416])):
        scores_max = tf.math.reduce_max(scores, axis=-1)

        mask = scores_max >= score_threshold
        class_boxes = tf.boolean_mask(box_xywh, mask)
        pred_conf = tf.boolean_mask(scores, mask)
        class_boxes = tf.reshape(class_boxes, [tf.shape(scores)[0], -1, tf.shape(class_boxes)[-1]])
        pred_conf = tf.reshape(pred_conf, [tf.shape(scores)[0], -1, tf.shape(pred_conf)[-1]])

        box_xy, box_wh = tf.split(class_boxes, (2, 2), axis=-1)

        input_shape = tf.cast(input_shape, dtype=tf.float32)

        box_yx = box_xy[..., ::-1]
        box_hw = box_wh[..., ::-1]

        box_mins = (box_yx - (box_hw / 2.)) / input_shape
        box_maxes = (box_yx + (box_hw / 2.)) / input_shape
        boxes = tf.concat([
            box_mins[..., 0:1],  # y_min
            box_mins[..., 1:2],  # x_min
            box_maxes[..., 0:1],  # y_max
            box_maxes[..., 1:2]  # x_max
        ], axis=-1)
        # return tf.concat([boxes, pred_conf], axis=-1)
        return (boxes, pred_conf)
    
    def inference(self, tensor):
        #self.interpreter.set_num_threads(int(self.num_threads));
        self.interpreter.set_tensor(self.input_details[0]['index'], tensor)
        self.interpreter.invoke()

        # get results
        pred = [self.interpreter.get_tensor(self.output_details[i]['index']) for i in range(len(self.output_details))]

        boxes, pred_conf = self.filter_boxes(pred[0], pred[1], score_threshold=0.25, input_shape=tf.constant([416, 416]))
        
        boxes, scores, classes, valid_detections = tf.image.combined_non_max_suppression(
            boxes=tf.reshape(boxes, (tf.shape(boxes)[0], -1, 1, 4)),
            scores=tf.reshape(
                pred_conf, (tf.shape(pred_conf)[0], -1, tf.shape(pred_conf)[-1])),
            max_output_size_per_class=50,
            max_total_size=50,
            iou_threshold=0.45,
            score_threshold=0.25
        )


        return {
            'boxes': boxes,
            'classes': classes,
            'scores': scores,
            'num': valid_detections
        }

    def process_output(self, output):
        # get results
        boxes = np.squeeze(output['boxes'][0])
        classes = np.squeeze(output['classes'][0]).astype(np.int32)
        scores = np.squeeze(output['scores'][0])
        num = output['num'][0]

        annotations = []
        number_boxes = boxes.shape[0]
        for i in range(number_boxes):
            box = tuple(boxes[i].tolist())
            ymin, xmin, ymax, xmax = box

            if scores[i] < self.threshold:
                continue
            annotations.append({
                'label': self.labels[classes[i]],
                'confidence': float(scores[i]),
                'left': int(xmin * self.img_w),
                'top': int(ymin * self.img_h),
                'right': int(xmax * self.img_w),
                'bottom': int(ymax * self.img_h)
            })
        return {'annotations': annotations}

    def _load_label(self, path):
        with open(path, 'r') as f:
            labels = list(map(str.strip, f.readlines()))
        return labels

def parse_argsr():
    parser = ArgumentParser()
    parser.add_argument(
        "-e", "--engine",
        help=("Classifier or Detector engine. "
              "classifier, or detector is acceptable. "
              "(detector by default)"),
        default="detector",
        type=str)
    parser.add_argument(
        "-m", "--model",
        help="Path to an .xml file with a trained model.",
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
        help="Path to a folder with images or path to an image files",
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
    #     $ python3 tfliteyolov4_engine.py -m yolov4-tiny-*.tflite \
    #           --labels coco.names -i dog.jpg --debug
    args = parse_argsr()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args.engine == 'detector':
        engine = TFLiteYoloV4DetectorEngine(
                     model = args.model,
                     labels = args.labels,
                     num_threads = args.num_threads)
    else:
        raise Exception('Illegal engine {}, it should be '
                        'classifier or detector'.format(args.engine))

    for i in range(5):
        bgr_array = cv2.imread(args.input)
        t = time.time()
        image_data = engine.process_input(bgr_array)
        output = engine.inference(image_data)
        model_outputs = engine.process_output(output)
        # Reference result
        #     input:
        #         darknet/data/dog.jpg
        #     output:
        #         Inference takes 0.7533011436462402 s
        #         Inference takes 0.5741658210754395 s
        #         Inference takes 0.6120760440826416 s
        #         Inference takes 0.6191139221191406 s
        #         Inference takes 0.5809791088104248 s
        #         label: bicycle  conf: 0.9563907980918884  (139, 116) (567, 429)
        #         label: car  conf: 0.8757821917533875  (459, 80) (690, 172)
        #         label: dog  conf: 0.869189441204071  (131, 218) (314, 539)
        #         label: car  conf: 0.40003547072410583  (698, 122) (724, 152)
        logger.debug('Inference takes {} s'.format(time.time() - t))

    if args.engine == 'classifier':
        for r in model_outputs['annotations']:
            logger.debug('label: {0}  conf: {1}'.format(
                r['label'],
                r['confidence']
            ))
    elif args.engine == 'detector':
        for r in model_outputs['annotations']:
            logger.debug('label: {0}  conf: {1}  ({2}, {3}) ({4}, {5})'.format(
                r['label'],
                r['confidence'],
                r['left'],
                r['top'],
                r['right'],
                r['bottom']
            ))
    else:
        raise Exception('Can not get result '
                        'from illegal engine {}'.format(args.engine))


if __name__ == '__main__':
    main()
