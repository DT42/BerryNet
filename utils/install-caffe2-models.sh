#!/bin/sh

# Main dependencies

sudo apt-get update
#sudo apt-get install -y git-lfs

# Download models
#
# FIXME: caffe2.python.models.download can not download correct
#   squeezenet model files currently.
#
#   It will download {init_net.pb, predict_net.pb}, but the latest
#   squeezenet model files on Caffe2 model repo are
#   {exec_net.pb, predict_net.pb}.
#
#   These two predict_net.pb are also different.
#
# Caffe2 model repo: https://github.com/caffe2/models/tree/master/squeezenet

CAFFE2_MODEL_DIR="/caffe2/caffe2/python/models"

#TMPDIR1=`mktemp -d`
#cd /caffe2/build
#sudo python -m caffe2.python.models.download squeezenet
#sudo mkdir -p "$TMPDIR1"/models
#sudo mv -f squeezenet "$TMPDIR1"/models
#cd "$TMPDIR1"
#git lfs clone https://github.com/caffe2/models.git


# Install models
#
# FIXME: git-lfs is unavailable on Raspbian.

sudo mkdir -p $CAFFE2_MODEL_DIR/squeezenet
sudo wget -O $CAFFE2_MODEL_DIR/squeezenet/exec_net.pb \
    https://github.com/caffe2/models/raw/master/squeezenet/exec_net.pb
sudo wget -O $CAFFE2_MODEL_DIR/squeezenet/predict_net.pb \
    https://github.com/caffe2/models/raw/master/squeezenet/predict_net.pb
#sudo cp -f models/squeezenet/*.pb /caffe2/caffe2/python/models
#sudo cp -f models/bvlc_alexnet/*.npy /caffe2/caffe2/python/models
