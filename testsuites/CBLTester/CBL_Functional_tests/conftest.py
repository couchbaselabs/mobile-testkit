import time
import pytest

from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords.constants import SDK_TIMEOUT
from keywords.utils import log_info
from keywords.utils import host_for_url
from keywords.ClusterKeywords import ClusterKeywords
from keywords.couchbaseserver import CouchbaseServer
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.SyncGateway import SyncGateway
from keywords.exceptions import ProvisioningError
from keywords.tklogging import Logging
from CBLClient.Replicator import Replicator
from CBLClient.BasicAuthenticator import BasicAuthenticator
from CBLClient.Database import Database
from CBLClient.Document import Document
from CBLClient.Dictionary import Dictionary
from CBLClient.DataTypeInitiator import DataTypeInitiator
from CBLClient.SessionAuthenticator import SessionAuthenticator
# from CBLClient.ReplicatorConfiguration import ReplicatorConfiguration
from CBLClient.Utils import Utils

from keywords.utils import host_for_url
from libraries.testkit.cluster import Cluster
from couchbase.bucket import Bucket
from couchbase.n1ql import N1QLQuery


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


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/listener/shared/client_sg/ directory
@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    liteserv_platform = request.config.getoption("--liteserv-platform")
    liteserv_version = request.config.getoption("--liteserv-version")
    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")

    skip_provisioning = request.config.getoption("--skip-provisioning")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    mode = request.config.getoption("--mode")

    server_version = request.config.getoption("--server-version")
    enable_sample_bucket = request.config.getoption("--enable-sample-bucket")
    xattrs_enabled = request.config.getoption("--xattrs")
    create_db_per_test = request.config.getoption("--create-db-per-test")
    create_db_per_suite = request.config.getoption("--create-db-per-suite")

    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, mode)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_travel_sample", mode)
    no_conflicts_enabled = request.config.getoption("--no-conflicts")
    cluster_utils = ClusterKeywords()
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    sg_db = "db"
    cbl_db = None
    sg_url = cluster_topology["sync_gateways"][0]["public"]
    sg_ip = host_for_url(sg_url)
    target_url = "ws://{}:4984/{}".format(sg_ip, sg_db)
    target_admin_url = "ws://{}:4985/{}".format(sg_ip, sg_db)

    cbs_url = cluster_topology['couchbase_servers'][0]
    cbs_ip = host_for_url(cbs_url)

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

    cluster_utils = ClusterKeywords()
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)
    cbs_url = cluster_topology['couchbase_servers'][0]
    cbs_ip = host_for_url(cbs_url)

    cluster = Cluster(cluster_config)

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

    if enable_sample_bucket and not create_db_per_suite:
        raise Exception("enable_sample_bucket has to be used with create_db_per_suite")

    source_db = None
    if create_db_per_suite:
        # Create CBL database
        cbl_db = create_db_per_suite
        db = Database(base_url)

        log_info("Creating a Database {} at the suite setup".format(cbl_db))
        source_db = db.create(cbl_db)
        log_info("Getting the database name")
        db_name = db.getName(source_db)
        assert db_name == cbl_db

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
        server._create_internal_rbac_bucket_user(enable_sample_bucket)

        # Restart SG after the bucket deletion
        sync_gateways = cluster_topology["sync_gateways"]
        sg_obj = SyncGateway()

        for sg in sync_gateways:
            sg_ip = host_for_url(sg["admin"])
            log_info("Restarting sync gateway {}".format(sg_ip))
            sg_obj.restart_sync_gateways(cluster_config=cluster_config, url=sg_ip)
            # Giving time to SG to load all docs into it's cache
            time.sleep(240)

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
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, enable_sample_bucket), password=password, timeout=SDK_TIMEOUT)
        log_info("Creating primary index for {}".format(enable_sample_bucket))
        n1ql_query = 'create primary index on {}'.format(enable_sample_bucket)
        query = N1QLQuery(n1ql_query)
        sdk_client.n1ql_query(query)

        # Start continuous replication
        repl_obj = Replicator(base_url)
        auth_obj = BasicAuthenticator(base_url)
        authenticator = auth_obj.create("traveL-sample", "password")
        repl_config = repl_obj.configure(source_db=source_db,
                                         target_url=target_admin_url,
                                         replication_type="PUSH_AND_PULL",
                                         continuous=True,
                                         replicator_authenticator=authenticator)
        repl = repl_obj.create(repl_config)
        repl_obj.start(repl)
        repl_obj.wait_until_replicator_idle(repl)

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
        "sg_ip": sg_ip,
        "sg_db": sg_db,
        "no_conflicts_enabled": no_conflicts_enabled,
        "sync_gateway_version": sync_gateway_version,
        "target_admin_url": target_admin_url,
        "base_url": base_url,
        "enable_sample_bucket": enable_sample_bucket,
        "create_db_per_test": create_db_per_test,
        "source_db": source_db,
        "cbl_db": cbl_db,
        "base_url": base_url,
        "sg_config": sg_config
    }

    if enable_sample_bucket:
        log_info("Stopping replication")
        repl_obj.stop(repl)

    if create_db_per_suite:
        # Delete CBL database
        log_info("Deleting the database {} at the suite teardown".format(create_db_per_suite))
        db.deleteDB(source_db)

    # Flush all the memory contents on the server app
    utils_obj = Utils(base_url)
    utils_obj.flushMemory()


