#!/bin/sh

if [ $# -lt 1 ]; then
    echo $0 '<device>'
    exit 0
fi

DEVICE="$1"

if [ ! -b "$DEVICE" ]; then
    echo "$DEVICE" "does not exist"
    exit 1
fi

echo $DEVICE

CTIME_YY=`date '+%Y'`
CTIME_MM=`date '+%m'`
CTIME_DD=`date '+%d'`

IMAGE_FILENAME=$CTIME_YY-$CTIME_MM-$CTIME_DD-raspbian-stretch-full-berrynet

sudo dd if="$DEVICE" of="$IMAGE_FILENAME".img bs=512

zip "$IMAGE_FILENAME".zip "$IMAGE_FILENAME".img
