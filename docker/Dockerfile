# We start from Debian Stretch. Can be rebase to Raspbian because they are
# similar
FROM debian:stretch
LABEL maintainer="dev@dt42.io"
LABEL project="Berrynet"
LABEL version="3.5.1"

# Update apt
RUN apt-get update

# Install dependencies
RUN apt-get install -y git sudo wget lsb-release software-properties-common

# Install build-essential
RUN apt-get install -y build-essential

# Install systemd
RUN apt-get install -y systemd systemd-sysv

# Install python
RUN apt-get install -y python python3

# Install BerryNet
RUN git clone https://github.com/DT42/BerryNet.git
RUN cd BerryNet; ./configure

