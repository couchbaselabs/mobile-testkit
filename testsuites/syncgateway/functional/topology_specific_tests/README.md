## Executing sync_gateway functional tests

You can run any of the sync_gateway tests in the 'topology_specific_tests/' directory in channel cache mode ('cc') or using sg_accel in distributed index ('di') mode, except the multiple_accels tests.

### Topology requirements

#### load_balancer/test_load_balancer.py
- 1 loadbalancer, 2 sync_gateways, 1 couchbase_server (cc)
- 1 loadbalancer, 2 sync_gateways, 1 sg_accel, 1 couchbase_server (di)

#### multiple_accels/test_multiple_accels.py
- 1 sync_gateways, 3 sg_accels 1 couchbase_server (di only)

#### multiple_servers/multiple_servers.py
- 1 sync_gateways, 3 couchbase_servers (cc)
- 1 sync_gateways, 1 sg_accel, 3 couchbase_servers (di)

#### multiple_sync_gateways/test_multiple_sync_gateways.py
- 2 sync_gateways, 1 couchbase_servers (cc)
- 2 sync_gateways, 1 sg_accel, 1 couchbase_servers (di)

These commands must be run from the root directory of the repo.

### Run all the tests in distributed index mode

```
pytest  -s \
        --mode=di \
        --server-version=4.5.1 \
        --sync-gateway-version=1.3.1-16 \
        testsuites/syncgateway/functional/topology_specific_tests/
```

### Run all the tests in channel cache mode

```
pytest  -s \
        --mode=cc \
        --server-version=4.5.1 \
        --sync-gateway-version=1.3.1-16 \
        testsuites/syncgateway/functional/topology_specific_tests/
```

### Run a the test in channel cache mode matching a -k pattern

```
pytest  -s \
        --mode=cc \
        --server-version=4.5.1 \
        --sync-gateway-version=1.3.1-16 \
        -k "test_load_balance_sanity" \
        testsuites/syncgateway/functional/topology_specific_tests/
```

### Run all the tests in a module (ex. test_multiple_servers.py)

```
pytest  -s \
        --mode=di \
        --server-version=4.5.1 \
        --sync-gateway-version=1.3.1-16 \
        testsuites/syncgateway/functional/topology_specific_tests/muliple_servers/test_muliple_servers.py
```

### Run a the test in channel cache mode matching a -k pattern and skipping the cluster provisioning. 
### WARNING! Only provide --skip-provisioning if you know what you are doing. You could end up running a test in an unexpected state. 


```
pytest  -s \
        --mode=cc \
        --skip-provisioning \
        --server-version=4.5.0 \
        --sync-gateway-version=1.3.1-16 \
        -k "test_load_balance_sanity" \
        testsuites/syncgateway/functional/topology_specific_tests/
```