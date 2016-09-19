
def pytest_addoption(parser):
    parser.addoption("--liteserv-one-platform", action="store", help="liteserv-one-platform: the platform to assign to the first liteserv")
    parser.addoption("--liteserv-one-version", action="store", help="liteserv-one-version: the version to download / install for the first liteserv")
    parser.addoption("--liteserv-one-host", action="store", help="liteserv-one-host: the host to start to the first liteserv on")
    parser.addoption("--liteserv-one-port", action="store", help="liteserv-one-port: the port to assign to the first liteserv")
    parser.addoption("--liteserv-one-storage-engine", action="store", help="liteserv-one-storage-engine: the storage engine to use with the first liteserv")
    parser.addoption("--liteserv-two-platform", action="store", help="liteserv-two-platform: the platform to assign to the first liteserv")
    parser.addoption("--liteserv-two-version", action="store", help="liteserv-two-version: the version to download / install for the first liteserv")
    parser.addoption("--liteserv-two-host", action="store", help="liteserv-two-host: the host to start to the first liteserv on")
    parser.addoption("--liteserv-two-port", action="store", help="liteserv-two-port: the port to assign to the first liteserv")
    parser.addoption("--liteserv-two-storage-engine", action="store", help="liteserv-two-storage-engine: the storage engine to use with the first liteserv")




