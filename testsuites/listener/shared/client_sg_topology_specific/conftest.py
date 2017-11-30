# Add custom arguments for executing tests in this directory
def pytest_addoption(parser):
    parser.addoption("--liteserv-platform", action="store", help="liteserv-platform: the platform to assign to the liteserv")
    parser.addoption("--liteserv-version", action="store", help="liteserv-version: the version to download / install for the liteserv")
    parser.addoption("--liteserv-host", action="store", help="liteserv-host: the host to start liteserv on")
    parser.addoption("--liteserv-port", action="store", help="liteserv-port: the port to assign to liteserv")
    parser.addoption("--liteserv-storage-engine", action="store", help="liteserv-storage-engine: the storage engine to use with liteserv")
    parser.addoption("--skip-provisioning", action="store_true", help="Skip cluster provisioning at setup", default=False)
    parser.addoption("--sync-gateway-version", action="store", help="sync-gateway-version: the version of sync_gateway to run tests against")
    parser.addoption("--sync-gateway-mode", action="store", help="sync-gateway-mode: the version of sync_gateway to run tests against, channel_cache ('cc') or distributed_index ('di')")
    parser.addoption("--server-version", action="store", help="server-version: version of Couchbase Server to install and run tests against")
    parser.addoption("--xattrs", action="store_true", help="Use xattrs for sync meta storage. Only works with Sync Gateway 1.5.0+ and Couchbase Server 5.0+")
