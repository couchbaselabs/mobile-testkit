import pytest
import datetime
import time

from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.exceptions import ProvisioningError
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.tklogging import Logging
from keywords.utils import check_xattr_support, log_info, version_is_binary, clear_resources_pngs, host_for_url, check_delta_sync_support
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords.constants import RESULTS_DIR
from keywords.TestServerFactory import TestServerFactory

from CBLClient.Database import Database
from CBLClient.Utils import Utils
from CBLClient.FileLogging import FileLogging


def pytest_addoption(parser):
    parser.addoption("--mode",
                     action="store",
                     help="Sync Gateway mode to run the test in, 'cc' for channel cache or 'di' for distributed index")

    parser.addoption("--cluster-config",
                     action="store",
                     help="Provide a custom cluster config",
                     default="ci_lb")

    parser.addoption("--skip-provisioning",
                     action="store_true",
                     help="Skip cluster provisioning at setup",
                     default=False)

    parser.addoption("--use-local-testserver",
                     action="store_true",
                     help="Skip download and launch TestServer, use local debug build",
                     default=False)

    parser.addoption("--num-docs",
                     action="store",
                     help="num-docs: Number of docs to load")

    parser.addoption("--cbs-platform",
                     action="store",
                     help="cbs-platform: Couchbase server platform",
                     default="centos7")

    parser.addoption("--server-version",
                     action="store",
                     help="server-version: Couchbase Server version to install (ex. 4.5.0 or 4.5.0-2601)")

    parser.addoption("--sync-gateway-version",
                     action="store",
                     help="sync-gateway-version: Sync Gateway version to install (ex. 1.3.1-16 or 590c1c31c7e83503eff304d8c0789bdd268d6291)")

    parser.addoption("--server-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between server and Sync Gateway")

    parser.addoption("--sg-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between Sync Gateway and CBL")

    parser.addoption("--xattrs",
                     action="store_true",
                     help="Use xattrs for sync meta storage. Only works with Sync Gateway 2.0+ and Couchbase Server 5.0+")

    parser.addoption("--no-conflicts",
                     action="store_true",
                     help="If set, allow_conflicts is set to false in sync-gateway config")

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

    parser.addoption("--enable-file-logging",
                     action="store_true",
                     help="If set, CBL file logging would enable. Supported only cbl2.5 onwards")

    parser.addoption("--device", action="store_true",
                     help="Enable device if you want to run it on device", default=False)

    parser.addoption("--server-upgraded-version",
                     action="store",
                     help="server-version: Couchbase Server version to upgrade (ex. 4.5.0 or 4.5.0-2601)")

    parser.addoption("--sync-gateway-upgraded-version",
                     action="store",
                     help="sync-gateway-version: Sync Gateway version to upgrade (ex. 1.3.1-16 or 590c1c31c7e83503eff304d8c0789bdd268d6291)")

    parser.addoption("--upgraded-server-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between server and Sync Gateway")

    parser.addoption("--upgraded-sg-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between Sync Gateway and CBL")

    parser.addoption("--upgraded-xattrs",
                     action="store_true",
                     help="Use xattrs for sync meta storage after upgrade. Only works with Sync Gateway 2.0+ and Couchbase Server 5.0+")

    parser.addoption("--upgraded-use-views",
                     action="store_true",
                     help="If set, uses views instead of GSI  after upgrade - SG 2.1 and above only")

    parser.addoption("--upgraded-number-replicas",
                     action="store",
                     help="Number of replicas for the indexer node  after upgrade - SG 2.1 and above only",
                     default=0)

    parser.addoption("--upgraded-delta-sync",
                     action="store_true",
                     help="delta-sync: Enable delta-sync for sync gateway after upgrade, Only works with Sync Gateway 2.5+ EE along with CBL 2.5+ EE")

    parser.addoption("--upgraded-no-conflicts",
                     action="store_true",
                     help="If set, allow_conflicts is set to false in sync-gateway config")

    parser.addoption("--stop-replication-before-upgrade",
                     action="store_true",
                     help="stop replication before upgrade , otherwise it won't stop replication")

    parser.addoption("--sgw_cluster1_count",
                     action="store", type="int",
                     help="SGW cluster1 node count",
                     default=2)

    parser.addoption("--sgw_cluster2_count",
                     action="store", type="int",
                     help="SGW cluster2 node count",
                     default=2)

    parser.addoption("--cbs-upgrade-toybuild",
                     action="store",
                     help="cbs-upgrade-toybuild: Couchbase server toy build to use")

    parser.addoption("--hide-product-version",
                     action="store_true",
                     help="Hides SGW product version when you hit SGW url",
                     default=False)

    parser.addoption("--skip-couchbase-provision",
                     action="store_true",
                     help="skip the couchbase provision step")


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/CBLTester/CBL_Functional_tests/ directory
@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    log_info("Setting up 'params_from_base_suite_setup' ...")

    # pytest command line parameters
    mode = request.config.getoption("--mode")
    cluster_config = request.config.getoption("--cluster-config")
    skip_provisioning = request.config.getoption("--skip-provisioning")
    use_local_testserver = request.config.getoption("--use-local-testserver")
    num_docs = request.config.getoption("--num-docs")
    cbs_platform = request.config.getoption("--cbs-platform")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")

    cbs_ssl = request.config.getoption("--server-ssl")
    sg_ssl = request.config.getoption("--sg-ssl")
    xattrs_enabled = request.config.getoption("--xattrs")
    use_views = request.config.getoption("--use-views")
    number_replicas = request.config.getoption("--number-replicas")
    delta_sync_enabled = request.config.getoption("--delta-sync")
    server_upgraded_version = request.config.getoption("--server-upgraded-version")
    sync_gateway_upgraded_version = request.config.getoption("--sync-gateway-upgraded-version")
    upgraded_cbs_ssl = request.config.getoption("--upgraded-server-ssl")
    upgraded_sg_ssl = request.config.getoption("--upgraded-sg-ssl")
    upgraded_xattrs_enabled = request.config.getoption("--upgraded-xattrs")
    upgraded_use_views = request.config.getoption("--upgraded-use-views")
    upgraded_number_replicas = request.config.getoption("--upgraded-number-replicas")
    upgraded_delta_sync_enabled = request.config.getoption("--upgraded-delta-sync")

    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")
    liteserv_version = request.config.getoption("--liteserv-version")
    liteserv_platform = request.config.getoption("--liteserv-platform")
    enable_file_logging = request.config.getoption("--enable-file-logging")
    device_enabled = request.config.getoption("--device")
    cbs_toy_build = request.config.getoption("--cbs-upgrade-toybuild")
    stop_replication_before_upgrade = request.config.getoption("--stop-replication-before-upgrade")
    sgw_cluster1_count = request.config.getoption("--sgw_cluster1_count")
    sgw_cluster2_count = request.config.getoption("--sgw_cluster2_count")
    no_conflicts_enabled = request.config.getoption("--no-conflicts")
    upgraded_no_conflicts_enabled = request.config.getoption("--upgraded-no-conflicts")
    hide_product_version = request.config.getoption("--hide-product-version")
    skip_couchbase_provision = request.config.getoption("--skip-couchbase-provision")
    test_name = request.node.name

    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))
    log_info("num_docs: {}".format(num_docs))
    log_info("cbs_platform: {}".format(cbs_platform))
    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("cbs_ssl: {}".format(cbs_ssl))
    log_info("sg_ssl: {}".format(sg_ssl))
    log_info("xattrs_enabled: {}".format(xattrs_enabled))
    log_info("use_views: {}".format(use_views))
    log_info("number_replicas: {}".format(number_replicas))
    log_info("delta_sync_enabled: {}".format(delta_sync_enabled))
    log_info("enable_file_logging: {}".format(enable_file_logging))
    log_info("server_upgraded_version: {}".format(server_upgraded_version))
    log_info("sync_gateway_upgraded_version: {}".format(sync_gateway_upgraded_version))
    log_info("upgraded_cbs_ssl: {}".format(upgraded_cbs_ssl))
    log_info("upgraded_sg_ssl: {}".format(upgraded_sg_ssl))
    log_info("upgraded_xattrs_enabled: {}".format(upgraded_xattrs_enabled))
    log_info("upgraded_use_views: {}".format(upgraded_use_views))
    log_info("upgraded_number_replicas: {}".format(upgraded_number_replicas))
    log_info("upgraded_delta_sync_enabled: {}".format(upgraded_delta_sync_enabled))
    log_info("liteserv_host: {}".format(liteserv_host))
    log_info("liteserv_port: {}".format(liteserv_port))
    log_info("liteserv_version: {}".format(liteserv_version))
    log_info("liteserv_platform: {}".format(liteserv_platform))
    log_info("device_enabled: {}".format(device_enabled))
    log_info("cbs_toy_build: {}".format(cbs_toy_build))
    log_info("stop replication before upgrade: {}".format(stop_replication_before_upgrade))
    log_info("sgw_cluster1_count: {}".format(sgw_cluster1_count))
    log_info("sgw_cluster2_count: {}".format(sgw_cluster2_count))
    log_info("no_conflicts_enabled: {}".format(no_conflicts_enabled))
    log_info("upgraded_no_conflicts_enabled: {}".format(upgraded_no_conflicts_enabled))
    log_info("hide_product_version: {}".format(hide_product_version))

    # if xattrs is specified but the post upgrade SG version doesn't support, don't continue
    if upgraded_xattrs_enabled and version_is_binary(sync_gateway_upgraded_version):
        check_xattr_support(server_upgraded_version, sync_gateway_upgraded_version)
    # if delta_sync is specified but the post upgrade version doesn't support, don't continue
    if upgraded_delta_sync_enabled:
        check_delta_sync_support(sync_gateway_upgraded_version, liteserv_version)

    create_db_per_test = "cbl-test"
    create_db_per_suite = None

    testserver = TestServerFactory.create(platform=liteserv_platform,
                                          version_build=liteserv_version,
                                          host=liteserv_host,
                                          port=liteserv_port,
                                          community_enabled=False,
                                          debug_mode=False)

    log_info("Downloading TestServer ...")
    # Download TestServer app
    if not use_local_testserver:
        testserver.download()

        # Install TestServer app
        if device_enabled:
            testserver.install_device()
        else:
            testserver.install()

    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    sg_config = sync_gateway_config_path_for_mode("listener_tests/multiple_sync_gateways", mode)

    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    suite_cbl_db = None

    # use cluster config specified by arguments with "cc" if mode is "cc" or "di" if mode is "di"
    cluster_config = "{}/{}_{}".format(CLUSTER_CONFIGS_DIR, cluster_config, mode)
    log_info("Using '{}' config!".format(cluster_config))

    # Only works with load balancer configs
    persist_cluster_config_environment_prop(cluster_config, 'two_sg_cluster_lb_enabled', True, property_name_check=False)
    persist_cluster_config_environment_prop(cluster_config, 'sgw_cluster1_count', sgw_cluster1_count, property_name_check=False)
    persist_cluster_config_environment_prop(cluster_config, 'sgw_cluster2_count', sgw_cluster2_count, property_name_check=False)

    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    sg1_url = cluster_topology["sync_gateways"][0]["public"]
    sg3_url = cluster_topology["sync_gateways"][2]["public"]
    sg1_ip = host_for_url(sg1_url)
    sg3_ip = host_for_url(sg3_url)

    target1_url = "ws://{}:4984/{}".format(sg1_ip, sg_db1)
    target1_admin_url = "ws://{}:4985/{}".format(sg1_ip, sg_db1)
    target2_url = "ws://{}:4984/{}".format(sg3_ip, sg_db2)
    target2_admin_url = "ws://{}:4985/{}".format(sg3_ip, sg_db2)

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
        if sync_gateway_version >= "2.0.0" and server_version >= "5.0.0":
            # if SG pre-upgrade version is 2.0+, set xattrs property, otherwise, don't specify in cluster config
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

        if sync_gateway_version >= "2.5.0" and server_version >= "5.5.0":
            # if SG pre-upgrade version is 2.5+, set delta sync property, otherwise, don't specify in cluster config
            if delta_sync_enabled:
                log_info("Running with delta sync")
                persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', True)
            else:
                log_info("Running without delta sync")
                persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', False)

    if sg_ssl:
        log_info("Enabling SSL on sync gateway")
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', True)
        target1_url = "wss://{}:4984/{}".format(sg1_ip, sg_db1)
        target1_admin_url = "wss://{}:4985/{}".format(sg1_ip, sg_db1)
        target2_url = "wss://{}:4984/{}".format(sg3_ip, sg_db2)
        target2_admin_url = "wss://{}:4985/{}".format(sg3_ip, sg_db2)
    else:
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)

    if cbs_ssl:
        log_info("Running tests with cbs <-> sg ssl enabled")
        # Enable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', True)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', False)

    if use_views:
        log_info("Running SG tests using views")
        # Enable sg views in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', True)
    else:
        log_info("Running tests not using views")
        # Disable sg views in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', False)

    if hide_product_version:
        log_info("Suppress the SGW product Version")
        persist_cluster_config_environment_prop(cluster_config, 'hide_product_version', True)
    else:
        log_info("Running without suppress SGW product Version")
        persist_cluster_config_environment_prop(cluster_config, 'hide_product_version', False)

    persist_cluster_config_environment_prop(cluster_config, 'sg_platform', "centos", False)

    # Write the number of replicas to cluster config
    persist_cluster_config_environment_prop(cluster_config, 'number_replicas', number_replicas)
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    if not skip_provisioning:
        log_info("Installing Sync Gateway + Couchbase Server")

        try:
            cluster_utils.provision_cluster(
                cluster_config=cluster_config,
                server_version=server_version,
                sync_gateway_version=sync_gateway_version,
                sync_gateway_config=sg_config,
                skip_couchbase_provision=skip_couchbase_provision
            )
        except ProvisioningError:
            logging_helper = Logging()
            logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=request.node.name)
            raise

    # Hit this installed running services to verify the correct versions are installed
    cluster_utils.verify_cluster_versions(
        cluster_config,
        expected_server_version=server_version,
        expected_sync_gateway_version=sync_gateway_version
    )

    # Start Test server which needed for suite level set up
    if create_db_per_suite:
        log_info("Starting TestServer...")
        test_name_cp = test_name.replace("/", "-")
        if device_enabled:
            testserver.start_device("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__,
                                                                  test_name_cp,
                                                                  datetime.datetime.now()))
        else:
            testserver.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__,
                                                           test_name_cp,
                                                           datetime.datetime.now()))

    suite_source_db = None
    suite_db = None
    suite_db_log_files = None
    if create_db_per_suite:
        if enable_file_logging and liteserv_version >= "2.5.0":
            cbllog = FileLogging(base_url)
            cbllog.configure(log_level="verbose", max_rotate_count=2,
                             max_size=1000000 * 512, plain_text=True)
            suite_db_log_files = cbllog.get_directory()
            log_info("Log files available at - {}".format(suite_db_log_files))
        # Create CBL database
        suite_cbl_db = create_db_per_suite
        suite_db = Database(base_url)

        log_info("Creating a Database {} at the suite setup".format(suite_cbl_db))
        db_config = suite_db.configure()
        suite_source_db = suite_db.create(suite_cbl_db, db_config)
        log_info("Getting the database name")
        db_name = suite_db.getName(suite_source_db)
        assert db_name == suite_cbl_db

    yield {
        "cluster_config": cluster_config,
        "cluster_topology": cluster_topology,
        "mode": mode,
        "cbs_platform": cbs_platform,
        "server_version": server_version,
        "sync_gateway_version": sync_gateway_version,
        "server_upgraded_version": server_upgraded_version,
        "sync_gateway_upgraded_version": sync_gateway_upgraded_version,
        "cbs_ssl": cbs_ssl,
        "sg_ssl": sg_ssl,
        "xattrs_enabled": xattrs_enabled,
        "use_views": use_views,
        "number_replicas": number_replicas,
        "delta_sync_enabled": delta_sync_enabled,
        "upgraded_cbs_ssl": upgraded_cbs_ssl,
        "upgraded_sg_ssl": upgraded_sg_ssl,
        "upgraded_xattrs_enabled": upgraded_xattrs_enabled,
        "upgraded_use_views": upgraded_use_views,
        "upgraded_number_replicas": upgraded_number_replicas,
        "upgraded_delta_sync_enabled": upgraded_delta_sync_enabled,
        "liteserv_host": liteserv_host,
        "liteserv_port": liteserv_port,
        "liteserv_version": liteserv_version,
        "liteserv_platform": liteserv_platform,
        "enable_file_logging": enable_file_logging,
        "testserver": testserver,
        "device_enabled": device_enabled,
        "num_docs": num_docs,
        "cbs_toy_build": cbs_toy_build,
        "target1_url": target1_url,
        "target1_admin_url": target1_admin_url,
        "target2_url": target2_url,
        "target2_admin_url": target2_admin_url,
        "base_url": base_url,
        "sg1_ip": sg1_ip,
        "sg3_ip": sg3_ip,
        "sg_config": sg_config,
        "create_db_per_test": create_db_per_test,
        "stop_replication_before_upgrade": stop_replication_before_upgrade,
        "sgw_cluster1_count": sgw_cluster1_count,
        "sgw_cluster2_count": sgw_cluster2_count,
        "no_conflicts_enabled": no_conflicts_enabled,
        "upgraded_no_conflicts_enabled": upgraded_no_conflicts_enabled
    }

    # Flush all the memory contents on the server app
    log_info("Flushing server memory")
    utils_obj = Utils(base_url)
    utils_obj.flushMemory()
    log_info("Stopping the test server per suite")
    if not use_local_testserver:
        testserver.stop()

    # Delete png files under resources/data
    clear_resources_pngs()


