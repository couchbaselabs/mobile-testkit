import pytest

from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.Logging import Logging
from keywords.SyncGateway import validate_sync_gateway_mode
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster

from libraries.NetworkUtils import NetworkUtils


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

    parser.addoption("--collect-logs",
                     action="store_true",
                     help="Collect logs for every test. If this flag is not set, collection will only happen for test failures.")


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

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))
    log_info("race_enabled: {}".format(race_enabled))

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use base_cc cluster config if mode is "cc" or base_di cluster config if more is "di"
    if ci:
        log_info("Using 'ci_{}' config!".format(mode))
        cluster_config = "{}/ci_{}".format(CLUSTER_CONFIGS_DIR, mode)
    else:
        log_info("Using 'base_{}' config!".format(mode))
        cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, mode)

    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)

    # Skip provisioning if user specifies '--skip-provisoning'
    if not skip_provisioning:
        cluster_helper = ClusterKeywords()
        cluster_helper.provision_cluster(
            cluster_config=cluster_config,
            server_version=server_version,
            sync_gateway_version=sync_gateway_version,
            sync_gateway_config=sg_config,
            race_enabled=race_enabled
        )

    # Load topology as a dictionary
    cluster_utils = ClusterKeywords()
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    yield {
        "cluster_config": cluster_config,
        "cluster_topology": cluster_topology,
        "mode": mode
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

    test_name = request.node.name
    log_info("Running test '{}'".format(test_name))
    log_info("cluster_config: {}".format(cluster_config))
    log_info("cluster_topology: {}".format(cluster_topology))

    # This dictionary is passed to each test
    yield {
        "cluster_config": cluster_config,
        "cluster_topology": cluster_topology,
        "mode": mode
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
