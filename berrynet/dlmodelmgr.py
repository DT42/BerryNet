# Copyright 2017 DT42
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

"""
DL Model Manager, following the DLModelBox model package
specification.

A model package is a directory in the model base directory
(/usr/share/dlmodels, or $BERRYNET_MODEL_DIR) containing the model files
and a meta.json such as

    {"model": "detect.tflite", "label": "labelmap.txt", "config": {}}
"""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile

from berrynet import logger


DEFAULT_BASEDIR = '/usr/share/dlmodels'

_TFLITE_MODELS = ('https://storage.googleapis.com/'
                  'download.tensorflow.org/models/tflite/')
_ONNX_MODELS_COMMIT = 'c5cae0f1942c8d7727372c7b1f6b485aa39e4421'
_ONNX_MODELS_LFS = ('https://media.githubusercontent.com/media/onnx/models/'
                    + _ONNX_MODELS_COMMIT + '/validated/vision/')
_ONNX_MODELS_RAW = ('https://raw.githubusercontent.com/onnx/models/'
                    + _ONNX_MODELS_COMMIT + '/validated/vision/')
_COCO_SSD_LITERT_ZIP = {
    'url': _TFLITE_MODELS + 'coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip',
    'sha256': 'a809cd290b4d6a2e8a9d5dad076e0bd695b8091974e0eed1052b480b2f21b6dc',
}

# Model packages that "bn_model install" can download.
MODEL_PACKAGES = {
    'ssd-mobilenet-v1-coco-litert': {
        'description': 'COCO object detector, SSD MobileNet v1, quantized (LiteRT)',
        'files': [
            dict(_COCO_SSD_LITERT_ZIP,
                 extract=['detect.tflite', 'labelmap.txt']),
        ],
        'model': 'detect.tflite',
        'label': 'labelmap.txt',
    },
    'mobilenet-v1-imagenet-litert': {
        'description': 'ImageNet classifier, MobileNet v1 1.0 224, quantized (LiteRT)',
        'files': [{
            'url': _TFLITE_MODELS + 'mobilenet_v1_1.0_224_quant_and_labels.zip',
            'sha256': '2f8054076cf655e1a73778a49bd8fd0306d32b290b7e576dda9574f00f186c0f',
            'extract': ['mobilenet_v1_1.0_224_quant.tflite',
                        'labels_mobilenet_quant_v1_224.txt'],
        }],
        'model': 'mobilenet_v1_1.0_224_quant.tflite',
        'label': 'labels_mobilenet_quant_v1_224.txt',
    },
    'mobilenet-v2-imagenet-onnx': {
        'description': 'ImageNet classifier, MobileNetV2 (ONNX)',
        'files': [{
            'url': _ONNX_MODELS_LFS + 'classification/mobilenet/model/mobilenetv2-12.onnx',
            'sha256': 'c0c3f76d93fa3fd6580652a45618618a220fced18babf65774ed169de0432ad5',
        }, {
            'url': _ONNX_MODELS_RAW + 'classification/synset.txt',
            'sha256': 'acf75ef0abe89694b19056e0796401068b459c457baa30335f240c7692857355',
        }],
        'model': 'mobilenetv2-12.onnx',
        'label': 'synset.txt',
    },
    'ssd-mobilenet-v1-coco-onnx': {
        'description': 'COCO object detector, SSD MobileNet v1 (ONNX)',
        'files': [{
            'url': _ONNX_MODELS_LFS + 'object_detection_segmentation/ssd-mobilenetv1/model/ssd_mobilenet_v1_12.onnx',
            'sha256': 'b8fba5e404077d4048d27fcd1667e85e27e192eb9bf51e696c46a3acd7d21058',
        },
            # The same COCO label map as the LiteRT model.
            dict(_COCO_SSD_LITERT_ZIP, extract=['labelmap.txt']),
        ],
        'model': 'ssd_mobilenet_v1_12.onnx',
        'label': 'labelmap.txt',
    },
}


def download(url, path, sha256):
    """Download url to path and verify its SHA-256 checksum."""
    logger.info('Downloading {}'.format(url))
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=60) as response, \
            open(path, 'wb') as f:
        for chunk in iter(lambda: response.read(1 << 20), b''):
            digest.update(chunk)
            f.write(chunk)
    if digest.hexdigest() != sha256:
        raise ValueError('Checksum mismatch of {}: expected {}, got {}'.format(
            url, sha256, digest.hexdigest()))


