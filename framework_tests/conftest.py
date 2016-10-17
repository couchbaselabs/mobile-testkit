def pytest_addoption(parser):
    parser.addoption("--android-host", action="store", help="host to target for android unit tests")
