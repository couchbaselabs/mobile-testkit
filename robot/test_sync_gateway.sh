#!/usr/bin/env bash

# TODO python libraries/install_deps.py # target the union vm pool

robot -b debug.txt testsuites/syncgateway/functional/1sg_1cbs.robot
robot -b debug.txt testsuites/syncgateway/functional/2sg_1cbs.robot