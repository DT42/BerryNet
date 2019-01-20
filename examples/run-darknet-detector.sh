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

# Example: Run Darknet detector.

set -e

SCRIPT_NAME=$0
COMMAND=$1


usage() {
    echo -e "Usage:\n\t$ bash $SCRIPT_NAME start|stop"
    exit 1
}

kill_script() {
    local script_name=$1
    local ext=${script_name##*.}
    local interpreter=""
    if [ "$ext" == "py" ]; then
        interpreter="python3"
    elif [ "$ext" == "js" ]; then
        interpreter="nodejs"
    else
        interpreter="bash"
    fi
    local process_id=$(ps aux | grep $script_name | grep $interpreter | awk '{print $2}')
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

    # Run Darknet detector
    echo -n "Run Darknet detector..."
    sleep 1
    python3 /usr/lib/python3/dist-packages/berrynet/service/darknet_service.py \
        --service_name detector \
        --model_package tinyyolovoc-20170816 \
        --draw \
        --debug >> /tmp/berrynet-example.log 2>&1 &
    echo "done"

    # Run camera client
    echo -n "Run Camera..."
    sleep 1
    python3 /usr/lib/python3/dist-packages/berrynet/client/camera.py \
        --fps 0.5 >> /tmp/berrynet-example.log 2>&1 &
    echo "done"
}

example_stop() {
    kill_script "camera.py"
    kill_script "darknet_service.py"
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
