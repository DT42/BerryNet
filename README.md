<p align="center"><a href="http://berrynet.org" target="_blank" rel="noopener noreferrer"><img width="50%" src="https://user-images.githubusercontent.com/292790/33802809-e4726cf8-dd45-11e7-8a64-fdc4c3ff9310.png" alt="BerryNet Logo"></a></p>
<h2  align="center">Deep Learning Gateway on Raspberry Pi</h2>

![Docker Image CI](https://github.com/DT42/BerryNet/workflows/Docker%20Image%20CI/badge.svg)

[Supporting BerryNet](https://dt42.io/berrynet-doc/community/donation/)

* [One-time donation via PayPal](https://paypal.me/berrynet).
* [One-time donation via crypto-currencies](https://dt42.io/berrynet-doc/community/donation/).
* [Become a backer or sponsor on Open Collective](https://opencollective.com/berrynet).

## Introduction

This project turns Raspberry Pi into an intelligent gateway with deep learning running on it. No internet connection is required, everything is done locally on the edge device itself. Further, multiple edge devices can create a distributed AIoT network.

At DT42, we believe that bringing deep learning to edge devices is the trend towards the future. It not only saves costs of data transmission and storage but also makes devices able to respond according to the events shown in the images or videos without connecting to the cloud.

![Figure 1](https://user-images.githubusercontent.com/292790/45943626-a3d28b80-c019-11e8-829c-5eb6afd3faa4.png)

<p align="center">Figure 1: BerryNet architecture</p>

Figure 1 shows the software architecture of the project, we use Python, MQTT and AI engines to analyze images or video frames with deep learning. The AI engines run models with [LiteRT](https://ai.google.dev/edge/litert) or [ONNX Runtime](https://onnxruntime.ai/). There are two types of AI engines, the classification engine (with MobileNet [[1]](https://arxiv.org/pdf/1704.04861.pdf) models) and the object detection engine (with SSD MobileNet [[2]](https://arxiv.org/pdf/1512.02325.pdf) or YOLOv4 [[3]](https://arxiv.org/pdf/2004.10934.pdf) models). Figure 2 shows the differences between classification and object detection.

![Figure 2](https://cloud.githubusercontent.com/assets/292790/25520013/d9497738-2c2c-11e7-9693-3840647f2e1e.jpg)

<p align="center">Figure 2: Classification vs detection</p>

One of the application of this intelligent gateway is to use the camera to monitor the place you care about. For example, Figure 3 shows the analyzed results from the camera hosted in the DT42 office. The frames were captured by the IP camera and they were submitted into the AI engine. The output from the AI engine will be shown in the dashboard. We are working on the Email and IM notification so you can get a notification when there is a dog coming into the meeting area with the next release.

![Figure 3](https://cloud.githubusercontent.com/assets/292790/25498294/0ab79976-2bba-11e7-9114-46e328d15a18.gif)

<p align="center">Figure 3: Object detection result example</p>

## Supported Hardware

* Raspberry Pi 5 or Raspberry Pi 4, including Raspberry Pi 500/400 and Compute Module 5/4
* 64-bit Raspberry Pi OS Bookworm or Trixie
* Raspberry Pi camera module, USB camera, or IP camera


## Installation

Install BerryNet from source on Raspberry Pi OS:

```
$ git clone https://github.com/DT42/BerryNet.git
$ cd BerryNet
$ ./configure
```

`configure` installs BerryNet into `/opt/berrynet/venv` (the `bn_*` commands are linked to `/usr/local/bin`), downloads the object detection model into `/usr/share/dlmodels`, and starts the default application with supervisor. The default application runs LiteRT, run `BERRYNET_ENGINE=onnx ./configure` to use ONNX Runtime instead.

You can also build and run a Docker image:

```
$ docker build -t berrynet -f docker/Dockerfile .
$ docker run -p 1883:1883 -p 3000:3000 -p 8080:8080 --device /dev/video0 berrynet
```

### AI Engines and Models

BerryNet runs models with LiteRT (`bn_litert`) or ONNX Runtime (`bn_onnx`). `bn_model` downloads model packages and verifies their checksums:

```
# Show model packages which can be installed
$ bn_model available

# Install an ONNX classification model
$ sudo bn_model install mobilenet-v2-imagenet-onnx

# Run engines with model packages
$ bn_litert --service detector --model_package ssd-mobilenet-v1-coco-litert
$ bn_onnx --service classifier --model_package mobilenet-v2-imagenet-onnx
```

You can also give model and label files with `--model` and `--label`. An engine publishes results to the MQTT topic `berrynet/engine/<service_name>/result`, and the service name is `<engine><service>` by default, e.g. `litertdetector` or `onnxclassifier`.

### Development Environment

The Python development environment is managed by [uv](https://docs.astral.sh/uv/) and supports Python 3.11 or newer (tested up to 3.15).

```
$ uv sync --all-extras

# Download the models and images for the tests
$ BERRYNET_MODEL_DIR=models uv run python -m tests.data

$ BERRYNET_MODEL_DIR=models uv run python -m unittest
```

LiteRT and ONNX Runtime do not publish wheels for Python 3.15 yet, so on Python 3.15 their extras install nothing and the engine tests are skipped.


## Start and Stop BerryNet

BerryNet performs an AIoT application by connecting independent components together. Component types include but not limited to AI engine, I/O processor, data processor (algorithm), or data collector.

We recommend to manage BerryNet componetns by [supervisor](http://supervisord.org/), but you can also run BerryNet components manually. You can manage BerryNet via `supervisorctl`:

    ```
    # Check status of BerryNet components
    $ sudo supervisorctl status all

    # Stop Camera client
    $ sudo supervisorctl stop camera

    # Restart all components
    $ sudo supervisorctl restart all

    # Show last stderr logs of camera client
    $ sudo supervisorctl tail camera stderr
    ```

For more possibilities of supervisorctl, please refer to the [official tutorial](http://supervisord.org/running.html#running-supervisorctl).

The default application has three components:

* Camera client to provide input images
* Object detection engine (LiteRT with SSD MobileNet) to find type and position of the detected objects in an image
* Dashboard to display the detection results

You will learn how to configure or change the components in the [Configuration](#configuration) section.


## Dashboard: Freeboard

### Open Freeboard on RPi (with touch screen)

Freeboard is a web-based dashboard. Here are the steps to show the detection result image and text on Freeboard:

* 1: Enter `http://127.0.0.1:8080/#source=dashboard-litertdetector.json` in browser's URL bar, and press enter
* 2: Wait for seconds, you should see the inference result image and text on Freeboard

If the default application runs ONNX Runtime, use `dashboard-onnxdetector.json` instead of `dashboard-litertdetector.json` here and below.

### Open Freeboard on another computer

Assuming that you have two devices:

* Device A with IP `192.168.1.42`, BerryNet default application runs on it
* Device B with IP `192.168.1.43`, you want to open Freeboard and see the detection result on it

Here are the steps:

* 1: Enter `http://192.168.1.42:8080` in browser's URL bar, and press enter
* 2: [Download](http://192.168.1.42:8080/dashboard-litertdetector.json) the Freeboard configuration for default application, `dashboard-litertdetector.json`
* 3: Replace all the `localhost` to `192.168.1.42` in `dashboard-litertdetector.json`
* 4: Click `LOAD FREEBOARD`, and select the modified `dashboard-litertdetector.json`
* 5: Wait for seconds, you should see the inference result image and text on Freeboard

For more details about dashboard configuration (e.g. how to add widgets), please refer to [Freeboard project](https://github.com/Freeboard/freeboard).


## Enable Data Collector

You might want to store the snapshot and inference results for data analysis.

To run BerryNet data collector manually, you can run the command below:

```
$ bn_data_collector --topic-config <topic-config-filepath> --data-dirpath <result-dirpath>
```

The topic config indicates what MQTT topic the data collector will listen, and what handler will be triggered. Here is a topic config example:

```
{
    "berrynet/engine/litertdetector/result": "self.update"
}
```

The inference result image and text will be saved into the indicated result directory.


## Configuration

The default supervisor config is at `/etc/supervisor/conf.d/berrynet-litert.conf`, or `berrynet-onnx.conf` with `BERRYNET_ENGINE=onnx`. To write your own supervisor config, you can refer to [here](https://github.com/DT42/BerryNet/tree/master/config/supervisor/conf.d) for more example supervisor configs of BerryNet

The MQTT broker (Mosquitto) accepts clients without authentication on port 1883, and on port 3000 over websockets for the dashboard, so that BerryNet components on other devices can connect. On an untrusted network, restrict these ports with a firewall or set up [Mosquitto authentication](https://mosquitto.org/documentation/authentication-methods/).

### Camera Client

BerryNet camera client can run in two modes: stream or file. In stream mode, Raspberry Pi camera module, USB camera and IP camera can be supported, and input frame rate (FPS) can be changed on demand (default is 1). In file mode, user can indicate filepath as input source.

To run camera client in stream mode:

```
# USB camera /dev/video0
$ bn_camera --fps 5

# Raspberry Pi camera module, read through rpicam-vid
$ bn_camera --stream-src picamera --fps 5

# IP camera
$ bn_camera --stream-src rtsp://<ip-address>/<stream-path> --fps 5
```

`configure` uses the Raspberry Pi camera module in the default application if one is connected.

To run camera client in file mode:

```
$ bn_camera --mode file --filepath <image-filepath>
```


## Discussion

Please refer to the [Slack](https://join.slack.com/t/berrynet/shared_invite/enQtODg5MjA0ODExMjUzLWIwMDNkZWExZGE2Njc1ZDljMmFiOWJlZDdmZmEwYmQ4YTJiNzg2NDc1NTJhMDVkMzhmNzA3YTU0ZTc4M2JiNTE) or [Telegram Group](https://t.me/berrynetdev) for questions, suggestions, or any idea discussion.
