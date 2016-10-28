Running the mobile testkit tests

To run all the tests the following dependencies need to be satisfied

### test_liteserv_android.py
- Running an Android device or emulator that is reachable by ip (--android-host)

### test_liteserv_ios.py
- Running an iOS device or emulator that is reachable by ip (--ios-host)

### test_liteserv_net_msft.py
- A running Windows machine with ansible configured (--net-msft-host)
- export LITESERV_MSFT_HOST_USER=<rdp_user_name>
- export LITESERV_MSFT_HOST_PASSWORD=<rdp_user_password>

## Running the tests (Execute from root of repo)
```
pytest -s \
       --android-version=1.3.1-30 \
       --android-host=192.168.0.7 \
       --ios-version=1.3.1-6 \
       --ios-host=192.168.0.19 \
       --macosx-version=1.3.1-6
       --net-version=1.3.1-30 \
       --net-msft-host=192.168.0.16 \
       framework_tests/
```
