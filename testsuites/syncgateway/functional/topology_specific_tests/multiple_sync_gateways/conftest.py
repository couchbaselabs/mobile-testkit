import pytest

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import validate_sync_gateway_mode
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.NetworkUtils import NetworkUtils
from keywords.Logging import Logging

from keywords import constants
from libraries.testkit import cluster

from utilities.enable_disable_ssl_cluster import enable_ssl_in_cluster_config
from utilities.enable_disable_ssl_cluster import disable_ssl_in_cluster_config


# This will be called once for the at the beggining of the execution of each .py file
# in the 'topology_specific_tests/multiple_syncgateways' directory.
# It will be torn down (code after the yeild) when all of the tests have executed in that file
@pytest.fixture(scope="module")
def params_from_base_suite_setup(request):
    log_info("Setting up 'params_from_base_suite_setup' ...")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    mode = request.config.getoption("--mode")
    skip_provisioning = request.config.getoption("--skip-provisioning")
    race_enabled = request.config.getoption("--race")
    ssl = request.config.getoption("--server-ssl")

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use base_cc cluster config if mode is "cc" or base_di cluster config if more is "di"
    cluster_config = "{}/multiple_sync_gateways_{}".format(constants.CLUSTER_CONFIGS_DIR, mode)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)

    if ssl:
        log_info("Running tests with ssl enabled")
        # Enable ssl in cluster configs
        enable_ssl_in_cluster_config(cluster_config)
    else:
        log_info("Running tests with ssl disabled")
        # Disable ssl in cluster configs
        disable_ssl_in_cluster_config(cluster_config)

    # Skip provisioning if user specifies '--skip-provisoning'
    if not skip_provisioning:
        cluster_helper = ClusterKeywords()
        cluster_helper.provision_cluster(
            cluster_config=cluster_config,
            server_version=server_version,
            sync_gateway_version=sync_gateway_version,
            sync_gateway_config=sg_config
        )

    yield {"cluster_config": cluster_config, "mode": mode}

    log_info("Tearing down 'params_from_base_suite_setup' ...")


# This is called before each test and will yield the dictionary to each test that references the method
# as a parameter to the test method
@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    # Code before the yeild will execute before each test starts

    cluster_config = params_from_base_suite_setup["cluster_config"]
    mode = params_from_base_suite_setup["mode"]

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    network_utils = NetworkUtils()
    network_utils.start_packet_capture(cluster_config)

    # This dictionary is passed to each test
    yield {"cluster_config": cluster_config, "mode": mode}

    # Code after the yeild will execute when each test finishes
    log_info("Tearing down test '{}'".format(test_name))

    network_utils.list_connections()
    network_utils.stop_packet_capture(cluster_config)
    network_utils.collect_packet_capture(cluster_config=cluster_config, test_name=test_name)

    # Verify all sync_gateways and sg_accels are reachable
    c = cluster.Cluster(cluster_config)
    errors = c.verify_alive(mode)
    assert len(errors) == 0

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)
