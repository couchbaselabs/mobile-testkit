def pytest_addoption(parser):
    parser.addoption("--android-host", action="store", help="host to target for android unit tests")
    parser.addoption("--ios-host", action="store", help="host to target for ios unit tests")
    parser.addoption("--net-msft-host", action="store", help="host to target for net-msft unit tests")

    parser.addoption("--android-version", action="store", help="version of Android to target with unit tests")
    parser.addoption("--ios-version", action="store", help="version of iOS to target with unit tests")
    parser.addoption("--macosx-version", action="store", help="version of Mac OSX to target with unit tests")
    parser.addoption("--net-version", action="store", help="version of Mac OSX to target with unit tests")
