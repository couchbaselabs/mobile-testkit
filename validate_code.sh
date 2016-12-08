#!/usr/bin/env bash

flake8

RUNPYLINT="pylint -E"

echo "$RUNPYLINT keywords/*.py"
$RUNPYLINT keywords/*.py

echo "$RUNPYLINT libraries/*.py"
$RUNPYLINT libraries/*.py

echo "$RUNPYLINT libraries/data/*.py"
$RUNPYLINT libraries/data/*.py

echo "$RUNPYLINT libraries/provision/*.py"
$RUNPYLINT libraries/provision/*.py

echo "$RUNPYLINT libraries/testkit/*.py"
$RUNPYLINT libraries/testkit/*.py

echo "$RUNPYLINT libraries/utilities/*.py"
$RUNPYLINT libraries/utilities/*.py

echo "$RUNPYLINT testsuites/android/listener/*.py"
$RUNPYLINT testsuites/android/listener/*.py

echo "$RUNPYLINT testsuites/listener/shared/client_client/*.py"
$RUNPYLINT testsuites/listener/shared/client_client/*.py

echo "$RUNPYLINT testsuites/listener/shared/client_sg/*.py"
$RUNPYLINT testsuites/listener/shared/client_sg/*.py

echo "$RUNPYLINT testsuites/syncgateway/performance/*.py"
$RUNPYLINT testsuites/syncgateway/performance/*.py

# testsuites/syncgateway/functional/tests/
echo "$RUNPYLINT testsuites/syncgateway/functional/tests/*.py"
$RUNPYLINT testsuites/syncgateway/functional/tests/*.py

# testsuites/syncgateway/functional/topology_specific_tests/*
echo "$RUNPYLINT testsuites/syncgateway/functional/topology_specific_tests/**/*.py"
$RUNPYLINT testsuites/syncgateway/functional/topology_specific_tests/**/*.py

