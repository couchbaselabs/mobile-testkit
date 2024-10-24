import pytest
import time
import datetime

from keywords.utils import log_info
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, get_cluster
from keywords.ClusterKeywords import ClusterKeywords
from keywords.couchbaseserver import CouchbaseServer
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.exceptions import ProvisioningError
from keywords.tklogging import Logging

from CBLClient.Database import Database
from CBLClient.FileLogging import FileLogging
from keywords.utils import host_for_url, clear_resources_pngs

from CBLClient.Utils import Utils
from keywords.TestServerFactory import TestServerFactory
from keywords.SyncGateway import SyncGateway
from keywords.constants import RESULTS_DIR


def pytest_addoption(parser):
    parser.addoption("--mode",
                     action="store",
                     help="Sync Gateway mode to run the test in, 'cc' for channel cache or 'di' for distributed index")

    parser.addoption("--skip-provisioning",
                     action="store_true",
                     help="Skip cluster provisioning at setup",
                     default=False)

    parser.addoption("--use-local-testserver",
                     action="store_true",
                     help="Skip download and launch TestServer, use local debug build",
                     default=False)

    parser.addoption("--server-version",
                     action="store",
                     help="server-version: Couchbase Server version to install (ex. 4.5.0 or 4.5.0-2601)")

    parser.addoption("--sync-gateway-version",
                     action="store",
                     help="sync-gateway-version: Sync Gateway version to install (ex. 1.3.1-16 or 590c1c31c7e83503eff304d8c0789bdd268d6291)")

    parser.addoption("--liteserv-platform",
                     action="store",
                     help="liteserv-platform: the platform to assign to the liteserv")

    parser.addoption("--liteserv-version",
                     action="store",
                     help="liteserv-version: the version to download / install for the liteserv")

    parser.addoption("--liteserv-host",
                     action="store",
                     help="liteserv-host: the host to start liteserv on")

    parser.addoption("--liteserv-port",
                     action="store",
                     help="liteserv-port: the port to assign to liteserv")

    parser.addoption("--enable-sample-bucket",
                     action="store",
                     help="enable-sample-bucket: Enable a sample server bucket")

    parser.addoption("--xattrs",
                     action="store_true",
                     help="xattrs: Enable xattrs for sync gateway")

    parser.addoption("--create-db-per-test",
                     action="store",
                     help="create-db-per-test: Creates/deletes client DB for every test")

    parser.addoption("--create-db-per-suite",
                     action="store",
                     help="create-db-per-suite: Creates/deletes client DB per suite")

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

    parser.addoption("--flush-memory-per-test",
                     action="store_true",
                     help="If set, will flush server memory per test")

    parser.addoption("--debug-mode", action="store_true",
                     help="Enable debug mode for the app ", default=False)

    parser.addoption("--use-views",
                     action="store_true",
                     help="If set, uses views instead of GSI - SG 2.1 and above only")

    parser.addoption("--enable-file-logging",
                     action="store_true",
                     help="If set, CBL file logging would enable. Supported only cbl2.5 onwards")

    parser.addoption("--number-replicas",
                     action="store",
                     help="Number of replicas for the indexer node - SG 2.1 and above only",
                     default=0)

    parser.addoption("--enable-encryption",
                     action="store_true",
                     help="Encryption will be enabled for CBL db",
                     default=True)

    parser.addoption("--encryption-password",
                     action="store",
                     help="Encryption will be enabled for CBL db",
                     default="password")

    parser.addoption("--delta-sync",
                     action="store_true",
                     help="delta-sync: Enable delta-sync for sync gateway")

    parser.addoption("--enable-cbs-developer-preview",
                     action="store_true",
                     help="Enabling CBS developer preview",
                     default=False)

# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/CBLTester/topology_sync_gateways/multiple_sync_gateways directory


