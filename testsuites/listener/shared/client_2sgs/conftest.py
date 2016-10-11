# Add custom arguments for executing tests in this directory
def pytest_addoption(parser):
    parser.addoption("--liteserv-platform", action="store", help="liteserv-platform: the platform to assign to the liteserv")
    parser.addoption("--liteserv-version", action="store", help="liteserv-version: the version to download / install for the liteserv")
    parser.addoption("--liteserv-host", action="store", help="liteserv-host: the host to start liteserv on")
    parser.addoption("--liteserv-port", action="store", help="liteserv-port: the port to assign to liteserv")
    parser.addoption("--liteserv-storage-engine", action="store", help="liteserv-storage-engine: the storage engine to use with liteserv")
    parser.addoption("--sync-gateway-version", action="store", help="sync-gateway-version: the version of sync_gateway to run tests against")
