#!/bin/sh
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

# Generate BerryNet release image from a SD card.

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <device>"
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

IMAGE_FILENAME=$CTIME_YY-$CTIME_MM-$CTIME_DD-raspbian-stretch-berrynet

echo "Creating image ${IMAGE_FILENAME}.img"
sudo dd if="$DEVICE" of="$IMAGE_FILENAME".img bs=512

echo "Compressing image to ${IMAGE_FILENAME}.zip"
zip "$IMAGE_FILENAME".zip "$IMAGE_FILENAME".img

echo "BerryNet release image has been created."
echo "Now you can upload the image to the release repository."
