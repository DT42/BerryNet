# Copyright 2018 DT42
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

"""OpenVINO classification inference engine.
"""

import logging
import os
import sys

from argparse import ArgumentParser
from time import time

from berrynet.engine import DLEngine
import cv2
import numpy as np

from berrynet import logger
from openvino.inference_engine import IENetwork, IEPlugin


class OpenVINOClassifierEngine(DLEngine):
    def __init__(self, model, labels=None, top_k=3, device='CPU'):
        """
        Args:
            model: Path to an .xml file with a trained model.

            device: Specify the target device to infer on; CPU, GPU, FPGA
                    or MYRIAD is acceptable. Sample will look for a suitable
                    plugin for device specified (CPU by default)

            labels: Labels mapping file

            top_k: Number of top results
        """
        super(OpenVINOClassifierEngine, self).__init__()

        model_bin = model
        model_xml = os.path.splitext(model_bin)[0] + ".xml"
        if labels:
            with open(labels, 'r') as f:
                # Allow label name with spaces. To use onlyh the 1st word,
                # uncomment another labels_map implementation below.
                self.labels_map = [l.strip() for l in f.readlines()]
                #self.labels_map = [x.split(sep=' ', maxsplit=1)[-1].strip()
                #                   for x in f]
        else:
            self.labels_map = None
        self.top_k = top_k

        # Plugin initialization for specified device and
        # load extensions library if specified
        #
        # Note: MKLDNN CPU-targeted custom layer support is not included
        #       because we do not use it yet.
        self.plugin = IEPlugin(device=device, plugin_dirs=None)

        # Read IR
        logger.debug('Loading network files:'
                     '\n\txml: {0}\n\tbin: {1}'.format(model_xml, model_bin))
        net = IENetwork.from_ir(model=model_xml, weights=model_bin)

        if self.plugin.device == "CPU":
            supported_layers = self.plugin.get_supported_layers(net)
            not_supported_layers = [l for l in net.layers.keys() if l not in supported_layers]
            if len(not_supported_layers) != 0:
                logger.error("Following layers are not supported by the plugin for specified device {}:\n {}".format(self.plugin.device, ', '.join(not_supported_layers)))
                sys.exit(1)

        assert len(net.inputs.keys()) == 1, "Sample supports only single input topologies"
        assert len(net.outputs) == 1, "Sample supports only single output topologies"

        # input_blob and and out_blob are the layer names in string format.
        logger.debug("Preparing input blobs")
        self.input_blob = next(iter(net.inputs))
        self.out_blob = next(iter(net.outputs))
        net.batch_size = 1

        self.n, self.c, self.h, self.w = net.inputs[self.input_blob].shape

        # Loading model to the plugin
        logger.debug("Loading model to the plugin")
        self.exec_net = self.plugin.load(network=net)

        del net

    def __delete__(self, instance):
        del self.exec_net
        del self.plugin

    def process_input(self, tensor):
        """Resize tensor (if needed) and change layout from HWC to CHW.

        Args:
            tensor: Input BGR tensor (OpenCV convention)

        Returns:
            Resized and transposed tensor
        """
        if tensor.shape[:-1] != (self.h, self.w):
            logger.warning("Input tensor is resized from {} to {}".format(
                tensor.shape[:-1], (self.h, self.w)))
            tensor = cv2.resize(tensor, (self.w, self.h))
        tensor = tensor.transpose((2, 0, 1))  # Change data layout from HWC to CHW
        return tensor

    def inference(self, tensor):
        logger.debug("Starting inference")
        res = self.exec_net.infer(inputs={self.input_blob: tensor})
        return res[self.out_blob]

    def process_output(self, output):
        logger.debug("Processing output blob")
        logger.debug("Top {} results: ".format(self.top_k))

        annotations = []
        for i, probs in enumerate(output):
            probs = np.squeeze(probs)
            top_ind = np.argsort(probs)[-self.top_k:][::-1]
            for id in top_ind:
                det_label = self.labels_map[id] if self.labels_map else "#{}".format(id)
                logger.debug("\t{:.7f} label {}".format(probs[id], det_label))

                annotations.append({
                    'type': 'classification',
                    'label': det_label,
                    'confidence': float(probs[id])
                })
        return {'annotations': annotations}


