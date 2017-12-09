#!/bin/bash
# Install Movidius neural compute stick dependencies.

sudo apt update
sudo apt install -y ncsdk python-mvnc python3-mvnc inception-movidius
sudo cp inference/classify_movidius_server.py /usr/local/berrynet/inference/
sudo cp systemd/classify_movidius_server.service /etc/systemd/system/
