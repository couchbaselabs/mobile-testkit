import datetime
import pytest

from keywords.utils import log_info, check_xattr_support, version_is_binary
from keywords.LiteServFactory import LiteServFactory
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.constants import RESULTS_DIR
from keywords.tklogging import Logging
from utilities.cluster_config_utils import persist_cluster_config_environment_prop


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/listener/shared/client_sg_topology_specific/multiple_sync_gateways/ directory
@pytest.fixture(scope="module")
def setup_client_syncgateway_suite(request):

    """Suite setup fixture for client sync_gateway tests"""

    log_info("Setting up client sync_gateway suite ...")

    liteserv_platform = request.config.getoption("--liteserv-platform")
    liteserv_version = request.config.getoption("--liteserv-version")
    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")
    liteserv_storage_engine = request.config.getoption("--liteserv-storage-engine")

    skip_provisioning = request.config.getoption("--skip-provisioning")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    sync_gateway_mode = request.config.getoption("--sync-gateway-mode")
    server_version = request.config.getoption("--server-version")
    xattrs_enabled = request.config.getoption("--xattrs")

    liteserv = LiteServFactory.create(platform=liteserv_platform,
                                      version_build=liteserv_version,
                                      host=liteserv_host,
                                      port=liteserv_port,
                                      storage_engine=liteserv_storage_engine)

    if xattrs_enabled and version_is_binary(sync_gateway_version):
            check_xattr_support(server_version, sync_gateway_version)

    log_info("Downloading LiteServ ...")
    # Download LiteServ
    liteserv.download()

    # Install LiteServ
    liteserv.install()

    cluster_config = "{}/multiple_sync_gateways_{}".format(CLUSTER_CONFIGS_DIR, sync_gateway_mode)

    try:
        server_version
    except NameError:
        log_info("Server version is not provided")
        persist_cluster_config_environment_prop(cluster_config, 'server_version', "")
    else:
        log_info("Running test with server version {}".format(server_version))
        persist_cluster_config_environment_prop(cluster_config, 'server_version', server_version)

    try:
        sync_gateway_version
    except NameError:
        log_info("Sync gateway version is not provided")
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_version', "")
    else:
        log_info("Running test with sync_gateway version {}".format(sync_gateway_version))
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_version', sync_gateway_version)

    if xattrs_enabled:
        log_info("Running test with xattrs for sync meta storage")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', True)
    else:
        log_info("Using document storage for sync meta data")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', False)

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sync_gateway_mode)

    if not skip_provisioning:
        log_info("Installing Sync Gateway + Couchbase Server + Accels ('di' only)")
        cluster_utils = ClusterKeywords()
        cluster_utils.provision_cluster(
            cluster_config=cluster_config,
            server_version=server_version,
            sync_gateway_version=sync_gateway_version,
            sync_gateway_config=sg_config
        )

    # Wait at the yeild until tests referencing this suite setup have run,
    # Then execute the teardown
    yield {
        "liteserv": liteserv,
        "cluster_config": cluster_config,
        "sg_mode": sync_gateway_mode,
        "xattrs_enabled": xattrs_enabled
    }

    log_info("Tearing down suite ...")

    liteserv.remove()


# Passed to each testcase, run for each test_* method in
# testsuites/listener/shared/client_sg_topology_specific/multiple_sync_gateways/ directory
@pytest.fixture(scope="function")
def setup_client_syncgateway_test(request, setup_client_syncgateway_suite):
    """Test setup fixture for client sync_gateway tests"""

    log_info("Setting up client sync_gateway test ...")

    liteserv = setup_client_syncgateway_suite["liteserv"]
    cluster_config = setup_client_syncgateway_suite["cluster_config"]
    xattrs_enabled = setup_client_syncgateway_suite["xattrs_enabled"]
    test_name = request.node.name

    client = MobileRestClient()

    # Start LiteServ and delete any databases
    ls_url = liteserv.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now()))
    client.delete_databases(ls_url)

    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config=cluster_config)

    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]

    # Yield values to test case via fixture argument
    yield {
        "cluster_config": cluster_config,
        "sg_mode": setup_client_syncgateway_suite["sg_mode"],
        "ls_url": ls_url,
        "sg_url": sg_url,
        "sg_admin_url": sg_admin_url,
        "xattrs_enabled": xattrs_enabled
    }

    log_info("Tearing down test")
    client.delete_databases(ls_url)
    liteserv.stop()

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)