@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    base_url = params_from_base_suite_setup["base_url"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    xattrs_enabled = params_from_base_suite_setup["xattrs_enabled"]
    liteserv_host = params_from_base_suite_setup["liteserv_host"]
    liteserv_port = params_from_base_suite_setup["liteserv_port"]
    create_db_per_test = params_from_base_suite_setup["create_db_per_test"]
    no_conflicts_enabled = params_from_base_suite_setup["no_conflicts_enabled"]
    target_admin_url = params_from_base_suite_setup["target_admin_url"]
    source_db = params_from_base_suite_setup["source_db"]
    cbl_db = params_from_base_suite_setup["cbl_db"]
    test_name = request.node.name
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    mode = params_from_base_suite_setup["mode"]
    target_url = params_from_base_suite_setup["target_url"]
    base_url = params_from_base_suite_setup["base_url"]
    sg_ip = params_from_base_suite_setup["sg_ip"]
    sg_db = params_from_base_suite_setup["sg_db"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    target_admin_url = params_from_base_suite_setup["target_admin_url"]
    sg_config = params_from_base_suite_setup["sg_config"]

    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config=cluster_config)
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]

    log_info("Running test '{}'".format(test_name))
    log_info("cluster_config: {}".format(cluster_config))
    log_info("cluster_topology: {}".format(cluster_topology))
    log_info("mode: {}".format(mode))
    log_info("xattrs_enabled: {}".format(xattrs_enabled))

    cbl_db = create_db_per_test
    if create_db_per_test:
        # Create CBL database
        db = Database(base_url)

        log_info("Creating a Database {} at test setup".format(cbl_db))
        source_db = db.create(cbl_db)
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
        "target_url": target_url,
        "target_admin_url": target_admin_url,
        "sg_ip": sg_ip,
        "sg_db": sg_db,
        "no_conflicts_enabled": no_conflicts_enabled,
        "sync_gateway_version": sync_gateway_version,
        "source_db": source_db,
        "cbl_db": cbl_db,
        "base_url": base_url,
        "sg_config": sg_config
    }

    if create_db_per_test:
        # Delete CBL database
        log_info("Deleting the database {} at test teardown".format(create_db_per_test))
        db.deleteDB(source_db)


@pytest.fixture(scope="class")
def class_init(request, params_from_base_suite_setup):
    base_url = params_from_base_suite_setup["base_url"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]

    db_obj = Database(base_url)
    doc_obj = Document(base_url)
    dict_obj = Dictionary(base_url)
    datatype = DataTypeInitiator(base_url)
    repl_obj = Replicator(base_url)
    # repl_config_obj = ReplicatorConfiguration(base_url)
    base_auth_obj = BasicAuthenticator(base_url)
    session_auth_obj = SessionAuthenticator(base_url)
    sg_client = MobileRestClient()
    db = db_obj.create("cbl-init-db")

    request.cls.db_obj = db_obj
    request.cls.doc_obj = doc_obj
    request.cls.dict_obj = dict_obj
    request.cls.datatype = datatype
    request.cls.repl_obj = repl_obj
    # request.cls.repl_config_obj = repl_config_obj
    request.cls.base_auth_obj = base_auth_obj
    request.cls.session_auth_obj = session_auth_obj
    request.cls.sg_client = sg_client
    request.cls.db_obj = db_obj
    request.cls.db = db
    request.cls.liteserv_platform = liteserv_platform

    yield
    db_obj.deleteDB(db)
