#!/bin/sh

# Main dependencies

sudo apt-get update
sudo apt-get install -y \
      build-essential \
      git \
      cmake \
      googletest \
      libgflags-dev \
      libgoogle-glog-dev \
      libprotobuf-dev \
      libpython-dev \
      python-pip \
      python-numpy \
      protobuf-compiler \
      python-protobuf \
      python-skimage \
      python-future

# Build and install caffe2

cd /   # Not sure why we need to build from /
sudo git clone --recursive https://github.com/caffe2/caffe2.git
cd caffe2
sudo ./scripts/build_raspbian.sh
cd build
sudo make install
