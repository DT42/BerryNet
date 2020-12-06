# We start from Debian Buster. Can be rebase to Raspbian because they are
# similar
FROM ubuntu:focal
LABEL maintainer="dev@dt42.io"
LABEL project="Berrynet"
LABEL version="3.7.0"

ENV TZ=Europe/London

# Update apt
RUN apt-get update

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install dependencies
RUN apt-get install -y git sudo wget lsb-release software-properties-common

# Install build-essential
RUN apt-get install -y build-essential curl

# Install systemd
RUN apt-get install -y systemd systemd-sysv

# Install python
RUN apt-get install -y python3 python3-dev

# Install python libs
RUN apt-get install -y python3-wheel python3-setuptools python3-pip
RUN apt-get install -y python3-paho-mqtt python3-logzero python3-astor
RUN apt-get install -y python3-opengl python3-six python3-grpcio
RUN apt-get install -y python3-keras-applications python3-keras-preprocessing
RUN apt-get install -y python3-protobuf python3-termcolor python3-numpy

# Install daemons
RUN apt-get install -y mosquitto mosquitto-clients
RUN apt-get install -y apache2

# Install tensorflow
RUN pip3 install tensorflow

# Install BerryNet
RUN git clone https://github.com/DT42/BerryNet.git
RUN cd BerryNet; ./configure
