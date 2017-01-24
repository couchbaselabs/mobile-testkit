## Executing listener/shared/client_client functional tests

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

These commands must be run from the root directory of the mobile-testkit repo.

### Running the client_client tests for Mac OSX (SQLite) with .NET mono (ForestDB)

```
pytest  -s \
        --liteserv-one-platform=android \
        --liteserv-one-version=1.3.1-30 \
        --liteserv-one-host=<android-device-ip> \
        --liteserv-one-port=5000 \
        --liteserv-one-storage-engine=SQLite \
        --liteserv-two-platform=net \
        --liteserv-two-version=1.3.1-13 \
        --liteserv-two-host=<net-device-ip> \
        --liteserv-two-port=51000 \
        --liteserv-two-storage-engine=ForestDB \
        testsuites/listener/shared/client_client/
```