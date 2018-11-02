#!/bin/bash

# TODO: Create a Debian package based on
#       <opencv>/opencv-VERSION/build/install_manifest.txt

OPENCV_VERSION="3.1.0"
OPENCV_DIR="/tmp/opencv"
OPENCV_SRC_DIR="$OPENCV_DIR/opencv-$OPENCV_VERSION"
OPENCV_CONTRIB_SRC_DIR="$OPENCV_DIR/opencv_contrib-$OPENCV_VERSION"

install_dependencies() {
    sudo apt-get update
    sudo apt-get -y install build-essential cmake pkg-config
    sudo apt-get -y install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev
    sudo apt-get -y install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
    sudo apt-get -y install libxvidcore-dev libx264-dev
    sudo apt-get -y install libgtk2.0-dev
    sudo apt-get -y install libatlas-base-dev gfortran
    sudo apt-get -y install python2.7-dev python3-dev
    sudo apt-get -y install python-pip python3-pip
    pip install --user numpy
    pip3 install --user numpy
}

download_opencv() {
    rm -rf $OPENCV_DIR
    mkdir -p $OPENCV_DIR
    pushd $OPENCV_DIR > /dev/null
    wget -O opencv.zip https://github.com/opencv/opencv/archive/${OPENCV_VERSION}.zip
    unzip opencv.zip
    wget -O opencv_contrib.zip https://github.com/opencv/opencv_contrib/archive/${OPENCV_VERSION}.zip
    unzip opencv_contrib.zip
    popd > /dev/null
}

compile_opencv() {
    rm -rf $OPENCV_SRC_DIR/build
    mkdir $OPENCV_SRC_DIR/build
    pushd $OPENCV_SRC_DIR/build > /dev/null
    cmake \
        -D CMAKE_BUILD_TYPE="RELEASE" \
        -D CMAKE_INSTALL_PREFIX="/usr/local" \
        -D OPENCV_EXTRA_MODULES_PATH="$OPENCV_CONTRIB_SRC_DIR/modules" \
        $OPENCV_SRC_DIR
    make -j3
    popd > /dev/null
}

install_opencv() {
    pushd $OPENCV_SRC_DIR/build > /dev/null
    sudo make install
    sudo ldconfig
    popd > /dev/null
}

clean_opencv() {
    xargs sudo rm < $OPENCV_SRC_DIR/build/install_manifest.txt
    rm -rf $OPENCV_DIR
}

install_dependencies
download_opencv
compile_opencv
install_opencv
#clean_opencv
