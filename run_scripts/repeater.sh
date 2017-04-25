#!/bin/bash

while true
do
	pytest --skip-provisioning --pdb -s --mode=di --server-version=5.0.0-2703 --sync-gateway-version=1.4.1-3 -k "test_user_views_sanity[user_views/user_views]" testsuites/syncgateway/functional/tests
done