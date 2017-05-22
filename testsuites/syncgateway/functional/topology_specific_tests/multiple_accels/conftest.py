import pytest

import keywords.constants
from libraries.testkit.cluster import Cluster
from libraries.NetworkUtils import NetworkUtils
from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.SyncGateway import validate_sync_gateway_mode
from keywords.tklogging import Logging
from keywords.exceptions import ProvisioningError

from utilities.enable_disable_ssl_cluster import enable_cbs_ssl_in_cluster_config
from utilities.enable_disable_ssl_cluster import disable_cbs_ssl_in_cluster_config


# This will be called once at the beggining of the execution of each .py file
# in the 'topology_specific_tests/multiple_accels' directory.
# It will be torn down (code after the yeild) when all of the tests have executed in that file
@pytest.fixture(scope="module")
def params_from_base_suite_setup(request):
    log_info("Setting up 'params_from_base_suite_setup' ...")

    # pytest command line parameters
    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    mode = request.config.getoption("--mode")
    skip_provisioning = request.config.getoption("--skip-provisioning")
    race_enabled = request.config.getoption("--race")
    cbs_ssl = request.config.getoption("--server-ssl")

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))
    log_info("race_enabled: {}".format(race_enabled))

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # Skip these tests unless you are running in 'di' mode
    if mode != "di":
        pytest.skip("These tests should only run in with sg_accels")

    # use multiple_sg_accels_di
    cluster_config = "{}/multiple_sg_accels_di".format(keywords.constants.CLUSTER_CONFIGS_DIR)
    sg_config = "{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)

    if cbs_ssl:
        log_info("Running tests with cbs <-> sg ssl enabled")
        # Enable ssl in cluster configs
        enable_cbs_ssl_in_cluster_config(cluster_config)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable ssl in cluster configs
        disable_cbs_ssl_in_cluster_config(cluster_config)

    # Skip provisioning if user specifies '--skip-provisoning'
    if not skip_provisioning:
        cluster_helper = ClusterKeywords()
        try:
            cluster_helper.provision_cluster(
                cluster_config=cluster_config,
                server_version=server_version,
                sync_gateway_version=sync_gateway_version,
                sync_gateway_config=sg_config,
                race_enabled=race_enabled
            )
        except ProvisioningError:
            logging_helper = Logging()
            logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=request.node.name)
            raise

    yield {"cluster_config": cluster_config, "mode": mode}

    log_info("Tearing down 'params_from_base_suite_setup' ...")


# This is called before each test and will yield the dictionary to each test that references the method
# as a parameter to the test method
@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    # Code before the yeild will execute before each test starts

    # pytest command line parameters
    collect_logs = request.config.getoption("--collect-logs")

    cluster_config = params_from_base_suite_setup["cluster_config"]
    mode = params_from_base_suite_setup["mode"]

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    # This dictionary is passed to each test
    yield {"cluster_config": cluster_config, "mode": mode}

    # Code after the yeild will execute when each test finishes
    log_info("Tearing down test '{}'".format(test_name))

    # Capture testkit socket usage
    network_utils = NetworkUtils()
    network_utils.list_connections()

    # Verify all sync_gateways and sg_accels are reachable
    c = Cluster(cluster_config)
    errors = c.verify_alive(mode)

    # if the test failed pull logs
    if collect_logs or request.node.rep_call.failed or len(errors) != 0:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)

    assert len(errors) == 0
