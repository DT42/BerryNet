#!/bin/sh

# Main dependencies

sudo apt-get update
#sudo apt-get install -y git-lfs

# Download models

TMPDIR1=`mktemp -d`


cd /caffe2/build
sudo python -m caffe2.python.models.download squeezenet
sudo mkdir -p "$TMPDIR1"/models
sudo mv -f squeezenet "$TMPDIR1"/models
cd "$TMPDIR1"
#git lfs clone https://github.com/caffe2/models.git


# Install models

sudo mkdir -p /caffe2/caffe2/python/models
sudo cp -f models/squeezenet/*.pb /caffe2/caffe2/python/models
sudo cp -f models/bvlc_alexnet/*.npy /caffe2/caffe2/python/models
