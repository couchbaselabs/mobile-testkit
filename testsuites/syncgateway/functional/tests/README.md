## Executing sync_gateway functional tests

You can run any of the sync_gateway tests in the 'test/' directory in channel cache mode ('cc') or using sg_accel in distributed index ('di') mode.

These commands must be run from the root directory of the repo.

### Run all the tests in distributed index mode

```
pytest  -s \
        --mode=di \
        --server-version=4.5.0 \
        --sync-gateway-version=1.3.1-16 \
        testsuites/syncgateway/functional/tests/
```

### Run all the tests in channel cache mode

```
pytest  -s \
        --mode=cc \
        --server-version=4.5.0 \
        --sync-gateway-version=1.3.1-16 \
        testsuites/syncgateway/functional/tests/
```

### Run a the test in channel cache mode matching a -k pattern

```
pytest  -s \
        --mode=cc \
        --server-version=4.5.0 \
        --sync-gateway-version=1.3.1-16 \
        -k "test_online_to_offline_check_503" \
        testsuites/syncgateway/functional/tests/
```

### Run all the tests in a module (ex. test_db_online_offline.py)

```
pytest  -s \
        --mode=di \
        --server-version=4.5.0 \
        --sync-gateway-version=1.4.0-20 \
        testsuites/syncgateway/functional/tests/test_db_online_offline.py
```

### Run a the test in channel cache mode matching a -k pattern and skipping the cluster provisioning. 
### WARNING! Only provide --skip-provisioning if you know what you are doing. You could end up running a test in an unexpected state. 


```
pytest  -s \
        --mode=cc \
        --skip-provisioning \
        --server-version=4.5.0 \
        --sync-gateway-version=1.3.1-16 \
        -k "test_online_to_offline_check_503" \
        testsuites/syncgateway/functional/tests/
```