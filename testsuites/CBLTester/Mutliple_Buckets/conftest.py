import pytest

from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords.utils import log_info
from keywords.utils import host_for_url
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.exceptions import ProvisioningError
from keywords.tklogging import Logging
from CBLClient.Utils import Utils



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


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/CBLTester/CBL_Functional_tests/ directory
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
    device_enabled = request.config.getoption("--device")
    sg_ssl = request.config.getoption("--sg-ssl")
    # community_enabled = request.config.getoption("--community")

#     testserver = TestServerFactory.create(platform=liteserv_platform,
#                                           version_build=liteserv_version,
#                                           host=liteserv_host,
#                                           port=liteserv_port,
#                                           community_enabled=community_enabled)
#
#     log_info("Downloading TestServer ...")
#     # Download TestServer app
#     testserver.download()
#
#     # Install TestServer app
#     if device_enabled and liteserv_platform == "ios":
#         testserver.install_device()
#     else:
#         testserver.install()

    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, mode)
    sg_config = sync_gateway_config_path_for_mode("multiple_dbs_unique_data_unique_index", mode)
    no_conflicts_enabled = request.config.getoption("--no-conflicts")
    cluster_utils = ClusterKeywords()
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)

    sg_db = "db"
    cbl_db = None
    sg_url = cluster_topology["sync_gateways"][0]["public"]
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_url)

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
    cluster_utils.set_cluster_config(cluster_config.split("/")[-1])

    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)
    target_url = "ws://{}:4984/{}".format(sg_ip, sg_db)
    target_admin_url = "ws://{}:4985/{}".format(sg_ip, sg_db)

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

    yield {
        "sg_url": sg_url,
        "sg_admin_url": sg_admin_url,
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
        "cbl_db": cbl_db,
        "base_url": base_url,
        "sg_config": sg_config,
        "target_url": target_url,
        "target_admin_url": target_admin_url,
        # "testserver": testserver,
        "device_enabled": device_enabled
    }

#     if create_db_per_suite:
#         # Delete CBL database
#         log_info("Deleting the database {} at the suite teardown".format(create_db_per_suite))
#         time.sleep(2)
#         db.deleteDB(source_db)
#         time.sleep(1)

    # Flush all the memory contents on the server app
    log_info("Flushing server memory")
    utils_obj = Utils(base_url)
    utils_obj.flushMemory()
    log_info("Stopping the test server")
#     testserver.stop()