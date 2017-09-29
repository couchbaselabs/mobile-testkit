import pytest

from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.SyncGateway import (sync_gateway_config_path_for_mode,
                                  validate_sync_gateway_mode)
from keywords.tklogging import Logging

from keywords.utils import log_info, check_xattr_support, version_is_binary
from keywords.exceptions import ProvisioningError, FeatureSupportedError

from libraries.NetworkUtils import NetworkUtils
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from utilities.cluster_config_utils import get_load_balancer_ip


# This will be called once for the at the beggining of the execution of each .py file
# in the 'topology_specific_tests/multiple_servers' directory.
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
    xattrs_enabled = request.config.getoption("--xattrs")
    sg_lb = request.config.getoption("--sg-lb")
    sg_ce = request.config.getoption("--sg-ce")
    use_sequoia = request.config.getoption("--sequoia")

    if xattrs_enabled and version_is_binary(sync_gateway_version):
        check_xattr_support(server_version, sync_gateway_version)

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))
    log_info("race_enabled: {}".format(race_enabled))
    log_info("cbs_ssl: {}".format(cbs_ssl))
    log_info("xattrs_enabled: {}".format(xattrs_enabled))
    log_info("sg_lb: {}".format(sg_lb))
    log_info("sg_ce: {}".format(sg_ce))

    # sg-ce is invalid for di mode
    if mode == "di" and sg_ce:
        raise FeatureSupportedError("SGAccel is only available as an enterprise edition")

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use base_cc cluster config if mode is "cc" or base_di cluster config if more is "di"
    cluster_config = "{}/multiple_servers_{}".format(CLUSTER_CONFIGS_DIR, mode)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)

    # Add load balancer prop and check if load balancer IP is available
    if sg_lb:
        persist_cluster_config_environment_prop(cluster_config, 'sg_lb_enabled', True)
        log_info("Running tests with load balancer enabled: {}".format(get_load_balancer_ip(cluster_config)))
    else:
        log_info("Running tests with load balancer disabled")
        persist_cluster_config_environment_prop(cluster_config, 'sg_lb_enabled', False)

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

    # Skip provisioning if user specifies '--skip-provisoning' or '--sequoia'
    should_provision = True
    if skip_provisioning or use_sequoia:
        should_provision = False

    cluster_utils = ClusterKeywords()
    if should_provision:
        try:
            cluster_utils.provision_cluster(
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

    # Hit this intalled running services to verify the correct versions are installed
    cluster_utils.verify_cluster_versions(
        cluster_config,
        expected_server_version=server_version,
        expected_sync_gateway_version=sync_gateway_version
    )

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

    # Stop all sync_gateway and sg_accels as test finished
    c.stop_sg_and_accel()