class OpenVINODetectorEngine(DLEngine):
    def __init__(self, model, labels=None, threshold=0.3, device='CPU'):
        super(OpenVINODetectorEngine, self).__init__()

        # Prepare model and labels
        model_bin = model
        model_xml = os.path.splitext(model_bin)[0] + ".xml"
        if labels:
            with open(labels, 'r') as f:
                self.labels_map = [x.strip() for x in f]
        else:
            self.labels_map = None
        self.threshold = threshold

        # Plugin initialization for specified device and
        # load extensions library if specified
        #
        # Note: MKLDNN CPU-targeted custom layer support is not included
        #       because we do not use it yet.
        if device == 'CPU':
            # Since OpenVINO 2020.1, cpu_extension content has been merged
            # into MKLDNN plugin and it is used automatically.
            #
            # We do not need to call these functions below anymore:
            #     self.plugin.add_cpu_extension(plugin_dirs + '/libcpu_extension_avx2.so')
            #     self.plugin.add_cpu_extension(plugin_dirs + '/libcpu_extension_avx512.so')
            #     self.plugin.add_cpu_extension(plugin_dirs + '/libcpu_extension_sse4.so')
            plugin_dirs = '/opt/intel/openvino/deployment_tools/inference_engine/lib/intel64'
            self.plugin = IEPlugin(device=device, plugin_dirs=plugin_dirs)
            logger.debug('plugin dirs: {}'.format(plugin_dirs))
        else:
            plugin_dirs = None
            self.plugin = IEPlugin(device=device, plugin_dirs=plugin_dirs)

        # Read IR
        logger.debug('Loading network files:'
                     '\n\txml: {0}\n\tbin: {1}'.format(model_xml, model_bin))
        net = IENetwork(model=model_xml, weights=model_bin)

        if self.plugin.device == "CPU":
            supported_layers = self.plugin.get_supported_layers(net)
            not_supported_layers = [l for l in net.layers.keys() if l not in supported_layers]
            if len(not_supported_layers) != 0:
                logger.error("Following layers are not supported by the plugin for specified device {}:\n {}".
                          format(self.plugin.device, ', '.join(not_supported_layers)))
                logger.error("Please try to specify cpu extensions library path in demo's command line parameters using -l "
                          "or --cpu_extension command line argument")
                sys.exit(1)

        assert len(net.inputs.keys()) == 1, "Demo supports only single input topologies"
        assert len(net.outputs) == 1, "Demo supports only single output topologies"

        # input_blob and and out_blob are the layer names in string format.
        logger.debug("Preparing input blobs")
        self.input_blob = next(iter(net.inputs))
        self.out_blob = next(iter(net.outputs))

        self.n, self.c, self.h, self.w = net.inputs[self.input_blob].shape

        # Loading model to the plugin
        self.exec_net = self.plugin.load(network=net, num_requests=2)

        del net

        # Initialize engine mode: sync or async
        #
        # FIXME: async mode does not work currently.
        #        process_input needs to provide two input tensors for async.
        self.is_async_mode = False
        self.cur_request_id = 0
        self.next_request_id = 1

    def __delete__(self, instance):
        del self.exec_net
        del self.plugin

    def process_input(self, tensor, next_tensor=None):
        frame = tensor
        next_frame = next_tensor

        # original input shape will be used in process_output
        self.img_w = tensor.shape[1]
        self.img_h = tensor.shape[0]

        # Main sync point:
        # in the truly Async mode we start the NEXT infer request, while waiting for the CURRENT to complete
        # in the regular mode we start the CURRENT request and immediately wait for it's completion
        if self.is_async_mode:
            in_frame = cv2.resize(next_frame, (self.w, self.h))
            in_frame = in_frame.transpose((2, 0, 1))  # Change data layout from HWC to CHW
            in_frame = in_frame.reshape((self.n, self.c, self.h, self.w))
        else:
            in_frame = cv2.resize(frame, (self.w, self.h))
            in_frame = in_frame.transpose((2, 0, 1))  # Change data layout from HWC to CHW
            in_frame = in_frame.reshape((self.n, self.c, self.h, self.w))
        return in_frame

    def inference(self, tensor):
        inf_start = time()
        if self.is_async_mode:
            self.exec_net.start_async(request_id=self.next_request_id, inputs={self.input_blob: tensor})
        else:
            self.exec_net.start_async(request_id=self.cur_request_id, inputs={self.input_blob: tensor})

        if self.exec_net.requests[self.cur_request_id].wait(-1) == 0:
            inf_end = time()
            det_time = inf_end - inf_start
            if self.is_async_mode:
                logger.debug('Inference time: N\A for async mode')
            else:
                logger.debug("Inference time: {:.3f} ms".format(det_time * 1000))

            # Parse detection results of the current request
            res = self.exec_net.requests[self.cur_request_id].outputs[self.out_blob]
        else:
            res = None

        return res

        # FIXME: async mode does not work currently.
        #        process_input needs to provide two input tensors for async.
        if self.is_async_mode:
            self.cur_request_id, self.next_request_id = self.next_request_id, self.cur_request_id
            frame = next_frame

    def process_output(self, output):
        logger.debug("Processing output blob")
        logger.debug("Threshold: {}".format(self.threshold))

        annotations = []
        for obj in output[0][0]:
            # Collect objects when probability more than specified threshold
            if obj[2] > self.threshold:
                xmin = int(obj[3] * self.img_w)
                ymin = int(obj[4] * self.img_h)
                xmax = int(obj[5] * self.img_w)
                ymax = int(obj[6] * self.img_h)
                class_id = int(obj[1])
                det_label = self.labels_map[class_id] if self.labels_map else str(class_id)
                annotations.append({
                    'label': det_label,
                    'confidence': float(obj[2]),
                    'left': xmin,
                    'top': ymin,
                    'right': xmax,
                    'bottom': ymax
                })
        return {'annotations': annotations}


