import os

import pytest

from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.Logging import Logging
from keywords.SyncGateway import validate_sync_gateway_mode
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from libraries.NetworkUtils import NetworkUtils


# This will be called once for the at the beggining of the execution in the 'tests/' directory
# and will be torn down, (code after the yeild) when all the test session has completed.
# IMPORTANT: Tests in 'tests/' should be executed in their own test run and should not be
# run in the same test run with 'topology_specific_tests/'. Doing so will make have unintended
# side effects due to the session scope
@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    log_info("Setting up 'params_from_base_suite_setup' ...")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    mode = request.config.getoption("--mode")
    skip_provisioning = request.config.getoption("--skip-provisioning")

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use base_cc cluster config if mode is "cc" or base_di cluster config if more is "di"
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, mode)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)

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

    log_info("Tearing down 'setup_1sg_1ac_1cbs_suite' ...")


# This is called before each test and will yield the dictionary to each test that references the method
# as a parameter to the test method
@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    # Code before the yeild will execute before each test starts

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

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)