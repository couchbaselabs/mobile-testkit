import time
import pytest
import datetime

from CBLClient.PeerToPeer import PeerToPeer
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords.utils import log_info
from keywords.utils import host_for_url
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

    parser.addoption("--enable-sample-bucket",
                     action="store",
                     help="enable-sample-bucket: Enable a sample server bucket")

    parser.addoption("--xattrs",
                     action="store_true",
                     help="xattrs: Enable xattrs for sync gateway")

    parser.addoption("--create-db-per-suite",
                     action="store",
                     help="create-db-per-suite: Creates/deletes client DB per suite")

    parser.addoption("--no-conflicts",
                     action="store_true",
                     help="If set, allow_conflicts is set to false in sync-gateway config")

    parser.addoption("--doc-generator",
                     action="store",
                     help="Provide the doc generator type. Valid values are - simple, four_k, simple_user and complex_doc",
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

    parser.addoption("--create-db-per-test",
                     action="store",
                     help="create-db-per-test: Creates/deletes client DB for every test",
                     default="test")


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/CBLTester/CBL_Functional_tests/ directory
@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    liteserv_platforms = request.config.getoption("--liteserv-platforms")
    liteserv_versions = request.config.getoption("--liteserv-versions")
    liteserv_hosts = request.config.getoption("--liteserv-hosts")
    liteserv_ports = request.config.getoption("--liteserv-ports")

    platform_list = liteserv_platforms.split(',')
    version_list = liteserv_versions.split(',')
    host_list = liteserv_hosts.split(',')
    port_list = liteserv_ports.split(',')

    if len(platform_list) != len(version_list) != len(host_list) != len(port_list):
        raise Exception("Provide equal no. of Parameters for host, port, version and platforms")
    skip_provisioning = request.config.getoption("--skip-provisioning")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
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
    create_db_per_test = request.config.getoption("--create-db-per-test")
    create_db_per_suite = request.config.getoption("--create-db-per-suite")

    community_enabled = request.config.getoption("--community")

    test_name = request.node.name
    # testserver_list = []
    # for platform, version, host, port in zip(platform_list,
    #                                          version_list,
    #                                          host_list,
    #                                          port_list):
    #     testserver = TestServerFactory.create(platform=platform,
    #                                           version_build=version,
    #                                           host=host,
    #                                           port=port,
    #                                           community_enabled=community_enabled)
    #
    #     log_info("Downloading TestServer ...")
    #     # Download TestServer app
    #     testserver.download()
    #
    #     # Install TestServer app
    #     if device_enabled and platform == "ios":
    #         testserver.install_device()
    #     else:
    #         testserver.install()
    #     testserver_list.append(testserver)
    base_url_list = []
    for host, port in zip(host_list, port_list):
        base_url_list.append("http://{}:{}".format(host, port))

    cluster_config = "{}/{}_{}".format(CLUSTER_CONFIGS_DIR, cluster_config_prefix, mode)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default", mode)
    no_conflicts_enabled = request.config.getoption("--no-conflicts")
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    sg_db = "db"
    sg_url = cluster_topology["sync_gateways"][0]["public"]
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_url)
    target_url = "ws://{}:4984/{}".format(sg_ip, sg_db)
    target_admin_url = "ws://{}:4985/{}".format(sg_ip, sg_db)
    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)

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

    # Write the number of replicas to cluster config
    persist_cluster_config_environment_prop(cluster_config, 'number_replicas', number_replicas)

    if sg_ssl:
        log_info("Enabling SSL on sync gateway")
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', True)
        target_url = "wss://{}:4984/{}".format(sg_ip, sg_db)
        target_admin_url = "wss://{}:4985/{}".format(sg_ip, sg_db)

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

    # Create CBL databases on all devices
    db_name_list = []
    cbl_db_list = []
    db_obj_list = []
    query_obj_list = []
    if create_db_per_suite:
        # Start Test server which needed for suite level set up like query tests
        # for testserver in testserver_list:
        #     log_info("Starting TestServer...")
        #     test_name_cp = test_name.replace("/", "-")
        #     if device_enabled:
        #         testserver.start_device("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__, test_name_cp, datetime.datetime.now()))
        #     else:
        #         testserver.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__, test_name_cp, datetime.datetime.now()))
        for base_url, i in zip(base_url_list, range(len(base_url_list))):
            db_name = "{}_{}_{}".format(create_db_per_suite, str(time.time()), i + 1)
            log_info("db name for {} is {}".format(base_url, db_name))
            db_name_list.append(db_name)
            db = Database(base_url)
            query_obj_list.append(Query(base_url))
            db_obj_list.append(db)

            log_info("Creating a Database {} at the suite setup".format(db_name))
            db_config = db.configure()
            cbl_db = db.create(db_name, db_config)
            cbl_db_list.append(cbl_db)
            log_info("Getting the database name")
            assert db.getName(cbl_db) == db_name
            if resume_cluster:
                path = db.getPath(cbl_db)
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
        "target_admin_url": target_admin_url,
        "enable_sample_bucket": enable_sample_bucket,
        "cbl_db_list": cbl_db_list,
        "db_name_list": db_name_list,
        "base_url_list": base_url_list,
        "query_obj_list": query_obj_list,
        "sg_config": sg_config,
        "db_obj_list": db_obj_list,
        "device_enabled": device_enabled,
        "generator": generator,
        "resume_cluster": resume_cluster,
        "create_db_per_test": create_db_per_test
    }

    # Delete CBL database
