import pytest
import os
import datetime

from libraries.provision.clean_cluster import clean_cluster

from keywords.utils import log_info

from keywords.constants import SYNC_GATEWAY_CONFIGS

from keywords.constants import RESULTS_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import SyncGateway
from keywords.Logging import Logging


# Add custom arguments for executing tests in this directory
def pytest_addoption(parser):
    parser.addoption("--liteserv-platform", action="store", help="liteserv-platform: the platform to assign to the liteserv")
    parser.addoption("--liteserv-version", action="store", help="liteserv-version: the version to download / install for the liteserv")
    parser.addoption("--liteserv-host", action="store", help="liteserv-host: the host to start liteserv on")
    parser.addoption("--liteserv-port", action="store", help="liteserv-port: the port to assign to liteserv")
    parser.addoption("--liteserv-storage-engine", action="store", help="liteserv-storage-engine: the storage engine to use with liteserv")
    parser.addoption("--sync-gateway-version", action="store", help="sync-gateway-version: the version of sync_gateway to run tests against")


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/listener/shared/client_sg/ directory
@pytest.fixture(scope="session")
def setup_client_syncgateway_suite(request):

    """Suite setup fixture for client sync_gateway tests"""

    log_info("Setting up client sync_gateway suite ...")

    liteserv_platform = request.config.getoption("--liteserv-platform")
    liteserv_version = request.config.getoption("--liteserv-version")
    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")
    liteserv_storage_engine = request.config.getoption("--liteserv-storage-engine")

    sync_gateway_version = request.config.getoption("--sync-gateway-version")

    liteserv = LiteServFactory.create(platform=liteserv_platform,
                                      version_build=liteserv_version,
                                      host=liteserv_host,
                                      port=liteserv_port,
                                      storage_engine=liteserv_storage_engine)

    log_info("Downloading LiteServ ...")

    # Download LiteServ
    liteserv.download()

    # Install LiteServ
    liteserv.install()

    cluster_helper = ClusterKeywords()
    cluster_helper.set_cluster_config("1sg")
    cluster_config = os.environ["CLUSTER_CONFIG"]

    clean_cluster(cluster_config=cluster_config)

    log_info("Installing sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.install_sync_gateway(
        cluster_config=cluster_config,
        sync_gateway_version=sync_gateway_version,
        sync_gateway_config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS)
    )

    # Wait at the yeild until tests referencing this suite setup have run,
    # Then execute the teardown
    yield liteserv

    log_info("Tearing down suite ...")
    cluster_helper.unset_cluster_config()

    liteserv.remove()


# Passed to each testcase, run for each test_* method in client_sg folder
@pytest.fixture(scope="function")
def setup_client_syncgateway_test(request, setup_client_syncgateway_suite):
    """Test setup fixture for client sync_gateway tests"""

    log_info("Setting up client sync_gateway test ...")

    liteserv = setup_client_syncgateway_suite
    test_name = request.node.name

    ls_url = liteserv.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now()))

    cluster_helper = ClusterKeywords()
    sg_helper = SyncGateway()

    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])

    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_url)

    # Yield values to test case via fixture argument
    yield {
        "cluster_config": os.environ["CLUSTER_CONFIG"],
        "ls_url": ls_url,
        "sg_url": sg_url,
        "sg_admin_url": sg_admin_url
    }

    log_info("Tearing down test")

    # Teardown test
    client = MobileRestClient()
    client.delete_databases(ls_url)

    liteserv.stop()

    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_url)

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=os.environ["CLUSTER_CONFIG"], test_name=test_name)
