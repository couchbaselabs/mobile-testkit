import pytest
import datetime

from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords.utils import log_info
from keywords.utils import host_for_url, clear_resources_pngs
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.TestServerFactory import TestServerFactory
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.exceptions import ProvisioningError
from keywords.tklogging import Logging
from keywords.constants import RESULTS_DIR
from CBLClient.FileLogging import FileLogging
from CBLClient.Utils import Utils
from utilities.cluster_config_utils import get_load_balancer_ip


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
                     help="sync-gateway-version: Sync Gateway version to install "
                          "(ex. 1.3.1-16 or 590c1c31c7e83503eff304d8c0789bdd268d6291)")

    parser.addoption("--base-liteserv-version",
                     action="store",
                     help="liteserv-version: the version to download / install for the liteserv")

    parser.addoption("--liteserv-platform",
                     action="store",
                     help="liteserv-platform: the platform to assign to the liteserv")

    parser.addoption("--upgraded-liteserv-version",
                     action="store",
                     help="liteserv-version: the version to download / install for the liteserv")

    parser.addoption("--encrypted-db",
                     action="store_true",
                     help="If base db is encrypted, set this option")

    parser.addoption("--encrypted-db-password",
                     action="store",
                     default="password",
                     help="Provide password for encrypted db")

    parser.addoption("--liteserv-host",
                     action="store",
                     help="liteserv-host: the host to start liteserv on")

    parser.addoption("--liteserv-port",
                     action="store",
                     help="liteserv-port: the port to assign to liteserv")

    parser.addoption("--xattrs",
                     action="store_true",
                     help="xattrs: Enable xattrs for sync gateway")

    parser.addoption("--no-conflicts",
                     action="store_true",
                     help="If set, allow_conflicts is set to false in sync-gateway config")

    parser.addoption("--device", action="store_true",
                     help="Enable device if you want to run it on device", default=False)

    parser.addoption("--community", action="store_true",
                     help="If set, community edition will get picked up , default is enterprise", default=False)

    parser.addoption("--sg-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between Sync Gateway and CBL")

    parser.addoption("--sg-lb",
                     action="store_true",
                     help="If set, will enable load balancer for Sync Gateway")

    parser.addoption("--ci",
                     action="store_true",
                     help="If set, will target larger cluster (3 backing servers instead of 1, 2 accels if in di mode)")

    parser.addoption("--debug-mode", action="store_true",
                     help="Enable debug mode for the app ", default=False)

    parser.addoption("--use-views",
                     action="store_true",
                     help="If set, uses views instead of GSI - SG 2.1 and above only")

    parser.addoption("--number-replicas",
                     action="store",
                     help="Number of replicas for the indexer node - SG 2.1 and above only",
                     default=0)

    parser.addoption("--enable-file-logging",
                     action="store_true",
                     help="If set, CBL file logging would enable. Supported only cbl2.5 onwards")

    parser.addoption("--delta-sync",
                     action="store_true",
                     help="delta-sync: Enable delta-sync for sync gateway")


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/CBLTester/CBL_Functional_tests/ directory
@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    liteserv_platform = request.config.getoption("--liteserv-platform")
    base_liteserv_version = request.config.getoption("--base-liteserv-version")
    upgraded_liteserv_version = request.config.getoption("--upgraded-liteserv-version")
    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")

    skip_provisioning = request.config.getoption("--skip-provisioning")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    mode = request.config.getoption("--mode")

    db_password = request.config.getoption("--encrypted-db-password")
    encrypted_db = request.config.getoption("--encrypted-db")

    server_version = request.config.getoption("--server-version")
    xattrs_enabled = request.config.getoption("--xattrs")
    device_enabled = request.config.getoption("--device")
    community_enabled = request.config.getoption("--community")
    sg_ssl = request.config.getoption("--sg-ssl")
    sg_lb = request.config.getoption("--sg-lb")
    ci = request.config.getoption("--ci")
    debug_mode = request.config.getoption("--debug-mode")
    no_conflicts_enabled = request.config.getoption("--no-conflicts")
    use_views = request.config.getoption("--use-views")
    number_replicas = request.config.getoption("--number-replicas")
    delta_sync_enabled = request.config.getoption("--delta-sync")
    enable_file_logging = request.config.getoption("--enable-file-logging")

