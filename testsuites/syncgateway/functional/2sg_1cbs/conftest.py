import pytest
import os

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import SYNC_GATEWAY_CONFIGS


# Add custom arguments for executing tests in this directory
def pytest_addoption(parser):
    parser.addoption("--server-version", action="store", help="server-version: Couchbase Server version to install (ex. 4.5.0 or 4.5.0-2601)")
    parser.addoption(
        "--sync-gateway-version",
        action="store",
        help="sync-gateway-version: Sync Gateway version to install (ex. 1.3.1-16 or 590c1c31c7e83503eff304d8c0789bdd268d6291)"
    )


# This will be called once for the first test in the test session.
# After all the tests have completed in the directory
# the function will execute everything after the yield
@pytest.fixture(scope="session")
def setup_2sg_1cbs_suite(request):
    log_info("Setting up client sync_gateway suite ...")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")

    # Set the CLUSTER_CONFIG environment variable to 2sg_1cbs
    cluster_helper = ClusterKeywords()
    cluster_helper.set_cluster_config("2sg_1cbs")

    cluster_helper.provision_cluster(
        cluster_config=os.environ["CLUSTER_CONFIG"],
        server_version=server_version,
        sync_gateway_version=sync_gateway_version,
        sync_gateway_config="{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)
    )

    yield

    cluster_helper.unset_cluster_config()

    log_info("Tearing down suite ...")