""" Setup for Sync Gateway functional tests """

import pytest

from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.exceptions import ProvisioningError, FeatureSupportedError
from keywords.SyncGateway import (sync_gateway_config_path_for_mode,
                                  validate_sync_gateway_mode)
from keywords.tklogging import Logging
from keywords.utils import check_xattr_support, log_info, version_is_binary, compare_versions
from libraries.NetworkUtils import NetworkUtils
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from utilities.cluster_config_utils import get_load_balancer_ip

UNSUPPORTED_1_5_0_CC = {
    "test_db_offline_tap_loss_sanity[bucket_online_offline/bucket_online_offline_default_dcp-100]": {
        "reason": "Loss of DCP not longer puts the bucket in the offline state"
    },
    "test_db_offline_tap_loss_sanity[bucket_online_offline/bucket_online_offline_default-100]": {
        "reason": "Loss of DCP not longer puts the bucket in the offline state"
    },
    "test_multiple_dbs_unique_buckets_lose_tap[bucket_online_offline/bucket_online_offline_multiple_dbs_unique_buckets-100]": {
        "reason": "Loss of DCP not longer puts the bucket in the offline state"
    },
    "test_db_online_offline_webhooks_offline_two[webhooks/webhook_offline-5-1-1-2]": {
        "reason": "Loss of DCP not longer puts the bucket in the offline state"
    }
}


def skip_if_unsupported(sync_gateway_version, mode, test_name):

    # sync_gateway_version >= 1.5.0 and channel cache
    if compare_versions(sync_gateway_version, "1.5.0") >= 0 and mode == 'cc':
        if test_name in UNSUPPORTED_1_5_0_CC:
            pytest.skip(UNSUPPORTED_1_5_0_CC[test_name]["reason"])


# Add custom arguments for executing tests in this directory
def pytest_addoption(parser):

    parser.addoption("--mode",
                     action="store",
                     help="Sync Gateway mode to run the test in, 'cc' for channel cache or 'di' for distributed index")

    parser.addoption("--skip-provisioning",
                     action="store_true",
                     help="Skip cluster provisioning at setup",
                     default=False)

    parser.addoption("--server-version",
                     action="store",
                     help="server-version: Couchbase Server version to install (ex. 4.5.0 or 4.5.0-2601)")

    parser.addoption("--sync-gateway-version",
                     action="store",
                     help="sync-gateway-version: Sync Gateway version to install (ex. 1.3.1-16 or 590c1c31c7e83503eff304d8c0789bdd268d6291)")

    parser.addoption("--ci",
                     action="store_true",
                     help="If set, will target larger cluster (3 backing servers instead of 1, 2 accels if in di mode)")

    parser.addoption("--race",
                     action="store_true",
                     help="Enable -races for Sync Gateway build. IMPORTANT - This will only work with source builds at the moment")

    parser.addoption("--xattrs",
                     action="store_true",
                     help="Use xattrs for sync meta storage. Only works with Sync Gateway 2.0+ and Couchbase Server 5.0+")

    parser.addoption("--collect-logs",
                     action="store_true",
                     help="Collect logs for every test. If this flag is not set, collection will only happen for test failures.")

    parser.addoption("--server-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between server and Sync Gateway")

    parser.addoption("--sg-platform",
                     action="store",
                     help="Sync Gateway Platform binary to install (ex. centos or windows)",
                     default="centos")

    parser.addoption("--sa-platform",
                     action="store",
                     help="Sync Gateway Accelerator Platform binary to install (ex. centos or windows)",
                     default="centos")

    parser.addoption("--sg-lb",
                     action="store_true",
                     help="If set, will enable load balancer for Sync Gateway")

    parser.addoption("--sg-ce",
                     action="store_true",
                     help="If set, will install CE version of Sync Gateway")

    parser.addoption("--sequoia",
                     action="store_true",
                     help="If set, the tests will use a cluster provisioned by sequoia")


