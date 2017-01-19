## Executing listener/shared/client_sg functional tests

The client_sg functional test test a client LiteServ application with a Sync Gateway backed by a Couchbase Server

- The client LiteServ application can be run with the following platforms
    - android
    - ios
    - macosx
    - net-mono
    - net-msft

- Using one of the following storage engines
    - SQLite
    - SQLCipher
    - ForestDB
    - ForestDB+Encryption

- Sync Gateway can be run in the following modes
    - cc = channel cache
    - di = distributed index (SG Accel)

These commands must be run from the root directory of the mobile-testkit repo.

### Running the tests for Mac OSX using Sync Gateway in channel cache mode

```
pytest -s \
    --liteserv-platform=macosx \
    --liteserv-version=1.4-20 \
    --liteserv-host=localhost \
    --liteserv-port=5000 \
    --liteserv-storage-engine=SQLite \
    --sync-gateway-version=1.4-16 \
    --sync-gateway-mode=cc \ 
    --server-version=4.6.0-3572 \
    testsuites/listener/shared/client_sg/
```

### Running the tests for Android using Sync Gateway in distributed index mode

```
pytest -s \
    --liteserv-platform=android \
    --liteserv-version=1.4-20 \
    --liteserv-host=<android-device-ip> \
    --liteserv-port=5000 \
    --liteserv-storage-engine=SQLite \
    --sync-gateway-version=1.4-16 \
    --sync-gateway-mode=cc \ 
    --server-version=4.6.0-3572 \
    testsuites/listener/shared/client_sg/
```

### Running a single test for Mono using Sync Gateway in distributed index mode

```
pytest -s \
    --liteserv-platform=net-mono \
    --liteserv-version=1.4-20 \
    --liteserv-host=localhost \
    --liteserv-port=5000 \
    --liteserv-storage-engine=SQLite \
    --sync-gateway-version=1.4-16 \
    --sync-gateway-mode=cc \ 
    --server-version=4.6.0-3572 \
    -k "test_auto_prune_listener_keeps_conflicts_sanity" \
    testsuites/listener/shared/client_sg/
```