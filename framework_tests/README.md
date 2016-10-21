Running the framework unit tests

To run all the tests the following dependencies need to be satisfied

### test_liteserv_android.py
- Running an Android device or emulator that is reachible by ip (--android-host)

### test_liteserv_net_msft.py
- A running Windows machine with ansible configured (--net-msft-host)
- export LITESERV_MSFT_HOST_USER=<rdp_user_name>
- export LITESERV_MSFT_HOST_PASSWORD=<rdp_user_password>

## Running the tests (Execute from root of repo)
pytest --android-host=192.168.0.7 --net-msft-host=192.168.0.16 framework_tests/
