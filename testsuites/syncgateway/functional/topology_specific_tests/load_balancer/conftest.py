import pytest

import keywords.constants
from keywords.ClusterKeywords import ClusterKeywords
from keywords.exceptions import ProvisioningError
from keywords.SyncGateway import (sync_gateway_config_path_for_mode,
                                  validate_sync_gateway_mode)
from keywords.tklogging import Logging
from keywords.utils import check_xattr_support, log_info, version_is_binary
from libraries.NetworkUtils import NetworkUtils
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop


# This will be called once at the beggining of the execution in the 'tests/load_balancer' directory
# and will be torn down, (code after the yeild) after each .py file in this directory
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
    xattrs_enabled = request.config.getoption("--xattrs")
    sg_ce = request.config.getoption("--sg-ce")

    if xattrs_enabled and version_is_binary(sync_gateway_version):
        check_xattr_support(server_version, sync_gateway_version)

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))
    log_info("race_enabled: {}".format(race_enabled))
    log_info("cbs_ssl: {}".format(cbs_ssl))
    log_info("xattrs_enabled: {}".format(xattrs_enabled))
    log_info("sg_ce: {}".format(sg_ce))

    # sg-ce is invalid for di mode
    if mode == "di" and sg_ce:
        pytest.skip("SGAccel is only available as an enterprise edition")

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use load_balancer_cc cluster config if mode is "cc" or load_balancer_di cluster config if mode is "di"
    cluster_config = "{}/load_balancer_{}".format(keywords.constants.CLUSTER_CONFIGS_DIR, mode)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)

    if cbs_ssl:
        log_info("Running tests with cbs <-> sg ssl enabled")
        # Enable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', True)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', False)

    if xattrs_enabled:
        log_info("Running test with xattrs for sync meta storage")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', True)
    else:
        log_info("Using document storage for sync meta data")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', False)

    # Skip provisioning if user specifies '--skip-provisoning'
    if not skip_provisioning:
        cluster_helper = ClusterKeywords()
        try:
            cluster_helper.provision_cluster(
                cluster_config=cluster_config,
                server_version=server_version,
                sync_gateway_version=sync_gateway_version,
                sync_gateway_config=sg_config,
                race_enabled=race_enabled,
                sg_ce=sg_ce
            )
        except ProvisioningError:
            logging_helper = Logging()
            logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=request.node.name)
            raise

    yield {"cluster_config": cluster_config, "mode": mode}

    log_info("Tearing down 'params_from_base_suite_setup' ...")


# This is called before each test and will yield the cluster_config to each test in the file
# After each test_* function, execution will continue from the yield a pull logs on failure
@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):

    # pytest command line parameters
    collect_logs = request.config.getoption("--collect-logs")

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    cluster_config = params_from_base_suite_setup["cluster_config"]
    mode = params_from_base_suite_setup["mode"]

    yield {
        "cluster_config": cluster_config,
        "mode": mode
    }

    log_info("Tearing down test '{}'".format(test_name))

    # Capture testkit socket usage
    network_utils = NetworkUtils()
    network_utils.list_connections()

    # Verify all sync_gateways and sg_accels are reachable
    c = cluster.Cluster(cluster_config)
    errors = c.verify_alive(mode)

    # if the test failed pull logs
    if collect_logs or request.node.rep_call.failed or len(errors) != 0:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)

    assert len(errors) == 0
