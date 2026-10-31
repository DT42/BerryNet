import hashlib
import json
import os
import pathlib
import tempfile
import unittest
import zipfile

from unittest import mock

from berrynet.dlmodelmgr import DLModelManager
from berrynet.dlmodelmgr import MODEL_PACKAGES


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestDLModelManager(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.basedir = os.path.join(tmpdir.name, 'dlmodels')

        self.archive = os.path.join(tmpdir.name, 'model.zip')
        with zipfile.ZipFile(self.archive, 'w') as archive:
            archive.writestr('model/model.tflite', b'model')
            archive.writestr('model/labels.txt', 'person\n')
            archive.writestr('README', 'not extracted')
        self.label_file = os.path.join(tmpdir.name, 'synset.txt')
        with open(self.label_file, 'w') as f:
            f.write('n01440764 tench\n')

    def package(self, archive_sha256=None):
        return {
            'description': 'Test model',
            'files': [{
                'url': pathlib.Path(self.archive).as_uri(),
                'sha256': archive_sha256 or sha256(self.archive),
                'extract': ['model/model.tflite', 'model/labels.txt'],
            }, {
                'url': pathlib.Path(self.label_file).as_uri(),
                'sha256': sha256(self.label_file),
            }],
            'model': 'model.tflite',
            'label': 'labels.txt',
        }

    def test_install(self):
        dlmm = DLModelManager(self.basedir)
        with mock.patch.dict(MODEL_PACKAGES, {'test-model': self.package()}):
            path = dlmm.install('test-model')

        self.assertEqual(path, os.path.join(self.basedir, 'test-model'))
        self.assertEqual(sorted(os.listdir(path)),
                         ['labels.txt', 'meta.json', 'model.tflite',
                          'synset.txt'])
        self.assertEqual(dlmm.get_model_names(), ['test-model'])
        meta = dlmm.get_model_meta('test-model')
        self.assertEqual(meta['model'], os.path.join(path, 'model.tflite'))
        self.assertEqual(meta['label'], os.path.join(path, 'labels.txt'))
        with open(meta['model'], 'rb') as f:
            self.assertEqual(f.read(), b'model')

    def test_install_checksum_mismatch(self):
        dlmm = DLModelManager(self.basedir)
        package = self.package(archive_sha256='0' * 64)
        with mock.patch.dict(MODEL_PACKAGES, {'test-model': package}):
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                dlmm.install('test-model')
        self.assertEqual(os.listdir(self.basedir), [])

    def test_model_meta_without_label(self):
        # Models such as Ultralytics YOLO contain their labels.
        os.makedirs(os.path.join(self.basedir, 'yolo'))
        with open(os.path.join(self.basedir, 'yolo', 'meta.json'), 'w') as f:
            json.dump({'model': 'yolo26n.tflite', 'config': {}}, f)
        meta = DLModelManager(self.basedir).get_model_meta('yolo')
        self.assertEqual(meta['model'],
                         os.path.join(self.basedir, 'yolo', 'yolo26n.tflite'))
        self.assertIsNone(meta['label'])

    def test_basedir_from_environment(self):
        with mock.patch.dict(os.environ, {'BERRYNET_MODEL_DIR': self.basedir}):
            self.assertEqual(DLModelManager().basedir, self.basedir)
        self.assertEqual(DLModelManager(self.basedir).get_model_names(), [])
