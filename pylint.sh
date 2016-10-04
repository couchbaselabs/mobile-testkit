#!/usr/bin/env bash
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

echo "$RUNPYLINT testsuites/*.py"
$RUNPYLINT testsuites/*.py

echo "$RUNPYLINT testsuites/android/listener/*.py"
$RUNPYLINT testsuites/android/listener/*.py

echo "$RUNPYLINT testsuites/listener/shared/client_client/*.py"
$RUNPYLINT testsuites/listener/shared/client_client/*.py

echo "$RUNPYLINT testsuites/listener/shared/client_sg/*.py"
$RUNPYLINT testsuites/listener/shared/client_sg/*.py

echo "$RUNPYLINT testsuites/syncgateway/*.py"
$RUNPYLINT testsuites/syncgateway/*.py

echo "$RUNPYLINT testsuites/syncgateway/functional/shared/*.py"
$RUNPYLINT testsuites/syncgateway/functional/shared/*.py

echo "$RUNPYLINT testsuites/syncgateway/performance/*.py"
$RUNPYLINT testsuites/syncgateway/performance/*.py

echo "$RUNPYLINT testsuites/syncgateway/functional/**/*.py"
$RUNPYLINT testsuites/syncgateway/functional/**/*.py

