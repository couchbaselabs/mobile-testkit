import pytest
import datetime

from keywords.utils import log_info

def pytest_addoption(parser):
    parser.addoption("--liteserv-host", action="store", help="liteserv-host: the host to start liteserv on")
    parser.addoption("--liteserv-port", action="store", help="liteserv-port: the port to assign to liteserv")

# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/listener/shared/client_sg/ directory
@pytest.fixture(scope="session")
def setup_client_syncgateway_suite(request):
    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")
    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    yield {
        "base_url" : base_url
        }