#!/bin/sh

# Main dependencies

sudo apt-get update
#sudo apt-get install -y git-lfs

# Download models

CAFFE2_MODEL_DIR="/caffe2/caffe2/python/models"

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

#TMPDIR1=`mktemp -d`
#cd /caffe2/build
#sudo python -m caffe2.python.models.download squeezenet
#sudo mkdir -p "$TMPDIR1"/models
#sudo mv -f squeezenet "$TMPDIR1"/models
#cd "$TMPDIR1"
#git lfs clone https://github.com/caffe2/models.git


# Install models

sudo mkdir -p $CAFFE2_MODEL_DIR
git clone https://github.com/caffe2/models.git /tmp/caffe2-models
sudo cp -a /tmp/caffe2-models/squeezenet $CAFFE2_MODEL_DIR
sudo cp -a /tmp/caffe2-models/bvlc_alexnet $CAFFE2_MODEL_DIR
rm -rf /tmp/caffe2-models
#sudo cp -f models/squeezenet/*.pb /caffe2/caffe2/python/models
#sudo cp -f models/bvlc_alexnet/*.npy /caffe2/caffe2/python/models
