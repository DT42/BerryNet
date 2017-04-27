#!/usr/bin/python

import json
import subprocess


def loadConfig():
    cmd = ("node -e \"const config = "
        "require('../config'); console.log(JSON.stringify(config));\"")
    config = json.loads(subprocess.check_output(cmd, shell=True))
    print(config)


if __name__ == '__main__':
    loadConfig()