#     test_name = request.node.name
#   
#     testserver = TestServerFactory.create(platform=liteserv_platform,
#                                           version_build=upgraded_liteserv_version,
#                                           host=liteserv_host,
#                                           port=liteserv_port,
#                                           community_enabled=community_enabled,
#                                           debug_mode=debug_mode)
#   
#     log_info("Downloading TestServer ...")
#     # Download TestServer app
#     testserver.download()
#   
#     # Install TestServer app
#     if device_enabled:
#         testserver.install_device()
#     else:
#         testserver.install()

    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_travel_sample", mode)

    sg_db = "db"
    suite_cbl_db = None

    # use base_(lb_)cc cluster config if mode is "cc" or base_(lb_)di cluster config if mode is "di"
    if ci:
        cluster_config = "{}/ci_{}".format(CLUSTER_CONFIGS_DIR, mode)
        if sg_lb:
            cluster_config = "{}/ci_lb_{}".format(CLUSTER_CONFIGS_DIR, mode)
    else:
        cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, mode)
        if sg_lb:
            cluster_config = "{}/base_lb_{}".format(CLUSTER_CONFIGS_DIR, mode)

    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    sg_url = cluster_topology["sync_gateways"][0]["public"]
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_url)

    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)
    target_url = "ws://{}:4984/{}".format(sg_ip, sg_db)

    if sg_ssl:
        log_info("Enabling SSL on sync gateway")
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', True)
        target_url = "wss://{}:4984/{}".format(sg_ip, sg_db)

    if sg_lb:
        persist_cluster_config_environment_prop(cluster_config, 'sg_lb_enabled', True)
        log_info("Running tests with load balancer enabled: {}".format(get_load_balancer_ip(cluster_config)))
    else:
        log_info("Running tests with load balancer disabled")
        persist_cluster_config_environment_prop(cluster_config, 'sg_lb_enabled', False)

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

    if no_conflicts_enabled:
        log_info("Running with no conflicts")
        persist_cluster_config_environment_prop(cluster_config, 'no_conflicts_enabled', True)
    else:
        log_info("Running with allow conflicts")
        persist_cluster_config_environment_prop(cluster_config, 'no_conflicts_enabled', False)

    if use_views:
        log_info("Running SG tests using views")
        # Enable sg views in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', True)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable sg views in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', False)

    if delta_sync_enabled:
        log_info("Running with delta sync")
        persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', True)
    else:
        log_info("Running without delta sync")
        persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', False)

    # Write the number of replicas to cluster config
    persist_cluster_config_environment_prop(cluster_config, 'number_replicas', number_replicas)
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)
    cbs_url = cluster_topology['couchbase_servers'][0]
    cbs_ip = host_for_url(cbs_url)

    if sync_gateway_version < "2.0":
        pytest.skip('Does not work with sg < 2.0 , so skipping the test')

    if not skip_provisioning:
        log_info("Installing Sync Gateway + Couchbase Server + Accels ('di' only)")

        try:
            cluster_utils.provision_cluster(
                cluster_config=cluster_config,
                server_version=server_version,
                sync_gateway_version=sync_gateway_version,
                sync_gateway_config=sg_config
            )
        except ProvisioningError:
            logging_helper = Logging()
            logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=request.node.name)
            raise

    # Hit this installed running services to verify the correct versions are installed
#     cluster_utils.verify_cluster_versions(
#         cluster_config,
#         expected_server_version=server_version,
#         expected_sync_gateway_version=sync_gateway_version
#     )

    # Start Test server which needed for suite level set up like query tests
    log_info("Starting TestServer...")
#     test_name_cp = test_name.replace("/", "-")
#     if device_enabled:
#         testserver.start_device("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__,
#                                                               test_name_cp,
#                                                               datetime.datetime.now()))
#     else:
#         testserver.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__,
#                                                        test_name_cp,
#                                                        datetime.datetime.now()))

    suite_source_db = None
    suite_db_log_files = None
    if enable_file_logging and upgraded_liteserv_version >= "2.5.0":
        cbllog = FileLogging(base_url)
        cbllog.configure(log_level="verbose", max_rotate_count=2,
                         max_size=1000000 * 512, plain_text=True)
        suite_db_log_files = cbllog.get_directory()
        log_info("Log files available at - {}".format(suite_db_log_files))

    utils_obj = Utils(base_url)

    yield {
        "cluster_config": cluster_config,
        "mode": mode,
        "xattrs_enabled": xattrs_enabled,
        "liteserv_platform": liteserv_platform,
        "cluster_topology": cluster_topology,
        "base_liteserv_version": base_liteserv_version,
        "upgraded_liteserv_version": upgraded_liteserv_version,
        "liteserv_host": liteserv_host,
        "liteserv_port": liteserv_port,
        "target_url": target_url,
        "cbs_ip": cbs_ip,
        "sg_ip": sg_ip,
        "sg_db": sg_db,
        "no_conflicts_enabled": no_conflicts_enabled,
        "server_version": server_version,
        "sync_gateway_version": sync_gateway_version,
        "sg_admin_url": sg_admin_url,
        "base_url": base_url,
        "suite_source_db": suite_source_db,
        "suite_cbl_db": suite_cbl_db,
        "sg_config": sg_config,
#         "testserver": testserver,
        "device_enabled": device_enabled,
        "delta_sync_enabled": delta_sync_enabled,
        "enable_file_logging": enable_file_logging,
        "suite_db_log_files": suite_db_log_files,
        "db_password": db_password,
        "encrypted_db": encrypted_db,
        "utils_obj": utils_obj,
    }

    # Flush all the memory contents on the server app
    log_info("Flushing server memory")
    utils_obj.flushMemory()
#     log_info("Stopping the test server per suite")
#     testserver.stop()
    # Delete png files under resources/data
    clear_resources_pngs()