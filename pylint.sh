RUNPYLINT="pylint -E"

echo "$RUNPYLINT libraries/*.py"
$RUNPYLINT libraries/*.py

echo "$RUNPYLINT libraries/testkit/*.py"
$RUNPYLINT libraries/testkit/*.py

echo "$RUNPYLINT libraries/provision/*.py"
$RUNPYLINT libraries/provision/*.py

echo "$RUNPYLINT libraries/data/*.py"
$RUNPYLINT libraries/data/*.py

echo "$RUNPYLINT libraries/keywords/*.py"
$RUNPYLINT libraries/keywords/*.py

echo "$RUNPYLINT libraries/utilities/*.py"
$RUNPYLINT libraries/utilities/*.py

echo "$RUNPYLINT libraries/testsuites/*.py"
$RUNPYLINT libraries/testsuites/*.py

echo "$RUNPYLINT libraries/testsuites/android/listener/*.py"
$RUNPYLINT libraries/testsuites/android/listener/*.py

echo "$RUNPYLINT libraries/testsuites/listener/shared/client_client/*.py"
$RUNPYLINT libraries/testsuites/listener/shared/client_client/*.py

echo "$RUNPYLINT libraries/testsuites/listener/shared/client_sg/*.py"
$RUNPYLINT libraries/testsuites/listener/shared/client_sg/*.py

echo "$RUNPYLINT libraries/testsuites/syncgateway/*.py"
$RUNPYLINT libraries/testsuites/syncgateway/*.py

echo "$RUNPYLINT libraries/testsuites/syncgateway/*.py"
$RUNPYLINT libraries/testsuites/syncgateway/*.py

echo "$RUNPYLINT testsuites/syncgateway/functional/*.py"
$RUNPYLINT testsuites/syncgateway/functional/*.py

echo "$RUNPYLINT testsuites/syncgateway/functional/shared/*.py"
$RUNPYLINT testsuites/syncgateway/functional/shared/*.py

echo "$RUNPYLINT testsuites/syncgateway/performance/*.py"
$RUNPYLINT testsuites/syncgateway/performance/*.py


