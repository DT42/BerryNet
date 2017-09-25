#!/bin/bash

SNAPSHOT_DIR="$1"
MODEL_DIR="/var/lib/dlmodels/tinyyolo-20170816"

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
    -c $MODEL_DIR/assets/tiny-yolo.cfg \
    -w $MODEL_DIR/tiny-yolo.weights \
    $SNAPSHOT_DIR
