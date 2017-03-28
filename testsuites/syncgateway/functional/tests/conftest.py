import pytest
import json
import ConfigParser

from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.Logging import Logging
from keywords.SyncGateway import validate_sync_gateway_mode
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from libraries.testkit import cluster

from libraries.NetworkUtils import NetworkUtils


class CustomConfigParser(ConfigParser.RawConfigParser):
    """Virtually identical to the original method, but delimit keys and values with '=' instead of ' = '
       Python 3 has a space_around_delimiters=False option for write, it does not work for python 2.x
    """

    def write(self, fp):
        DEFAULTSECT = "DEFAULT"
        """Write an .ini-format representation of the configuration state."""
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in self._defaults.items():
                fp.write("%s=%s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for (key, value) in self._sections[section].items():
                if key == "__name__":
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    key = "=".join((key, str(value).replace('\n', '\n\t')))
                fp.write("%s\n" % (key))
            fp.write("\n")

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

    parser.addoption("--server-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between server and Sync Gateway")

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
    ci = request.config.getoption("--ci")
    ssl = request.config.getoption("--server-ssl")

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use base_cc cluster config if mode is "cc" or base_di cluster config if more is "di"
    if ci:
        log_info("Using 'ci_{}' config!".format(mode))
        cluster_config = "{}/ci_{}".format(CLUSTER_CONFIGS_DIR, mode)
    else:
        log_info("Using 'base_{}' config!".format(mode))
        cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, mode)

    if ssl:
        log_info("Running tests with ssl enabled")
        # Write ssl_enabled = True in the cluster_config.json
        cluster_config_json = "{}.json".format(cluster_config)
        with open(cluster_config_json, "rw") as f:
            cluster = json.loads(f.read())
        f.close()

        cluster["ssl_enabled"] = True
        with open(cluster_config_json, "w") as f:
            json.dump(cluster, f, indent=4)
        f.close()

        # Write [ssl] ssl_enabled = True in the cluster_config
        config = CustomConfigParser()
        config.read(cluster_config)
        if not config.has_section("ssl"):
            config.add_section("ssl")
        config.set('ssl', 'ssl_enabled', 'True')

        with open(cluster_config, 'w') as f:
            config.write(f)
        f.close()
    else:
        log_info("Running tests with ssl disabled")
        # Write ssl_enabled = False in the cluster_config.json
        # if ssl_enabled is present
        cluster_config_json = "{}.json".format(cluster_config)
        with open(cluster_config_json, "rw") as f:
            cluster = json.loads(f.read())
        f.close()

        if "ssl_enabled" in cluster:
            cluster["ssl_enabled"] = False
            with open(cluster_config_json, "w") as f:
                json.dump(cluster, f, indent=4)
            f.close()

        # Write [ssl] ssl_enabled = False in the cluster_config
        # if ssl is present
        config = CustomConfigParser()
        config.read(cluster_config)
        if config.has_section("ssl"):
            config.set('ssl', 'ssl_enabled', 'False')

            with open(cluster_config, 'w') as f:
                config.write(f)
            f.close()

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
    if request.node.rep_call.failed or len(errors) != 0:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)

    assert len(errors) == 0
