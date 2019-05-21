""" Setup for Sync Gateway functional tests """
import pdb
import pytest
import os
import datetime
import time

from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.exceptions import ProvisioningError
from keywords.SyncGateway import (sync_gateway_config_path_for_mode,
                                  validate_sync_gateway_mode)
from keywords.tklogging import Logging
from keywords.utils import check_xattr_support, log_info, version_is_binary, clear_resources_pngs, check_delta_sync_support, host_for_url
from libraries.NetworkUtils import NetworkUtils
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords.exceptions import LogScanningError
from libraries.provision.ansible_runner import AnsibleRunner
from keywords.constants import RESULTS_DIR
from keywords.TestServerFactory import TestServerFactory

from CBLClient.Database import Database
from CBLClient.Utils import Utils


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

    parser.addoption("--server-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between server and Sync Gateway")

    parser.addoption("--xattrs",
                     action="store_true",
                     help="Use xattrs for sync meta storage. Only works with Sync Gateway 2.0+ and Couchbase Server 5.0+")

    parser.addoption("--liteserv-host",
                     action="store",
                     help="liteserv-host: the host to start liteserv on")

    parser.addoption("--liteserv-port",
                     action="store",
                     help="liteserv-port: the port to assign to liteserv")

    parser.addoption("--liteserv-version",
                     action="store",
                     help="liteserv-version: the version of liteserv to use")

    parser.addoption("--liteserv-platform",
                     action="store",
                     help="liteserv-platform: the platform on which to run liteserv")

    parser.addoption("--device", action="store_true",
                     help="Enable device if you want to run it on device", default=False)

    parser.addoption("--cluster-config",
                     action="store",
                     help="Provide a custom cluster config",
                     default="ci_lb")

    parser.addoption("--server-upgraded-version",
                     action="store",
                     help="server-version: Couchbase Server version to upgrade (ex. 4.5.0 or 4.5.0-2601)")

    parser.addoption("--sync-gateway-upgraded-version",
                     action="store",
                     help="sync-gateway-version: Sync Gateway version to upgrade (ex. 1.3.1-16 or 590c1c31c7e83503eff304d8c0789bdd268d6291)")

    parser.addoption("--num-docs",
                     action="store",
                     help="num-docs: Number of docs to load")

    parser.addoption("--cbs-platform",
                     action="store",
                     help="cbs-platform: Couchbase server platform",
                     default="centos7")

    parser.addoption("--cbs-upgrade-toybuild",
                     action="store",
                     help="cbs-upgrade-toybuild: Couchbase server toy build to use")

    parser.addoption("--sg-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between Sync Gateway and CBL")

    parser.addoption("--use-views",
                     action="store_true",
                     help="If set, uses views instead of GSI - SG 2.1 and above only")

    parser.addoption("--number-replicas",
                     action="store",
                     help="Number of replicas for the indexer node - SG 2.1 and above only",
                     default=0)

    parser.addoption("--delta-sync",
                     action="store_true",
                     help="delta-sync: Enable delta-sync for sync gateway, Only works with Sync Gateway 2.5+ EE along with CBL 2.5+ EE")


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
    server_upgraded_version = request.config.getoption("--server-upgraded-version")
    sync_gateway_upgraded_version = request.config.getoption("--sync-gateway-upgraded-version")
    mode = request.config.getoption("--mode")
    cluster_config = request.config.getoption("--cluster-config")
    skip_provisioning = request.config.getoption("--skip-provisioning")
    cbs_ssl = request.config.getoption("--server-ssl")
    xattrs_enabled = request.config.getoption("--xattrs")
    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")
    liteserv_version = request.config.getoption("--liteserv-version")
    liteserv_platform = request.config.getoption("--liteserv-platform")
    device_enabled = request.config.getoption("--device")
    num_docs = request.config.getoption("--num-docs")
    cbs_platform = request.config.getoption("--cbs-platform")
    cbs_toy_build = request.config.getoption("--cbs-upgrade-toybuild")
    sg_ssl = request.config.getoption("--sg-ssl")
    use_views = request.config.getoption("--use-views")
    number_replicas = request.config.getoption("--number-replicas")
    delta_sync_enabled = request.config.getoption("--delta-sync")

    if xattrs_enabled and version_is_binary(sync_gateway_version):
        check_xattr_support(server_upgraded_version, sync_gateway_upgraded_version)

    if delta_sync_enabled:
        check_delta_sync_support(sync_gateway_upgraded_version, liteserv_version)

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("server_upgraded_version: {}".format(server_upgraded_version))
    log_info("sync_gateway_upgraded_version: {}".format(sync_gateway_upgraded_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))
    log_info("cbs_ssl: {}".format(cbs_ssl))
    log_info("xattrs_enabled: {}".format(xattrs_enabled))
    log_info("liteserv_host: {}".format(liteserv_host))
    log_info("liteserv_port: {}".format(liteserv_port))
    log_info("liteserv_version: {}".format(liteserv_version))
    log_info("liteserv_platform: {}".format(liteserv_platform))
    log_info("device_enabled: {}".format(device_enabled))
    log_info("num_docs: {}".format(num_docs))
    log_info("cbs_platform: {}".format(cbs_platform))
    log_info("cbs_toy_build: {}".format(cbs_toy_build))
    log_info("sg_ssl: {}".format(sg_ssl))
    log_info("use_views: {}".format(use_views))
    log_info("number_replicas: {}".format(number_replicas))
    log_info("delta_sync_enabled: {}".format(delta_sync_enabled))

    pdb.set_trace()

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use ci_lb_cc cluster config if mode is "cc" or ci_lb_di cluster config if more is "di"
    # use base_(lb_)cc cluster config if mode is "cc" or base_(lb_)di cluster config if mode is "di"
    sg_db = "db"
    cluster_config = "{}/{}_{}".format(CLUSTER_CONFIGS_DIR, cluster_config, mode)
    log_info("Using '{}' config!".format(cluster_config))
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)
    sg_url = cluster_topology["sync_gateways"][0]["public"]
    sg_ip = host_for_url(sg_url)
    target_url = "ws://{}:4984/{}".format(sg_ip, sg_db)
    target_admin_url = "ws://{}:4985/{}".format(sg_ip, sg_db)

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

    # Only works with load balancer configs
    persist_cluster_config_environment_prop(cluster_config, 'sg_lb_enabled', True)

    if sg_ssl:
        log_info("Enabling SSL on sync gateway")
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', True)
        target_url = "wss://{}:4984/{}".format(sg_ip, sg_db)
        target_admin_url = "wss://{}:4985/{}".format(sg_ip, sg_db)
    else:
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)

    if use_views:
        log_info("Running SG tests using views")
        # Enable sg views in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', True)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable sg views in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', False)

    # Write the number of replicas to cluster config
    persist_cluster_config_environment_prop(cluster_config, 'number_replicas', number_replicas)

    if cbs_ssl:
        log_info("Running tests with cbs <-> sg ssl enabled")
        # Enable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', True)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', False)

    if delta_sync_enabled:
        log_info("Running with delta sync")
        persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', True)
    else:
        log_info("Running without delta sync")
        persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', False)

    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)

    pdb.set_trace()
    testserver = TestServerFactory.create(platform=liteserv_platform,
                                          version_build=liteserv_version,
                                          host=liteserv_host,
                                          port=liteserv_port,
                                          community_enabled=False,  # community_enabled
                                          debug_mode=False)  # debug_mode

    log_info("Downloading TestServer ...")
    # Download TestServer app
    testserver.download()

    # Install TestServer app
    if device_enabled:
        testserver.install_device()
    else:
        testserver.install()

    pdb.set_trace()
    # Skip provisioning if user specifies '--skip-provisoning'
    should_provision = True
    if skip_provisioning:
        should_provision = False

    cluster_utils = ClusterKeywords(cluster_config)
    if should_provision:
        try:
            cluster_utils.provision_cluster(
                cluster_config=cluster_config,
                server_version=server_version,
                sync_gateway_version=sync_gateway_version,
                sync_gateway_config=sg_config,
                cbs_platform=cbs_platform
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

    pdb.set_trace()
    yield {
        "cluster_config": cluster_config,
        "mode": mode,
        "xattrs_enabled": xattrs_enabled,
        "server_version": server_version,
        "sync_gateway_version": sync_gateway_version,
        "server_upgraded_version": server_upgraded_version,
        "sync_gateway_upgraded_version": sync_gateway_upgraded_version,
        "liteserv_host": liteserv_host,
        "liteserv_port": liteserv_port,
        "liteserv_version": liteserv_version,
        "liteserv_platform": liteserv_platform,
        "testserver": testserver,
        "device_enabled": device_enabled,
        "num_docs": num_docs,
        "cbs_platform": cbs_platform,
        "cbs_toy_build": cbs_toy_build,
        "target_url": target_url,
        "target_admin_url": target_admin_url,
        "sg_ip": sg_ip,
        "sg_db": sg_db
    }

    log_info("Tearing down 'params_from_base_suite_setup' ...")
    # Delete png files under resources/data
    clear_resources_pngs()


# This is called before each test and will yield the dictionary to each test that references the method
# as a parameter to the test method
@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    # Code before the yeild will execute before each test starts

    # pytest command line parameters
    cluster_config = params_from_base_suite_setup["cluster_config"]
    mode = params_from_base_suite_setup["mode"]
    xattrs_enabled = params_from_base_suite_setup["xattrs_enabled"]
    server_version = params_from_base_suite_setup["server_version"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    server_upgraded_version = params_from_base_suite_setup["server_upgraded_version"]
    sync_gateway_upgraded_version = params_from_base_suite_setup["sync_gateway_upgraded_version"]
    liteserv_host = params_from_base_suite_setup["liteserv_host"]
    liteserv_port = params_from_base_suite_setup["liteserv_port"]
    liteserv_version = params_from_base_suite_setup["liteserv_version"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]
    testserver = params_from_base_suite_setup["testserver"]
    device_enabled = params_from_base_suite_setup["device_enabled"]
    num_docs = params_from_base_suite_setup["num_docs"]
    cbs_platform = params_from_base_suite_setup["cbs_platform"]
    cbs_toy_build = params_from_base_suite_setup["cbs_toy_build"]
    target_url = params_from_base_suite_setup["target_url"]
    target_admin_url = params_from_base_suite_setup["target_admin_url"]
    sg_ip = params_from_base_suite_setup["sg_ip"]
    sg_db = params_from_base_suite_setup["sg_db"]

    test_name = request.node.name
    log_info("Running test '{}'".format(test_name))
    log_info("cluster_config: {}".format(cluster_config))
    log_info("mode: {}".format(mode))
    log_info("xattrs_enabled: {}".format(xattrs_enabled))

    pdb.set_trace()
    source_db = None
    test_name_cp = test_name.replace("/", "-")
    log_filename = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__,
                                                 test_name_cp,
                                                 datetime.datetime.now())

    # Starting TestServer
    log_info("Starting TestServer...")
    if device_enabled:
        testserver.start_device(log_filename)
    else:
        testserver.start(log_filename)

    pdb.set_trace()

    if xattrs_enabled:
        log_info("Running upgrade with xattrs for sync meta storage")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', True)
    else:
        log_info("Using document storage for sync meta data")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', False)

    # Create CBL database
    log_info("Creating database on cbl...")
    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    db = Database(base_url)

    cbl_db = "sg-upgrade{}".format(str(time.time()))
    log_info("Creating a Database {} at test setup".format(cbl_db))
    db_config = db.configure()
    source_db = db.create(cbl_db, db_config)
    log_info("Getting the database name")
    db_name = db.getName(source_db)
    assert db_name == cbl_db

    # This dictionary is passed to each test
    yield {
        "cluster_config": cluster_config,
        "mode": mode,
        "xattrs_enabled": xattrs_enabled,
        "server_version": server_version,
        "sync_gateway_version": sync_gateway_version,
        "server_upgraded_version": server_upgraded_version,
        "sync_gateway_upgraded_version": sync_gateway_upgraded_version,
        "liteserv_host": liteserv_host,
        "liteserv_port": liteserv_port,
        "liteserv_version": liteserv_version,
        "liteserv_platform": liteserv_platform,
        "device_enabled": device_enabled,
        "base_url": base_url,
        "target_url": target_url,
        "target_admin_url": target_admin_url,
        "sg_ip": sg_ip,
        "sg_db": sg_db,
        "db": db,
        "num_docs": num_docs,
        "cbs_platform": cbs_platform,
        "cbs_toy_build": cbs_toy_build
    }

    log_info("Tearing down test")
    # Delete CBL database
    log_info("Deleting the database sg-upgrade at test teardown")
    time.sleep(1)
    path = db.getPath(source_db)
    if db.exists(cbl_db, path):
        db.deleteDB(source_db)
    log_info("Flushing server memory")
    utils_obj = Utils(base_url)
    utils_obj.flushMemory()

    log_info("Stopping the test server per test")
    testserver.stop()

    network_utils = NetworkUtils()
    network_utils.list_connections()

    # Verify all sync_gateways and sg_accels are reachable
    c = cluster.Cluster(cluster_config)
    errors = c.verify_alive(mode)

    # Fetch logs
    logging_helper = Logging()
    logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)

    assert len(errors) == 0

    # Scan logs
    # SG logs for panic, data race
    # System logs for OOM
    ansible_runner = AnsibleRunner(cluster_config)
    script_name = "{}/utilities/check_logs.sh".format(os.getcwd())
    status = ansible_runner.run_ansible_playbook(
        "check-logs.yml",
        extra_vars={
            "script_name": script_name
        }
    )

    if status != 0:
        raise LogScanningError("Errors found in the logs")