@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    liteserv_platform = request.config.getoption("--liteserv-platform")
    liteserv_version = request.config.getoption("--liteserv-version")
    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")

    skip_provisioning = request.config.getoption("--skip-provisioning")
    use_local_testserver = request.config.getoption("--use-local-testserver")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    disable_tls_server = request.config.getoption("--disable-tls-server")
    mode = request.config.getoption("--mode")

    server_version = request.config.getoption("--server-version")
    enable_sample_bucket = request.config.getoption("--enable-sample-bucket")
    xattrs_enabled = request.config.getoption("--xattrs")
    create_db_per_test = request.config.getoption("--create-db-per-test")
    create_db_per_suite = request.config.getoption("--create-db-per-suite")
    device_enabled = request.config.getoption("--device")
    community_enabled = request.config.getoption("--community")
    sg_ssl = request.config.getoption("--sg-ssl")
    flush_memory_per_test = request.config.getoption("--flush-memory-per-test")
    debug_mode = request.config.getoption("--debug-mode")
    use_views = request.config.getoption("--use-views")
    number_replicas = request.config.getoption("--number-replicas")
    enable_file_logging = request.config.getoption("--enable-file-logging")
    delta_sync_enabled = request.config.getoption("--delta-sync")
    enable_encryption = request.config.getoption("--enable-encryption")
    encryption_password = request.config.getoption("--encryption-password")
    enable_cbs_developer_preview = request.config.getoption("--enable-cbs-developer-preview")

    liteserv_host_list = liteserv_host.split(',')
    liteserv_ports = liteserv_port.split(',')
    testserver = TestServerFactory.create(platform=liteserv_platform,
                                          version_build=liteserv_version,
                                          host=liteserv_host_list[0],
                                          port=liteserv_ports[0],
                                          community_enabled=community_enabled,
                                          debug_mode=debug_mode)

    if not use_local_testserver:
        log_info("Downloading TestServer ...")
        # Download TestServer app
        testserver.download()

        # Install TestServer app
        if device_enabled:
            testserver.install_device()
        else:
            testserver.install()

    base_url = "http://{}:{}".format(liteserv_host_list[0], liteserv_ports[0])
    base_url2 = "http://{}:{}".format(liteserv_host_list[1], liteserv_ports[1])
    cluster_config = "{}/multiple_sync_gateways_{}".format(CLUSTER_CONFIGS_DIR, mode)
    no_conflicts_enabled = request.config.getoption("--no-conflicts")
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    sg_db = "db"
    sg_url = cluster_topology["sync_gateways"][0]["public"]
    sg_ip = host_for_url(sg_url)

    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)
    target_url = "ws://{}:4984/{}".format(sg_ip, sg_db)
    target_admin_url = "ws://{}:4985/{}".format(sg_ip, sg_db)

    cbs_url = cluster_topology['couchbase_servers'][0]
    cbs_ip = host_for_url(cbs_url)

    if sg_ssl:
        log_info("Enabling SSL on sync gateway")
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', True)
        target_url = "wss://{}:4984/{}".format(sg_ip, sg_db)
        target_admin_url = "wss://{}:4985/{}".format(sg_ip, sg_db)

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

    if enable_cbs_developer_preview:
        log_info("Enable CBS developer preview")
        persist_cluster_config_environment_prop(cluster_config, 'cbs_developer_preview', True)
    else:
        log_info("Running without CBS developer preview")
        persist_cluster_config_environment_prop(cluster_config, 'cbs_developer_preview', False)

    # As cblite jobs run with on debian platform, adding by default debian to environment config
    persist_cluster_config_environment_prop(cluster_config, 'sg_platform', "debian", False)

    # Write the number of replicas to cluster config
    persist_cluster_config_environment_prop(cluster_config, 'number_replicas', number_replicas)

    sg_config = sync_gateway_config_path_for_mode("listener_tests/multiple_sync_gateways", mode)
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    log_info("no conflicts enabled {}".format(no_conflicts_enabled))

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

    # Hit this intalled running services to verify the correct versions are installed
    cluster_utils.verify_cluster_versions(
        cluster_config,
        expected_server_version=server_version,
        expected_sync_gateway_version=sync_gateway_version
    )
    if enable_sample_bucket and not create_db_per_suite:
        # if enable_sample_bucket and not create_db_per_test:
        raise Exception("enable_sample_bucket has to be used with create_db_per_suite")

    suite_source_db = None
    suite_cbl_db = None
    suite_cbl_db2 = None
    suite_source_db2 = None
    if create_db_per_suite:
        if enable_file_logging and liteserv_version >= "2.5.0":
            cbllog = FileLogging(base_url)
            cbllog.configure(log_level="verbose", max_rotate_count=2,
                             max_size=1000 * 512, plain_text=True)
            log_info("Log files available at - {}".format(cbllog.get_directory()))
        # Create CBL database
        suite_cbl_db = create_db_per_suite
        suite_cbl_db2 = create_db_per_suite
        suite_db = Database(base_url)
        suite_db2 = Database(base_url2)

        log_info("Creating a Database {} at the suite setup".format(suite_cbl_db))
        if enable_encryption:
            db_config = suite_db.configure(password=encryption_password)
            db_config2 = suite_db2.configure(password=encryption_password)
        else:
            db_config = suite_db.configure()
            db_config2 = suite_db2.configure()
        suite_source_db = suite_db.create(suite_cbl_db, db_config)
        suite_source_db2 = suite_db.create(suite_cbl_db2, db_config2)
        log_info("Getting the database name")
        db_name = suite_db.getName(suite_source_db)
        assert db_name == suite_cbl_db

    if enable_sample_bucket:
        server_url = cluster_topology["couchbase_servers"][0]
        server = CouchbaseServer(server_url)
        buckets = server.get_bucket_names()
        if enable_sample_bucket in buckets:
            log_info("Deleting existing {} bucket".format(enable_sample_bucket))
            server.delete_bucket(enable_sample_bucket)
            time.sleep(5)
        log_info("Loading sample bucket {}".format(enable_sample_bucket))
        server.load_sample_bucket(enable_sample_bucket)
        server._create_internal_rbac_bucket_user(enable_sample_bucket, cluster_config=cluster_config)

        # Restart SG after the bucket deletion
        sync_gateways = cluster_topology["sync_gateways"]
        sg_obj = SyncGateway()

        for sg in sync_gateways:
            sg_ip = host_for_url(sg["admin"])
            log_info("Restarting sync gateway {}".format(sg_ip))
            sg_obj.restart_sync_gateways(cluster_config=cluster_config, url=sg_ip)

        if mode == "di":
            ac_obj = SyncGateway()
            sg_accels = cluster_topology["sg_accels"]
            for ac in sg_accels:
                ac_ip = host_for_url(ac)
                log_info("Restarting sg accel {}".format(ac_ip))
                ac_obj.restart_sync_gateways(cluster_config=cluster_config, url=ac_ip)
                time.sleep(5)
        # Create primary index
        password = "password"
        log_info("Connecting to {}/{} with password {}".format(cbs_ip, enable_sample_bucket, password))
        sdk_client = get_cluster('couchbase://{}'.format(cbs_ip), enable_sample_bucket)
        log_info("Creating primary index for {}".format(enable_sample_bucket))
        n1ql_query = 'create primary index on {}'.format(enable_sample_bucket)
        sdk_client.n1ql_query(n1ql_query)

    yield {
        "cluster_config": cluster_config,
        "mode": mode,
        "xattrs_enabled": xattrs_enabled,
        "liteserv_platform": liteserv_platform,
        "cluster_topology": cluster_topology,
        "liteserv_version": liteserv_version,
        "liteserv_host": liteserv_host,
        "liteserv_port": liteserv_port,
        "target_url": target_url,
        "target_admin_url": target_admin_url,
        "sg_ip": sg_ip,
        "sg_db": sg_db,
        "no_conflicts_enabled": no_conflicts_enabled,
        "sync_gateway_version": sync_gateway_version,
        "disable_tls_server": disable_tls_server,
        "base_url": base_url,
        "base_url2": base_url2,
        "enable_sample_bucket": enable_sample_bucket,
        "create_db_per_test": create_db_per_test,
        "suite_source_db": suite_source_db,
        "suite_cbl_db": suite_cbl_db,
        "suite_cbl_db2": suite_cbl_db2,
        "suite_source_db2": suite_source_db2,
        "sg_config": sg_config,
        "testserver": testserver,
        "device_enabled": device_enabled,
        "flush_memory_per_test": flush_memory_per_test,
        "sg_ssl": sg_ssl,
        "delta_sync_enabled": delta_sync_enabled,
        "enable_file_logging": enable_file_logging,
        "enable_encryption": enable_encryption,
        "liteserv_host_list": liteserv_host_list,
        "encryption_password": encryption_password
    }
    if create_db_per_suite:
        # Delete CBL database
        log_info("Deleting the database {} at the suite teardown".format(create_db_per_suite))
        time.sleep(2)
        suite_db.deleteDB(suite_source_db)
        suite_db2.deleteDB(suite_source_db2)
        time.sleep(1)

    # Flush all the memory contents on the server app
    log_info("Flushing server memory")
    utils_obj = Utils(base_url)
    utils_obj.flushMemory()
    log_info("Stopping the test server")
    if not use_local_testserver:
        log_info("Stopping the test server per suite")
        testserver.stop()

    # Delete png files under resources/data
    clear_resources_pngs()