@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    cluster_config = params_from_base_suite_setup["cluster_config"]
    mode = params_from_base_suite_setup["mode"]
    server_version = params_from_base_suite_setup["server_version"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    server_upgraded_version = params_from_base_suite_setup["server_upgraded_version"]
    sync_gateway_upgraded_version = params_from_base_suite_setup["sync_gateway_upgraded_version"]
    cbs_ssl = params_from_base_suite_setup["cbs_ssl"],
    sg_ssl = params_from_base_suite_setup["sg_ssl"],
    xattrs_enabled = params_from_base_suite_setup["xattrs_enabled"],
    use_views = params_from_base_suite_setup["use_views"],
    number_replicas = params_from_base_suite_setup["number_replicas"],
    delta_sync_enabled = params_from_base_suite_setup["delta_sync_enabled"],
    upgraded_cbs_ssl = params_from_base_suite_setup["upgraded_cbs_ssl"]
    upgraded_sg_ssl = params_from_base_suite_setup["upgraded_sg_ssl"]
    upgraded_xattrs_enabled = params_from_base_suite_setup["upgraded_xattrs_enabled"]
    upgraded_use_views = params_from_base_suite_setup["upgraded_use_views"]
    upgraded_number_replicas = params_from_base_suite_setup["upgraded_number_replicas"]
    upgraded_delta_sync_enabled = params_from_base_suite_setup["upgraded_delta_sync_enabled"]
    liteserv_host = params_from_base_suite_setup["liteserv_host"]
    liteserv_port = params_from_base_suite_setup["liteserv_port"]
    liteserv_version = params_from_base_suite_setup["liteserv_version"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]
    testserver = params_from_base_suite_setup["testserver"]
    device_enabled = params_from_base_suite_setup["device_enabled"]
    num_docs = params_from_base_suite_setup["num_docs"]
    cbs_platform = params_from_base_suite_setup["cbs_platform"]
    cbs_toy_build = params_from_base_suite_setup["cbs_toy_build"]
    target1_url = params_from_base_suite_setup["target1_url"]
    target1_admin_url = params_from_base_suite_setup["target1_admin_url"]
    target2_url = params_from_base_suite_setup["target2_url"]
    target2_admin_url = params_from_base_suite_setup["target2_admin_url"]
    sg1_ip = params_from_base_suite_setup["sg1_ip"]
    sg3_ip = params_from_base_suite_setup["sg3_ip"]
    sg_config = params_from_base_suite_setup["sg_config"]
    create_db_per_test = params_from_base_suite_setup["create_db_per_test"]
    enable_file_logging = params_from_base_suite_setup["enable_file_logging"]
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    base_url = params_from_base_suite_setup["base_url"]
    stop_replication_before_upgrade = params_from_base_suite_setup["stop_replication_before_upgrade"]
    use_local_testserver = request.config.getoption("--use-local-testserver")
    sgw_cluster1_count = params_from_base_suite_setup["sgw_cluster1_count"]
    sgw_cluster2_count = params_from_base_suite_setup["sgw_cluster2_count"]
    no_conflicts_enabled = params_from_base_suite_setup["no_conflicts_enabled"]
    upgraded_no_conflicts_enabled = params_from_base_suite_setup["upgraded_no_conflicts_enabled"]

    test_name = request.node.name

    source_db = None
    source_db2 = None
    test_name_cp = test_name.replace("/", "-")
    log_filename = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__,
                                                 test_name_cp,
                                                 datetime.datetime.now())

    if not use_local_testserver and create_db_per_test:
        log_info("Starting TestServer...")
        if device_enabled:
            testserver.start_device(log_filename)
        else:
            testserver.start(log_filename)

    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config=cluster_config)
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]

    log_info("Running test '{}'".format(test_name))
    log_info("cluster_config: {}".format(cluster_config))
    log_info("cluster_topology: {}".format(cluster_topology))
    log_info("mode: {}".format(mode))
    log_info("xattrs_enabled: {}".format(xattrs_enabled))
    db_config = None

    db = None
    cbl_db = None
    cbl_db2 = None
    test_db_log_file = None
    path = None
    if create_db_per_test:
        if enable_file_logging and liteserv_version >= "2.5.0":
            cbllog = FileLogging(base_url)
            cbllog.configure(log_level="verbose", max_rotate_count=2,
                             max_size=100000 * 512, plain_text=True)
            test_db_log_file = cbllog.get_directory()
            log_info("Log files available at - {}".format(test_db_log_file))
        cbl_db = create_db_per_test + str(time.time())
        cbl_db2 = create_db_per_test + "-2-" + str(time.time())
        # Create CBL database
        db = Database(base_url)

        log_info("Creating a Database {} at test setup".format(cbl_db))
        db_config = db.configure()
        source_db = db.create(cbl_db, db_config)
        source_db2 = db.create(cbl_db2, db_config)
        log_info("Getting the database name")
        db_name = db.getName(source_db)
        assert db_name == cbl_db
        path = db.getPath(source_db).rstrip("/\\")
        path2 = db.getPath(source_db2).rstrip("/\\")
        if '\\' in path:
            path = '\\'.join(path.split('\\')[:-1])
            path2 = '\\'.join(path2.split('\\')[:-1])
        else:
            path = '/'.join(path.split('/')[:-1])
            path2 = '/'.join(path2.split('/')[:-1])

    # This dictionary is passed to each test
    yield {
        "cluster_config": cluster_config,
        "mode": mode,
        "server_version": server_version,
        "sync_gateway_version": sync_gateway_version,
        "server_upgraded_version": server_upgraded_version,
        "sync_gateway_upgraded_version": sync_gateway_upgraded_version,
        "cbs_ssl": cbs_ssl,
        "sg_ssl": sg_ssl,
        "xattrs_enabled": xattrs_enabled,
        "use_views": use_views,
        "number_replicas": number_replicas,
        "delta_sync_enabled": delta_sync_enabled,
        "upgraded_cbs_ssl": upgraded_cbs_ssl,
        "upgraded_sg_ssl": upgraded_sg_ssl,
        "upgraded_xattrs_enabled": upgraded_xattrs_enabled,
        "upgraded_use_views": upgraded_use_views,
        "upgraded_number_replicas": upgraded_number_replicas,
        "upgraded_delta_sync_enabled": upgraded_delta_sync_enabled,
        "liteserv_host": liteserv_host,
        "liteserv_port": liteserv_port,
        "liteserv_version": liteserv_version,
        "liteserv_platform": liteserv_platform,
        "device_enabled": device_enabled,
        "base_url": base_url,
        "target1_url": target1_url,
        "target1_admin_url": target1_admin_url,
        "target2_url": target2_url,
        "target2_admin_url": target2_admin_url,
        "sg1_ip": sg1_ip,
        "sg3_ip": sg3_ip,
        "source_db": source_db,
        "source_db2": source_db2,
        "db": db,
        "num_docs": num_docs,
        "cbs_platform": cbs_platform,
        "cbs_toy_build": cbs_toy_build,
        "sg_config": sg_config,
        "cluster_topology": cluster_topology,
        "sg_url": sg_url,
        "sg_admin_url": sg_admin_url,
        "cbl_db": cbl_db,
        "stop_replication_before_upgrade": stop_replication_before_upgrade,
        "sgw_cluster1_count": sgw_cluster1_count,
        "sgw_cluster2_count": sgw_cluster2_count,
        "no_conflicts_enabled": no_conflicts_enabled,
        "upgraded_no_conflicts_enabled": upgraded_no_conflicts_enabled
    }

    log_info("Tearing down test")
    if create_db_per_test:
        # Delete CBL database
        log_info("Deleting the database {} at test teardown".format(create_db_per_test))
        time.sleep(1)
        try:
            if db.exists(cbl_db, path):
                db.deleteDB(source_db)
            if db.exists(cbl_db2, path2):
                db.deleteDB(source_db2)
            log_info("Flushing server memory")
            utils_obj = Utils(base_url)
            utils_obj.flushMemory()
            log_info("Stopping the test server per test")
            if not use_local_testserver:
                testserver.stop()
        except Exception as err:
            log_info("Exception occurred: {}".format(err))