# This will be called once for the at the beggining of the execution in the 'tests/' directory
# and will be torn down, (code after the yeild) when all the test session has completed.
# IMPORTANT: Tests in 'tests/' should be executed in their own test run and should not be
# run in the same test run with 'topology_specific_tests/'. Doing so will make have unintended
# side effects due to the session scope
@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    log_info("Setting up 'params_from_base_suite_setup' ...")

    # pytest command line parameters
    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    mode = request.config.getoption("--mode")
    skip_provisioning = request.config.getoption("--skip-provisioning")
    ci = request.config.getoption("--ci")
    race_enabled = request.config.getoption("--race")
    cbs_ssl = request.config.getoption("--server-ssl")
    xattrs_enabled = request.config.getoption("--xattrs")
    sg_platform = request.config.getoption("--sg-platform")
    sa_platform = request.config.getoption("--sa-platform")
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
    log_info("xattrs_enabled: {}".format(xattrs_enabled))
    log_info("sg_platform: {}".format(sg_platform))
    log_info("sa_platform: {}".format(sa_platform))
    log_info("sg_lb: {}".format(sg_lb))
    log_info("sg_ce: {}".format(sg_ce))

    # sg-ce is invalid for di mode
    if mode == "di" and sg_ce:
        raise FeatureSupportedError("SGAccel is only available as an enterprise edition")

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use base_(lb_)cc cluster config if mode is "cc" or base_(lb_)di cluster config if mode is "di"
    if ci:
        cluster_config = "{}/ci_{}".format(CLUSTER_CONFIGS_DIR, mode)
        if sg_lb:
            cluster_config = "{}/ci_lb_{}".format(CLUSTER_CONFIGS_DIR, mode)
    else:
        cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, mode)
        if sg_lb:
            cluster_config = "{}/base_lb_{}".format(CLUSTER_CONFIGS_DIR, mode)

    log_info("Using '{}' config!".format(cluster_config))

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

    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)

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
                sg_platform=sg_platform,
                sa_platform=sa_platform,
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

    # Load topology as a dictionary
    cluster_utils = ClusterKeywords()
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    yield {
        "sync_gateway_version": sync_gateway_version,
        "cluster_config": cluster_config,
        "cluster_topology": cluster_topology,
        "mode": mode,
        "xattrs_enabled": xattrs_enabled,
        "sg_lb": sg_lb
    }

    log_info("Tearing down 'params_from_base_suite_setup' ...")


# This is called before each test and will yield the dictionary to each test that references the method
# as a parameter to the test method
@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    # Code before the yeild will execute before each test starts

    # pytest command line parameters
    collect_logs = request.config.getoption("--collect-logs")

    cluster_config = params_from_base_suite_setup["cluster_config"]
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    mode = params_from_base_suite_setup["mode"]
    xattrs_enabled = params_from_base_suite_setup["xattrs_enabled"]
    sg_lb = params_from_base_suite_setup["sg_lb"]

    test_name = request.node.name

    if sg_lb:
        # These tests target one SG node
        skip_tests = ['resync', 'log_rotation', 'openidconnect']
        for test in skip_tests:
            if test in test_name:
                pytest.skip("Skipping online/offline tests with load balancer")

    # Certain test are diabled for certain modes
    # Given the run conditions, check if the test needs to be skipped
    skip_if_unsupported(
        sync_gateway_version=params_from_base_suite_setup["sync_gateway_version"],
        mode=mode,
        test_name=test_name
    )

    log_info("Running test '{}'".format(test_name))
    log_info("cluster_config: {}".format(cluster_config))
    log_info("cluster_topology: {}".format(cluster_topology))
    log_info("mode: {}".format(mode))
    log_info("xattrs_enabled: {}".format(xattrs_enabled))

    # This dictionary is passed to each test
    yield {
        "cluster_config": cluster_config,
        "cluster_topology": cluster_topology,
        "mode": mode,
        "xattrs_enabled": xattrs_enabled
    }

    # Code after the yield will execute when each test finishes
    log_info("Tearing down test '{}'".format(test_name))

    network_utils = NetworkUtils()
    network_utils.list_connections()

    # Verify all sync_gateways and sg_accels are reachable
    c = cluster.Cluster(cluster_config)
    errors = c.verify_alive(mode)

    # if the test failed or a node is down, pull logs
    if collect_logs or request.node.rep_call.failed or len(errors) != 0:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)

    assert len(errors) == 0
