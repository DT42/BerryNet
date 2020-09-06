#!/usr/bin/python3
"""This script will block until the specified file appears or the timeout
   expires. The first argument is the timeout in seconds. The second argument
   is the filepath."""
import os
import time
import sys


def logging(*args):
    """add a prefix to print() output"""
    print("wait_for_warmup:", ' '.join(args), flush=True)


def wait_for_warmup(warmup_file, max_wait_sec):
    """wait for warmup_file to appear until max_wait_sec timeout"""
    counter = 0
    msg = warmup_file
    while True:
        if os.access(warmup_file, os.F_OK):
            msg += " is detected!"
            break
        if counter >= max_wait_sec:
            msg += " didn't show up!"
            break
        counter += 1
        time.sleep(1)
    msg += " Time elapsed = %d" % counter
    logging(msg)


def main():
    """Program starts here"""
    warmup_file = '/tmp/pipeline.warmup.done'
    max_wait_sec = 60

    for i in range(len(sys.argv)):
        arg = sys.argv[i]
        if i == 1:
            max_wait_sec = int(arg)
        elif i == 2:
            warmup_file = arg
    if max_wait_sec > 0:
        wait_for_warmup(warmup_file, max_wait_sec)


if __name__ == '__main__':
    main()