class DLModelManager(object):
    def __init__(self, basedir=None):
        self.basedir = basedir or os.environ.get('BERRYNET_MODEL_DIR',
                                                 DEFAULT_BASEDIR)

    def get_model_names(self):
        if not os.path.isdir(self.basedir):
            return []
        return sorted(
            name for name in os.listdir(self.basedir)
            if os.path.isfile(os.path.join(self.basedir, name, 'meta.json')))

    def get_model_meta(self, modelname):
        meta_filepath = os.path.join(self.basedir, modelname, 'meta.json')
        with open(meta_filepath, 'r') as f:
            meta = json.load(f)
        meta['model'] = os.path.join(self.basedir, modelname, meta['model'])
        # Models such as Ultralytics YOLO contain their labels.
        if meta.get('label'):
            meta['label'] = os.path.join(self.basedir, modelname,
                                         meta['label'])
        else:
            meta['label'] = None
        for k, v in meta['config'].items():
            meta['config'][k] = os.path.join(self.basedir, modelname,
                                             meta['config'][k])
        return meta

    def install(self, modelname, force=False):
        """Download and install a model package of MODEL_PACKAGES.

        Returns:
            Path of the installed model package.
        """
        package = MODEL_PACKAGES[modelname]
        target = os.path.join(self.basedir, modelname)
        if os.path.isfile(os.path.join(target, 'meta.json')) and not force:
            logger.info('{} has been installed'.format(modelname))
            return target

        os.makedirs(self.basedir, exist_ok=True)
        # Build the package next to the target, then move it in place.
        with tempfile.TemporaryDirectory(dir=self.basedir) as workdir:
            pkgdir = os.path.join(workdir, modelname)
            os.mkdir(pkgdir)
            for spec in package['files']:
                path = os.path.join(workdir, os.path.basename(spec['url']))
                download(spec['url'], path, spec['sha256'])
                if 'extract' not in spec:
                    os.replace(path, os.path.join(pkgdir,
                                                  os.path.basename(path)))
                    continue
                with zipfile.ZipFile(path) as archive:
                    for member in spec['extract']:
                        dst = os.path.join(pkgdir, os.path.basename(member))
                        with archive.open(member) as src, \
                                open(dst, 'wb') as f:
                            shutil.copyfileobj(src, f)
            with open(os.path.join(pkgdir, 'meta.json'), 'w') as f:
                json.dump({
                    'model': package['model'],
                    'label': package['label'],
                    'config': {}
                }, f, indent=4)
            if os.path.exists(target):
                shutil.rmtree(target)
            os.replace(pkgdir, target)
        logger.info('Installed {} to {}'.format(modelname, target))
        return target


def parse_args():
    ap = argparse.ArgumentParser(description='Manage model packages.')
    ap.add_argument(
        '--basedir',
        help=('Model package directory. '
              '($BERRYNET_MODEL_DIR or {} by default)'.format(
                  DEFAULT_BASEDIR)))
    subparsers = ap.add_subparsers(dest='command', required=True)
    subparsers.add_parser('list', help='Show installed model packages.')
    subparsers.add_parser('available',
                          help='Show model packages that can be installed.')
    install_parser = subparsers.add_parser(
        'install', help='Download and install model packages.')
    install_parser.add_argument(
        'modelnames',
        nargs='+',
        choices=sorted(MODEL_PACKAGES),
        metavar='modelname',
        help='Model package name, see "available".')
    install_parser.add_argument(
        '--force',
        action='store_true',
        help='Reinstall model packages which have been installed.')
    return ap.parse_args()


def main():
    args = parse_args()
    dlmm = DLModelManager(args.basedir)
    if args.command == 'list':
        for name in dlmm.get_model_names():
            print(name)
    elif args.command == 'available':
        for name, package in sorted(MODEL_PACKAGES.items()):
            print('{:32} {}'.format(name, package['description']))
    else:
        for name in args.modelnames:
            dlmm.install(name, force=args.force)


if __name__ == '__main__':
    main()
