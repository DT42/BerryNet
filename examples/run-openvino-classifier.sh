#!/bin/bash
#
# Copyright 2019 DT42
#
# This file is part of BerryNet.
#
# BerryNet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BerryNet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BerryNet.  If not, see <http://www.gnu.org/licenses/>.

# Example: Run OpenVINO classifier on general x86 notebook.
#
#   For more details, please refer to Medium XXX.

set -e

SCRIPT_NAME=$0
COMMAND=$1


usage() {
    echo -e "Usage:\n\t$ bash $SCRIPT_NAME start|stop"
    exit 1
}

kill_script() {
    local script_name=$1
    local process_id=$(ps aux | grep $script_name | grep Sl | awk '{print $2}')
    echo "Terminate $script_name (pid $process_id)"
    kill -9 $process_id
}

example_start() {
    # Run Freeboard
    echo -n "Run Dashboard..."
    pushd /usr/lib/berrynet/dashboard > /dev/null
    nodejs server.js >> /tmp/berrynet-example.log &
    popd > /dev/null
    echo "done"

    # Run OpenVINO classifier
    echo -n "Run OpenVINO classifier..."
    MODELPKG_DIRPATH="/usr/share/dlmodels/mobilenet-1.0-224-openvino-1"

    source /opt/intel/computer_vision_sdk_2018.5.445/bin/setupvars.sh
    sleep 1
    python3 /usr/lib/python3/dist-packages/berrynet/service/openvino_service.py \
        --model $MODELPKG_DIRPATH/mobilenet_v1_1.0_224_frozen.xml \
        --label $MODELPKG_DIRPATH/imagenet_slim_labels.txt \
        --service_name ovclassifier \
        --num_top_predictions 3 \
        --debug >> /tmp/berrynet-example.log 2>&1 &
    echo "done"

    # Run camera client
    echo -n "Run Camera..."
    sleep 1
    python3 /usr/lib/python3/dist-packages/berrynet/client/camera.py \
        --fps 5 >> /tmp/berrynet-example.log 2>&1 &
    echo "done"
}

example_stop() {
    kill_script "camera.py"
    kill_script "openvino_service.py"
    kill_script "server.js"
}

main() {
    local cmd=$1
    if [ "$cmd" == "start" ]; then
        example_start
    elif [ "$cmd" == "stop" ]; then
        example_stop
    else
        usage
    fi
}

main $COMMAND
