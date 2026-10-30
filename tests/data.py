"""Model packages and images used by the engine tests.

Download them into $BERRYNET_MODEL_DIR (/usr/share/dlmodels by default):

    $ BERRYNET_MODEL_DIR=models uv run python -m tests.data
"""

import os

from berrynet.dlmodelmgr import DLModelManager
from berrynet.dlmodelmgr import download


MODEL_PACKAGES = [
    'mobilenet-v1-imagenet-litert',
    'mobilenet-v2-imagenet-onnx',
    'ssd-mobilenet-v1-coco-litert',
    'ssd-mobilenet-v1-coco-onnx',
]

# An image with a dog, a bicycle and a car.
DOG_JPG = {
    'url': ('https://raw.githubusercontent.com/pjreddie/darknet/'
            'f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/data/dog.jpg'),
    'sha256': '5a9522051c3cec2bbd2f6323fccba32e8fbf3ddcc2b3e2fd46b04c720bc6f866',
}

# A grasshopper.
GRASSHOPPER_JPG = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'berrynet', 'engine', 'grace_hopper.jpg')


def dog_jpg_path():
    return os.path.join(DLModelManager().basedir, 'dog.jpg')


def main():
    dlmm = DLModelManager()
    for name in MODEL_PACKAGES:
        dlmm.install(name)
    if not os.path.isfile(dog_jpg_path()):
        download(DOG_JPG['url'], dog_jpg_path(), DOG_JPG['sha256'])


if __name__ == '__main__':
    main()
