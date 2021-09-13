import time
import datetime
import pytest

from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords.utils import host_for_url, clear_resources_pngs
from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.TestServerFactory import TestServerFactory
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.exceptions import ProvisioningError
from keywords.tklogging import Logging
from CBLClient.Database import Database
from CBLClient.Query import Query
from CBLClient.Utils import Utils
from keywords.constants import RESULTS_DIR
from CBLClient.FileLogging import FileLogging


def pytest_addoption(parser):
    parser.addoption("--use-local-testserver",
                     action="store_true",
                     help="Skip installing testserver at setup",
                     default=False)

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

    parser.addoption("--liteserv-platforms",
                     action="store",
                     help="liteserv-platforms: the platforms to assign to the liteserv")

    parser.addoption("--liteserv-versions",
                     action="store",
                     help="liteserv-versions: the versions to download / install for the liteserv")

    parser.addoption("--liteserv-hosts",
                     action="store",
                     help="liteserv-hosts: the hosts to start liteserv on")

    parser.addoption("--liteserv-ports",
                     action="store",
                     help="liteserv-ports: the ports to assign to liteserv")

    parser.addoption("--liteserv-android-serial-numbers",
                     action="store",
                     help="liteserv-android-serial-numbers: the android device serial numbers")

    parser.addoption("--enable-sample-bucket",
                     action="store",
                     help="enable-sample-bucket: Enable a sample server bucket")

    parser.addoption("--xattrs",
                     action="store_true",
                     help="xattrs: Enable xattrs for sync gateway")

    parser.addoption("--no-conflicts",
                     action="store_true",
                     help="If set, allow_conflicts is set to false in sync-gateway config")

    parser.addoption("--doc-generator",
                     action="store",
                     help="Provide the doc generator type. Valid values are - simple, four_k, simple_user and"
                          " complex_doc",
                     default="simple")

    parser.addoption("--resume-cluster", action="store_true",
                     help="Enable System test to start without reseting cluster", default=False)

    parser.addoption("--no-db-delete", action="store_true",
                     help="Enable System test to start without reseting cluster", default=False)

    parser.addoption("--device", action="store_true",
                     help="Enable device if you want to run it on device", default=False)

    parser.addoption("--community", action="store_true",
                     help="If set, community edition will get picked up , default is enterprise", default=False)

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

    parser.addoption("--cluster-config",
                     action="store",
                     help="Provide cluster config to use. Default is base config",
                     default="base")

    parser.addoption("--enable-file-logging",
                     action="store_true",
                     help="If set, CBL file logging would enable. Supported only cbl2.5 onwards")

    parser.addoption("--enable-rebalance",
                     action="store_true",
                     default=False,
                     help="If set, CBS not would be rebalance in/out of cluster")

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

    parser.addoption("--num-of-docs",
                     action="store",
                     default="10000",
                     help="Specify the initial no. of docs for an app to start the system test. Default is 10k Docs per cbl db")

    parser.addoption("--num-of-doc-updates",
                     action="store",
                     default="100",
                     help="Specify the no. of times a random doc will be update. Default is 100 times")

    parser.addoption("--num-of-docs-to-update",
                     action="store",
                     default="100",
                     help="Specify the no. of random doc to update in each iteration. Default is 100 times")

    parser.addoption("--num-of-docs-to-delete",
                     action="store",
                     default="100",
                     help="Specify the no. of random docs to delete in each iteration. Default is 1000 times."
                          "In each iteration twice the no. of docs specified will be deleted. Once from SG side and "
                          "once from all cbl app in cluster")

    parser.addoption("--num-of-docs-in-itr",
                     action="store",
                     default="1000",
                     help="Specify the max no. of docs that be created in one batch of create doc. "
                          "Default is 1000 times")

    parser.addoption("--num-of-docs-to-add",
                     action="store",
                     default="2000",
                     help="Specify the no. of random docs to add in each iteration per cbl app. Default is 2000 times")

    parser.addoption("--up-time",
                     action="store",
                     default="1",
                     help="Specify the no. of days system test will execute. Default is 1 days")

    parser.addoption("--repl-status-check-sleep-time",
                     action="store",
                     default="20",
                     help="Specify the time for replicator to sleep before it polls again for replication status")

    parser.addoption("--hide-product-version",
                     action="store_true",
                     help="Hides SGW product version when you hit SGW url",
                     default=False)

    parser.addoption("--enable-cbs-developer-preview",
                     action="store_true",
                     help="Enabling CBS developer preview",
                     default=False)

    parser.addoption("--disable-persistent-config",
                     action="store_true",
                     help="Disable Centralized Persistent Config")

    parser.addoption("--enable-server-tls-skip-verify",
                     action="store_true",
                     help="Enable Server tls skip verify config")

    parser.addoption("--disable-tls-server",
                     action="store_true",
                     help="Disable tls server")

    parser.addoption("--disable-admin-auth",
                     action="store_true",
                     help="Disable Admin auth")

    parser.addoption("--server-ssl",
                     action="store_true",
                     help="If set, will enable SSL communication between server and Sync Gateway")


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/CBLTester/CBL_Functional_tests/ directory
@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    use_local_testserver = request.config.getoption("--use-local-testserver")
    liteserv_platforms = request.config.getoption("--liteserv-platforms")
    liteserv_versions = request.config.getoption("--liteserv-versions")
    liteserv_hosts = request.config.getoption("--liteserv-hosts")
    liteserv_ports = request.config.getoption("--liteserv-ports")
    liteserv_android_serial_numbers = request.config.getoption("--liteserv-android-serial-numbers")

    platform_list = liteserv_platforms.split(',')
    version_list = liteserv_versions.split(',')
    host_list = liteserv_hosts.split(',')
    port_list = liteserv_ports.split(',')
    liteserv_android_serial_number = []
    if liteserv_android_serial_numbers:
        liteserv_android_serial_number = liteserv_android_serial_numbers.split(',')

    if len(platform_list) != len(version_list) != len(host_list) != len(port_list):
        raise Exception("Provide equal no. of Parameters for host, port, version and platforms")
    skip_provisioning = request.config.getoption("--skip-provisioning")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    disable_tls_server = request.config.getoption("--disable-tls-server")
    mode = request.config.getoption("--mode")

    server_version = request.config.getoption("--server-version")
    enable_sample_bucket = request.config.getoption("--enable-sample-bucket")
    xattrs_enabled = request.config.getoption("--xattrs")
    device_enabled = request.config.getoption("--device")
    sg_ssl = request.config.getoption("--sg-ssl")
    resume_cluster = request.config.getoption("--resume-cluster")
    generator = request.config.getoption("--doc-generator")
    no_db_delete = request.config.getoption("--no-db-delete")
    use_views = request.config.getoption("--use-views")
    number_replicas = request.config.getoption("--number-replicas")
    cluster_config_prefix = request.config.getoption("--cluster-config")
    enable_rebalance = request.config.getoption("--enable-rebalance")
    enable_file_logging = request.config.getoption("--enable-file-logging")
    delta_sync_enabled = request.config.getoption("--delta-sync")
    cbs_ssl = request.config.getoption("--server-ssl")

    community_enabled = request.config.getoption("--community")

    enable_encryption = request.config.getoption("--enable-encryption")
    encryption_password = request.config.getoption("--encryption-password")
    num_of_docs = int(request.config.getoption("--num-of-docs"))
    num_of_doc_updates = int(request.config.getoption("--num-of-doc-updates"))
    num_of_docs_to_update = int(request.config.getoption("--num-of-docs-to-update"))
    num_of_docs_in_itr = int(request.config.getoption("--num-of-docs-in-itr"))
    num_of_docs_to_delete = int(request.config.getoption("--num-of-docs-to-delete"))
    num_of_docs_to_add = int(request.config.getoption("--num-of-docs-to-add"))
    hide_product_version = request.config.getoption("--hide-product-version")
    # test runtime in days, float type allow debug runs specify shorter time, i.e. a quarter day etc.
    up_time = float(request.config.getoption("--up-time"))
    # convert to minutes
    up_time = up_time * 24 * 60
    enable_cbs_developer_preview = request.config.getoption("--enable-cbs-developer-preview")
    disable_persistent_config = request.config.getoption("--disable-persistent-config")
    enable_server_tls_skip_verify = request.config.getoption("--enable-server-tls-skip-verify")
    disable_tls_server = request.config.getoption("--disable-tls-server")

    disable_admin_auth = request.config.getoption("--disable-admin-auth")
    repl_status_check_sleep_time = int(request.config.getoption("--repl-status-check-sleep-time"))
    test_name = request.node.name

    # ================================================ #
    # prepare testserver app for each cbl client
    # testserver app download + install
    # ================================================ #
    testserver_list = []
    android_device_idx = 0
    for platform, version, host, port in zip(platform_list,
                                             version_list,
                                             host_list,
                                             port_list):
        testserver = TestServerFactory.create(platform=platform,
                                              version_build=version,
                                              host=host,
                                              port=port,
                                              community_enabled=community_enabled)

        if not use_local_testserver:
            log_info("Downloading TestServer ...")
            # Download TestServer app
            testserver.download()

            # Install TestServer app
            if device_enabled and (platform == "ios" or platform == "android"):
                if platform == "android" and len(liteserv_android_serial_number) != 0:
                    testserver.serial_number = liteserv_android_serial_number[android_device_idx]
                    android_device_idx += 1
                testserver.install_device()
            else:
                testserver.install()

        testserver_list.append(testserver)

    # ================================================ #
    # prepare couchbase server and sync gateway cluster
    # ================================================ #
    cluster_config = "{}/{}_{}".format(CLUSTER_CONFIGS_DIR, cluster_config_prefix, mode)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default", mode)
    no_conflicts_enabled = request.config.getoption("--no-conflicts")
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    sg_db = "db"
    sg_url = cluster_topology["sync_gateways"][0]["public"]
    sg_ip = host_for_url(sg_url)
    target_url = "ws://{}:4984/{}".format(sg_ip, sg_db)
    target_admin_url = "ws://{}:4985/{}".format(sg_ip, sg_db)
    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)

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
    # Write the number of replicas to cluster config
    persist_cluster_config_environment_prop(cluster_config, 'number_replicas', number_replicas)

    if hide_product_version:
        log_info("Suppress the SGW product Version")
        persist_cluster_config_environment_prop(cluster_config, 'hide_product_version', True)
    else:
        log_info("Running without suppress SGW product Version")
        persist_cluster_config_environment_prop(cluster_config, 'hide_product_version', False)
    # As cblite jobs run with on Centos platform, adding by default centos to environment config
    persist_cluster_config_environment_prop(cluster_config, 'sg_platform', "centos", False)

    if enable_cbs_developer_preview:
        log_info("Enable CBS developer preview")
        persist_cluster_config_environment_prop(cluster_config, 'cbs_developer_preview', True)
    else:
        log_info("Running without CBS developer preview")
        persist_cluster_config_environment_prop(cluster_config, 'cbs_developer_preview', False)

    if cbs_ssl:
        log_info("Running tests with cbs <-> sg ssl enabled")
        # Enable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', True)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', False)

    if disable_persistent_config:
        log_info(" disable persistent config")
        persist_cluster_config_environment_prop(cluster_config, 'disable_persistent_config', True)
    else:
        log_info("Running without Centralized Persistent Config")
        persist_cluster_config_environment_prop(cluster_config, 'disable_persistent_config', False)

    if enable_server_tls_skip_verify:
        log_info("Enable server tls skip verify flag")
        persist_cluster_config_environment_prop(cluster_config, 'server_tls_skip_verify', True)
    else:
        log_info("Running without server_tls_skip_verify Config")
        persist_cluster_config_environment_prop(cluster_config, 'server_tls_skip_verify', False)

    if disable_tls_server:
        log_info("Disable tls server flag")
        persist_cluster_config_environment_prop(cluster_config, 'disable_tls_server', True)
    else:
        log_info("Enable tls server flag")
        persist_cluster_config_environment_prop(cluster_config, 'disable_tls_server', False)

    if disable_admin_auth:
        log_info("Disabled Admin Auth")
        persist_cluster_config_environment_prop(cluster_config, 'disable_admin_auth', True)
    else:
        log_info("Enabled Admin Auth")
        persist_cluster_config_environment_prop(cluster_config, 'disable_admin_auth', False)

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

    # update sgw urls to meet the runtime settings
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config=cluster_config)
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    log_info("sg_url: {}".format(sg_url))
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    log_info("sg_admin_url: {}".format(sg_admin_url))

    # ================================================ #
    # prepare testserver app on cbl client
    # start testserver app, setup log config, etc
    # ================================================ #
    base_url_list = []
    for host, port in zip(host_list, port_list):
        base_url_list.append("http://{}:{}".format(host, port))

    # Create CBL databases on all devices
    cbl_db_name_list = []
    cbl_db_obj_list = []
    testkit_db_obj_list = []
    query_obj_list = []
    # Start Test server which needed for suite level set up like query tests
    for testserver, platform in zip(testserver_list, platform_list):
        if not use_local_testserver:
            log_info("Starting TestServer...")
            test_name_cp = test_name.replace("/", "-")
            if device_enabled and (platform == "ios" or platform == "android"):
                testserver.start_device("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__,
                                                                      test_name_cp, datetime.datetime.now()))
            else:
                testserver.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__, test_name_cp,
                                                               datetime.datetime.now()))

    for base_url, i, liteserv_version in zip(base_url_list, range(len(base_url_list)), version_list):
        if enable_file_logging and liteserv_version >= "2.5.0":
            cbllog = FileLogging(base_url)
            cbllog.configure(log_level="verbose", max_rotate_count=2,
                             max_size=1000 * 512 * 4, plain_text=True)
            log_info("Log files available at - {}".format(cbllog.get_directory()))

        db_name = "{}-{}-{}".format("cbl-sys-test", i + 1, str(time.time()))
        log_info("db name for {} is {}".format(base_url, db_name))
        cbl_db_name_list.append(db_name)
        db = Database(base_url)
        query_obj_list.append(Query(base_url))
        testkit_db_obj_list.append(db)

        log_info("Creating a Database {} at the suite setup".format(db_name))
        if enable_encryption:
            db_config = db.configure(password=encryption_password)
        else:
            db_config = db.configure()
        cbl_db = db.create(db_name, db_config)
        cbl_db_obj_list.append(cbl_db)
        log_info("Getting the database name")
        assert db.getName(cbl_db) == db_name
        if resume_cluster:
            path = db.getPath(cbl_db).rstrip("/\\")
            if '\\' in path:
                path = '\\'.join(path.split('\\')[:-1])
            else:
                path = '/'.join(path.split('/')[:-1])
            assert db.exists(db_name, path)

    yield {
        "cluster_config": cluster_config,
        "mode": mode,
        "xattrs_enabled": xattrs_enabled,
        "platform_list": platform_list,
        "cluster_topology": cluster_topology,
        "version_list": version_list,
        "host_list": host_list,
        "port_list": port_list,
        "target_url": target_url,
        "sg_ip": sg_ip,
        "sg_db": sg_db,
        "sg_url": sg_url,
        "sg_admin_url": sg_admin_url,
        "no_conflicts_enabled": no_conflicts_enabled,
        "sync_gateway_version": sync_gateway_version,
        "disable_tls_server": disable_tls_server,
        "target_admin_url": target_admin_url,
        "enable_sample_bucket": enable_sample_bucket,
        "cbl_db_obj_list": cbl_db_obj_list,
        "cbl_db_name_list": cbl_db_name_list,
        "base_url_list": base_url_list,
        "query_obj_list": query_obj_list,
        "sg_config": sg_config,
        "testkit_db_obj_list": testkit_db_obj_list,
        "device_enabled": device_enabled,
        "generator": generator,
        "resume_cluster": resume_cluster,
        "enable_rebalance": enable_rebalance,
        "enable_encryption": enable_encryption,
        "encryption_password": encryption_password,
        "enable_file_logging": enable_file_logging,
        "delta_sync_enabled": delta_sync_enabled,
        "num_of_docs": num_of_docs,
        "num_of_docs_to_delete": num_of_docs_to_delete,
        "num_of_docs_in_itr": num_of_docs_in_itr,
        "num_of_docs_to_add": num_of_docs_to_add,
        "num_of_docs_to_update": num_of_docs_to_update,
        "num_of_doc_updates": num_of_doc_updates,
        "up_time": up_time,
        "repl_status_check_sleep_time": repl_status_check_sleep_time,
        "hide_product_version": hide_product_version
    }

    for cbl_db, db_obj, base_url in zip(cbl_db_obj_list, testkit_db_obj_list, base_url_list):
        if not no_db_delete:
            log_info("Deleting the database {} at the suite teardown".format(db_obj.getName(cbl_db)))
            time.sleep(2)
            db_obj.deleteDB(cbl_db)

    # Flush all the memory contents on the server app
    for base_url, testserver in zip(base_url_list, testserver_list):
        log_info("Flushing server memory")
        utils_obj = Utils(base_url)
        utils_obj.flushMemory()
        if not use_local_testserver:
            log_info("Stopping the test server")
            testserver.stop()

    clear_resources_pngs()
