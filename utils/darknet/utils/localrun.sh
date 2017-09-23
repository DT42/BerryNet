#!/bin/bash

SNAPSHOT_DIR="$1"
DARKFLOW_DIR="/usr/local/berrynet/inference/darkflow"

usage() {
    echo "Usage: <darknet-root>/utils/local_debug.sh SNAPSHOT_DIR"
    exit 1
}


if [ "$SNAPSHOT_DIR" = "" ]; then
    usage
else
    echo "SNAPSHOT_DIR: $SNAPSHOT_DIR"
fi

python detectord.py \
    -c $DARKFLOW_DIR/cfg/tiny-yolo.cfg \
    -w $DARKFLOW_DIR/bin/tiny-yolo.weights \
    $SNAPSHOT_DIR
