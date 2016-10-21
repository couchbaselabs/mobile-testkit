def pytest_addoption(parser):
    parser.addoption("--android-host", action="store", help="host to target for android unit tests")
    parser.addoption("--net-msft-host", action="store", help="host to target for net-msft unit tests")
