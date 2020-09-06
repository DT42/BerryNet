#!/bin/bash
#
# Manually run BerryNet pipeline powered by Dyda.
#
# Testing input & output client commands
#
#     $ bn_dashboard --topic berrynet/engine/pipeline/result --no-full-screen --no-decoration --debug
#     $ bn_camera --mode file --filepath <image-filepath>
#
# Verified on Dyda v1.41.0

dyda_source_dir="$HOME/codes/dyda"
berrynet_source_dir="$HOME/codes/BerryNet"
dyda_config_system_dir="/etc/dyda/pipelines/configs"
dyda_config_local_dir="$dyda_source_dir/dyda/pipelines/configs"
bnpipeline_dir="$berrynet_source_dir/bndyda/bndyda"

# AIKEA (TFLite)
config="$dyda_config_system_dir/object_detection_and_tracking_aikea.config"

# OpenVINO detection
#config="/home/bafu/codes/bntrainer/bntrainer/object_counting_mobilenet-ssd_cpu.config"

# Main
python3 $bnpipeline_dir/bnpipeline.py --pipeline-config $config --disable-warmup -vvv --debug