#     for db_name, testserver, base_url in zip(db_name_list,
#                                              testserver_list,
#                                              base_url_list):
    if create_db_per_suite:
        for cbl_db, db_obj, base_url in zip(cbl_db_list, db_obj_list, base_url_list):
            if not no_db_delete:
                print "The base url is ", base_url
                log_info("Deleting the database {} at the suite teardown".format(db_obj.getName(cbl_db)))
#                 time.sleep(5)
                db_obj.deleteDB(cbl_db)

        # Flush all the memory contents on the server app
    for base_url in base_url_list:
        log_info("Flushing server memory")
        utils_obj = Utils(base_url)
        utils_obj.flushMemory()
        # log_info("Stopping the test server")
        # testserver.stop()


@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    cluster_config = params_from_base_suite_setup["cluster_config"]
    mode = params_from_base_suite_setup["mode"]
    xattrs_enabled = params_from_base_suite_setup["xattrs_enabled"]
    platform_list = params_from_base_suite_setup["platform_list"]
    host_list = params_from_base_suite_setup["host_list"]
    version_list = params_from_base_suite_setup["version_list"]
    host_list = params_from_base_suite_setup["host_list"]
    port_list = params_from_base_suite_setup["port_list"]
    target_url = params_from_base_suite_setup["target_url"]
    sg_ip = params_from_base_suite_setup["sg_ip"]
    sg_db = params_from_base_suite_setup["sg_db"]
    sg_url = params_from_base_suite_setup["sg_url"]
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    no_conflicts_enabled = params_from_base_suite_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    target_admin_url = params_from_base_suite_setup["target_admin_url"]
    enable_sample_bucket = params_from_base_suite_setup["enable_sample_bucket"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    base_url_list = params_from_base_suite_setup["base_url_list"]
    query_obj_list = params_from_base_suite_setup["query_obj_list"]
    sg_config = params_from_base_suite_setup["sg_config"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    device_enabled = params_from_base_suite_setup["device_enabled"]
    generator = params_from_base_suite_setup["generator"]
    resume_cluster = params_from_base_suite_setup["resume_cluster"]
    create_db_per_test = params_from_base_suite_setup["create_db_per_test"]
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    # testserver_list = params_from_base_suite_setup["testserver_list"]
    # test_name = request.node.name

    if create_db_per_test:
        db_name_list = []
        cbl_db_list = []
        db_obj_list = []
        for base_url, i in zip(base_url_list, range(len(base_url_list))):
            """log_info("Starting TestServer...")
            test_name_cp = test_name.replace("/", "-")
            log_filename = "{}-{}/logs/{}-{}-{}.txt".format("testserver-",RESULTS_DIR, type(testserver).__name__, test_name_cp, datetime.datetime.now())
            if device_enabled:
                testserver.start_device(log_filename)
            else:
                testserver.start(log_filename)
            """
            db_name = "{}_{}_{}".format(create_db_per_test, str(time.time()), i + 1)
            log_info("db name for {} is {}".format(base_url, db_name))
            db_name_list.append(db_name)
            db = Database(base_url)
            query_obj_list.append(Query(base_url))
            db_obj_list.append(db)

            log_info("Creating a Database {} at the test setup".format(db_name))
            db_config = db.configure()
            cbl_db = db.create(db_name, db_config)
            cbl_db_list.append(cbl_db)
            log_info("Getting the database name")
            assert db.getName(cbl_db) == db_name
            if resume_cluster:
                path = db.getPath(cbl_db)
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
        "target_admin_url": target_admin_url,
        "enable_sample_bucket": enable_sample_bucket,
        "cbl_db_list": cbl_db_list,
        "db_name_list": db_name_list,
        "base_url_list": base_url_list,
        "query_obj_list": query_obj_list,
        "sg_config": sg_config,
        "db_obj_list": db_obj_list,
        # "testserver_list": testserver_list,
        "device_enabled": device_enabled,
        "generator": generator,
        "resume_cluster": resume_cluster
    }

    if create_db_per_test:
        for cbl_db, db_obj, base_url in zip(cbl_db_list, db_obj_list, base_url_list):
            log_info("Deleting the database {} at the test teardown".format(db_obj.getName(cbl_db)))
#             time.sleep(5)
            db_obj.deleteDB(cbl_db)


@pytest.fixture(scope="function")
def server_setup(params_from_base_test_setup):
    base_url_list = params_from_base_test_setup["base_url_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    base_url_server = base_url_list[0]
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    replicatorTcpListener = peerToPeer_server.server_start(cbl_db_server)
    log_info("server starting .....")
    yield{
        "replicatorTcpListener": replicatorTcpListener,
        "peerToPeer_server": peerToPeer_server,
        "base_url_list": base_url_list,
        "base_url_server": base_url_server,
        "cbl_db_server": cbl_db_server,
        "cbl_db_list": cbl_db_list
    }
    peerToPeer_server.server_stop(replicatorTcpListener)