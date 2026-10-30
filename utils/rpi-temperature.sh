#!/bin/bash
# Display CPU & GPU temperature for degrees C.
#
# Thanks badfur and yuusou for writing the script.
# https://www.raspberrypi.org/forums/viewtopic.php?t=34994

cpuTemp0=$(cat /sys/class/thermal/thermal_zone0/temp)
cpuTemp1=$(($cpuTemp0/1000))
cpuTemp2=$(($cpuTemp0/100))
cpuTempM=$(($cpuTemp2 % $cpuTemp1))

gpuTemp0=$(vcgencmd measure_temp)
gpuTemp0=${gpuTemp0//\'/º}
gpuTemp0=${gpuTemp0//temp=/}

echo CPU Temp: $cpuTemp1"."$cpuTempM"ºC"
echo GPU Temp: $gpuTemp0
