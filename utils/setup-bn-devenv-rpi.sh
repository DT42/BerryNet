#!/bin/bash
# Setup BerryNet devenv on RPi3.

install_system_dependencies() {
    sudo apt-get update
    sudo apt-get install -y \
        curl \
        fswebcam \
        git \
        imagemagick \
        libkrb5-dev \
        libyaml-dev \
        libzmq3-dev \
        lsb-release \
        mongodb \
        mosquitto \
        mosquitto-clients \
        python3-dev \
        python3-pip \
        supervisor \
        wget
    sudo service mongodb start
    sudo -H pip3 install --timeout 60 cython
    sudo -H pip3 install --timeout 60 logzero
    sudo -H pip3 install --timeout 60 paho-mqtt
    sudo -H pip3 install --timeout 60 watchdog
}

install_berrynet_repository() {
    sudo apt update
    sudo apt install -y dirmngr
    pushd /etc/apt/sources.list.d
    sudo wget https://raw.githubusercontent.com/DT42/BerryNet/master/config/berrynet.list
    popd
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv C0C4CC4C
    sudo apt update
}

install_opencv() {
    sudo apt install -y python3-opencv
}

main() {
    install_system_dependencies
    install_berrynet_repository
    install_opencv
}

main
