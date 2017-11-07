#!/bin/sh

# Main dependencies

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
      build-essential \
      cmake \
      git \
      libgoogle-glog-dev \
      libprotobuf-dev \
      protobuf-compiler \
      python-dev \
      python-pip
sudo pip install --upgrade pip
sudo pip install numpy protobuf

# Optional dependencies
sudo apt-get install -y --no-install-recommends libgflags-dev
sudo apt-get install -y --no-install-recommends \
      libgtest-dev \
      libiomp-dev \
      libleveldb-dev \
      liblmdb-dev \
      libopencv-dev \
      libopenmpi-dev \
      libsnappy-dev \
      openmpi-bin \
      openmpi-doc \
      python-pydot
sudo pip install \
      flask \
      future \
      graphviz \
      hypothesis \
      jupyter \
      matplotlib \
      pydot python-nvd3 \
      pyyaml \
      requests \
      scikit-image \
      scipy \
      setuptools \
      six \
      tornado

# Build and install caffe2

cd /   # Not sure why we need to build from /
sudo git clone --recursive https://github.com/caffe2/caffe2.git
cd caffe2
sudo make
cd build
sudo make install

# Test
export PYTHONPATH=/usr/local:$PYTHONPATH
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

python -c 'from caffe2.python import core' 2>/dev/null && echo "Success" || echo "Failure"