@pytest.fixture(scope="function")
def setup_customized_teardown_test(params_from_base_test_setup):
    cbl_db_name1 = "cbl_db1" + str(time.time())
    cbl_db_name2 = "cbl_db2" + str(time.time())
    cbl_db_name3 = "cbl_db3" + str(time.time())
    base_url = params_from_base_test_setup["base_url"]
    db = Database(base_url)
    db_config = db.configure()
    cbl_db1 = db.create(cbl_db_name1, db_config)
    cbl_db2 = db.create(cbl_db_name2, db_config)
    cbl_db3 = db.create(cbl_db_name3, db_config)
    log_info("setting up all 3 dbs")

    yield{
        "db": db,
        "cbl_db_name1": cbl_db_name1,
        "cbl_db_name2": cbl_db_name2,
        "cbl_db_name3": cbl_db_name3,
        "cbl_db1": cbl_db1,
        "cbl_db2": cbl_db2,
        "cbl_db3": cbl_db3,
    }
    log_info("Tearing down test")
    path = db.getPath(cbl_db1).rstrip("/\\")
    path2 = db.getPath(cbl_db2).rstrip("/\\")
    path3 = db.getPath(cbl_db3).rstrip("/\\")
    if '\\' in path:
        path = '\\'.join(path.split('\\')[:-1])
        path2 = '\\'.join(path2.split('\\')[:-1])
        path3 = '\\'.join(path3.split('\\')[:-1])
    else:
        path = '/'.join(path.split('/')[:-1])
        path2 = '/'.join(path2.split('/')[:-1])
        path3 = '/'.join(path3.split('/')[:-1])
    try:
        if db.exists(cbl_db_name1, path):
            db.deleteDB(cbl_db1)
        if db.exists(cbl_db_name2, path2):
            db.deleteDB(cbl_db2)
        if db.exists(cbl_db_name3, path2):
            db.deleteDB(cbl_db3)
    except Exception as err:
        log_info("Exception occurred: {}".format(err))