@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    base_url = params_from_base_suite_setup["base_url"]
    base_url2 = params_from_base_suite_setup["base_url2"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    xattrs_enabled = params_from_base_suite_setup["xattrs_enabled"]
    liteserv_host = params_from_base_suite_setup["liteserv_host"]
    liteserv_port = params_from_base_suite_setup["liteserv_port"]
    create_db_per_test = params_from_base_suite_setup["create_db_per_test"]
    no_conflicts_enabled = params_from_base_suite_setup["no_conflicts_enabled"]
    target_admin_url = params_from_base_suite_setup["target_admin_url"]
    suite_source_db = params_from_base_suite_setup["suite_source_db"]
    suite_cbl_db = params_from_base_suite_setup["suite_cbl_db"]
    suite_cbl_db2 = params_from_base_suite_setup["suite_cbl_db2"]
    test_name = request.node.name
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    mode = params_from_base_suite_setup["mode"]
    target_url = params_from_base_suite_setup["target_url"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    disable_tls_server = params_from_base_suite_setup["disable_tls_server"]
    sg_ip = params_from_base_suite_setup["sg_ip"]
    sg_db = params_from_base_suite_setup["sg_db"]
    sg_config = params_from_base_suite_setup["sg_config"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]
    liteserv_version = params_from_base_suite_setup["liteserv_version"]
    testserver = params_from_base_suite_setup["testserver"]
    device_enabled = params_from_base_suite_setup["device_enabled"]
    flush_memory_per_test = params_from_base_suite_setup["flush_memory_per_test"]
    sg_ssl = params_from_base_suite_setup["sg_ssl"]
    enable_file_logging = params_from_base_suite_setup["enable_file_logging"]
    delta_sync_enabled = params_from_base_suite_setup["delta_sync_enabled"]
    encryption_password = params_from_base_suite_setup["encryption_password"]
    enable_encryption = params_from_base_suite_setup["enable_encryption"]
    use_local_testserver = request.config.getoption("--use-local-testserver")
    liteserv_host_list = params_from_base_suite_setup["liteserv_host_list"]
    source_db = None
    cbl_db = None
    db_config = None
    db = None

    # Start LiteServ and delete any databases
    log_info("Starting TestServer...")
    log_info(test_name)
    test_name_cp = test_name.replace("/", "-")

    if not use_local_testserver:
        if device_enabled:
            testserver.start_device("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__, test_name_cp, datetime.datetime.now()))
        else:
            testserver.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__, test_name_cp, datetime.datetime.now()))
        # sleep for some time to reach cbl
        time.sleep(5)

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
    if create_db_per_test:
        if enable_file_logging and liteserv_version >= "2.5.0":
            cbllog = FileLogging(base_url)
            cbllog.configure(log_level="verbose", max_rotate_count=2,
                             max_size=1000 * 512, plain_text=True)
            log_info("Log files available at - {}".format(cbllog.get_directory()))
        cbl_db = create_db_per_test + str(time.time())
        cbl_db2 = create_db_per_test + str(time.time())
        # Create CBL database
        db = Database(base_url)
        db2 = Database(base_url2)
        log_info("Creating a Database {} at test setup".format(cbl_db))
        if enable_encryption:
            db_config = db.configure(password=encryption_password)
            db_config2 = db2.configure(password=encryption_password)
        else:
            db_config = db.configure()
            db_config2 = db2.configure()
        source_db = db.create(cbl_db, db_config)
        source_db2 = db2.create(cbl_db2, db_config2)
        log_info("Getting the database name")
        db_name = db.getName(source_db)
        assert db_name == cbl_db

    # This dictionary is passed to each test
    yield {
        "cluster_config": cluster_config,
        "cluster_topology": cluster_topology,
        "mode": mode,
        "sg_url": sg_url,
        "sg_admin_url": sg_admin_url,
        "xattrs_enabled": xattrs_enabled,
        "liteserv_host": liteserv_host,
        "liteserv_port": liteserv_port,
        "liteserv_platform": liteserv_platform,
        "target_url": target_url,
        "target_admin_url": target_admin_url,
        "sg_ip": sg_ip,
        "sg_db": sg_db,
        "no_conflicts_enabled": no_conflicts_enabled,
        "sync_gateway_version": sync_gateway_version,
        "disable_tls_server": disable_tls_server,
        "source_db": source_db,
        "source_db2": source_db2,
        "cbl_db": cbl_db,
        "cbl_db2": cbl_db2,
        "suite_source_db": suite_source_db,
        "suite_cbl_db": suite_cbl_db,
        "suite_cbl_db2": suite_cbl_db2,
        "base_url": base_url,
        "base_url2": base_url2,
        "sg_config": sg_config,
        "db": db,
        "db2": db2,
        "device_enabled": device_enabled,
        "testserver": testserver,
        "db_config": db_config,
        "sg_ssl": sg_ssl,
        "delta_sync_enabled": delta_sync_enabled,
        "enable_file_logging": enable_file_logging,
        "liteserv_host_list": liteserv_host_list
    }

    log_info("Tearing down test")
    if create_db_per_test:
        # Delete CBL database
        log_info("Deleting the database {} at test teardown".format(create_db_per_test))
        time.sleep(1)
        db.deleteDB(source_db)
        db2.deleteDB(source_db2)

    if flush_memory_per_test:
        log_info("Flushing server memory")
        utils_obj = Utils(base_url)
        utils_obj.flushMemory()
        utils_obj2 = Utils(base_url2)
        utils_obj2.flushMemory()


@pytest.fixture(scope="function")
def setup_customized_teardown_test(params_from_base_test_setup):
    cbl_db_name1 = "cbl_db1" + str(time.time())
    cbl_db_name2 = "cbl_db2" + str(time.time())
    cbl_db_name3 = "cbl_db3" + str(time.time())
    base_url = params_from_base_test_setup["base_url"]
    base_url2 = params_from_base_test_setup["base_url2"]
    db = Database(base_url)
    db_config = db.configure()
    db2 = Database(base_url2)
    db_config2 = db2.configure()
    cbl_db1 = db.create(cbl_db_name1, db_config)
    cbl_db2 = db2.create(cbl_db_name2, db_config2)
    cbl_db3 = db.create(cbl_db_name3, db_config)

    yield{
        "db": db,
        "db2": db2,
        "cbl_db_name1": cbl_db_name1,
        "cbl_db_name2": cbl_db_name2,
        "cbl_db_name3": cbl_db_name3,
        "cbl_db1": cbl_db1,
        "cbl_db2": cbl_db2,
        "cbl_db3": cbl_db3,
    }
    log_info("tearing down all 3 dbs")
    time.sleep(2)
    db.deleteDB(cbl_db1)
    db2.deleteDB(cbl_db2)
    db.deleteDB(cbl_db3)