def get_distribution_info():
    """Get Debuan or Ubuntu distribution information.
    """
    info = {}
    with open('/etc/lsb-release') as f:
        info_l = [i.strip().split('=') for i in f.readlines()]
    for i in info_l:
        info[i[0]] = i[1]
    logger.debug('Distribution info: {}'.format(info))
    return info


def set_openvino_environment():
    """The same effect as executing <openvino>/bin/setupvars.sh.
    """
    dist_info = get_distribution_info()
    python_version = 3.5

    os.environ['INSTALLDIR'] = '/opt/intel/computer_vision_sdk_2018.4.420'
    os.environ['INTEL_CVSDK_DIR'] = os.environ['INSTALLDIR']
    os.environ['LD_LIBRARY_PATH'] = (
        '{installdir}/deployment_tools/model_optimizer/bin:'
        '{ld_library_path}').format(
            installdir = os.environ.get('INSTALLDIR'),
            ld_library_path = os.environ.get('LD_LIBRARY_PATH' or '')
    )
    os.environ['InferenceEngine_DIR'] = os.path.join(
        os.environ.get('INTEL_CVSDK_DIR'),
        'deployment_tools/inference_engine/share'
    )
    os.environ['IE_PLUGINS_PATH'] = os.path.join(
        os.environ.get('INTEL_CVSDK_DIR'),
        'deployment_tools/inference_engine/lib/ubuntu_{}.04/intel64'.format(
            dist_info['DISTRIB_RELEASE'])
    )
    os.environ['LD_LIBRARY_PATH'] = (
        '/opt/intel/opencl:'
        '{installdir}/deployment_tools/inference_engine/external/gna/lib:'
        '{installdir}/deployment_tools/inference_engine/external/mkltiny_lnx/lib:'
        '{installdir}/deployment_tools/inference_engine/external/omp/lib:'
        '{ie_plugins_path}:'
        '{ld_library_path}').format(
            installdir = os.environ.get('INSTALLDIR'),
            ie_plugins_path = os.environ.get('IE_PLUGINS_PATH'),
            ld_library_path = os.environ.get('LD_LIBRARY_PATH' or '')
    )
    os.environ['PATH'] = (
        '{intel_cvsdk_dir}/deployment_tools/model_optimizer:'
        '{path}').format(
            intel_cvsdk_dir = os.environ.get('INTEL_CVSDK_DIR'),
            path = os.environ.get('PATH'),
    )
    os.environ['PYTHONPATH'] = (
        '{intel_cvsdk_dir}/deployment_tools/model_optimizer:'
        '{pythonpath}').format(
            intel_cvsdk_dir = os.environ.get('INTEL_CVSDK_DIR'),
            pythonpath = os.environ.get('PYTHONPATH' or '')
    )
    os.environ['PYTHONPATH'] = (
        '{intel_cvsdk_dir}/python/python$python_version:'
        '{intel_cvsdk_dir}/python/python$python_version/ubuntu16:'
        '{pythonpath}').format(
            intel_cvsdk_dir = os.environ.get('INTEL_CVSDK_DIR'),
            pythonpath = os.environ.get('PYTHONPATH' or '')
    )


def parse_argsr():
    parser = ArgumentParser()
    parser.add_argument(
        "-e", "--engine",
        help=("Classifier or Detector engine. "
              "classifier, or detector is acceptable. "
              "(classifier by default)"),
        default="classifier",
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
        default=10,
        type=int)
    parser.add_argument(
        "-d", "--device",
        help="Specify the target device to infer on; CPU, GPU, FPGA or MYRIAD is acceptable. Sample will look for a suitable plugin for device specified (CPU by default)",
        default="CPU",
        type=str)
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
    args = parse_argsr()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args.engine == 'classifier':
        engine = OpenVINOClassifierEngine(
                     model = args.model,
                     device = args.device,
                     labels = args.labels,
                     top_k = args.top_k)
    elif args.engine == 'detector':
        engine = OpenVINODetectorEngine(
                     model = args.model,
                     device = args.device,
                     labels = args.labels)
    else:
        raise Exception('Illegal engine {}, it should be '
                        'classifier or detector'.format(args.engine))

    #set_openvino_environment()
    #if args.debug:
    #    logger.debug('OpenVINO environment vars')
    #    target_vars = ['INSTALLDIR',
    #                   'INTEL_CVSDK_DIR',
    #                   'LD_LIBRARY_PATH',
    #                   'InferenceEngine_DIR',
    #                   'IE_PLUGINS_PATH',
    #                   'PATH',
    #                   'PYTHONPATH']
    #    for i in target_vars:
    #        logger.debug('\t{var}: {val}'.format(
    #            var = i,
    #            val = os.environ.get(i)))

    bgr_array = cv2.imread(args.input)
    t = time()
    image_data = engine.process_input(bgr_array)
    output = engine.inference(image_data)
    model_outputs = engine.process_output(output)
    logger.debug('Result: {}'.format(model_outputs))
    logger.debug('Classification takes {} s'.format(time() - t))


if __name__ == '__main__':
    main()
