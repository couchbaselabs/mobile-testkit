import pytest
import os
import datetime

from libraries.provision.clean_cluster import clean_cluster
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.constants import RESULTS_DIR
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.LiteServ import LiteServ
from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import SyncGateway
from keywords.Logging import Logging


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/listener/shared/client_2sgs/ directory
@pytest.fixture(scope="module")
def setup_client_2sgs_suite(request):

    """Suite setup fixture for client sync_gateway tests"""

    log_info("Setting up client sync_gateway suite ...")

    liteserv_platform = request.config.getoption("--liteserv-platform")
    liteserv_version = request.config.getoption("--liteserv-version")
    liteserv_storage_engine = request.config.getoption("--liteserv-storage-engine")

    sync_gateway_version = request.config.getoption("--sync-gateway-version")

    ls = LiteServ()

    log_info("Downloading LiteServ One ...")

    # Download LiteServ One
    ls.download_liteserv(
        platform=liteserv_platform,
        version=liteserv_version,
        storage_engine=liteserv_storage_engine
    )

    ls_cluster_target = None
    if liteserv_platform == "net-win":
        ls_cluster_target = "resources/cluster_configs/windows"

    # Install LiteServ
    ls.install_liteserv(
        platform=liteserv_platform,
        version=liteserv_version,
        storage_engine=liteserv_storage_engine,
        cluster_config=ls_cluster_target
    )

    cluster_helper = ClusterKeywords()
    cluster_helper.set_cluster_config("2sgs")
    cluster_config = os.environ["CLUSTER_CONFIG"]

    clean_cluster(cluster_config=cluster_config)

    log_info("Installing sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.install_sync_gateway(
        cluster_config=cluster_config,
        sync_gateway_version=sync_gateway_version,
        sync_gateway_config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS)
    )

    # Wait at the yeild until tests referencing this suite setup have run,
    # Then execute the teardown
    yield

    log_info("Tearing down suite ...")
    cluster_helper.unset_cluster_config()


# Passed to each testcase, run for each test_* method in client_sg folder
@pytest.fixture(scope="function")
def setup_client_2sgs_test(request):

    """Test setup fixture for client sync_gateway tests"""

    log_info("Setting up client sync_gateway test ...")

    liteserv_platform = request.config.getoption("--liteserv-platform")
    liteserv_version = request.config.getoption("--liteserv-version")
    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")
    liteserv_storage_engine = request.config.getoption("--liteserv-storage-engine")

    ls = LiteServ()
    client = MobileRestClient()

    test_name = request.node.name

    # Verify LiteServ is not running
    ls.verify_liteserv_not_running(host=liteserv_host, port=liteserv_port)

    ls_cluster_target = None
    if liteserv_platform == "net-win":
        ls_cluster_target = "resources/cluster_configs/windows"

    print("Starting LiteServ ...")

    if liteserv_platform != "net-win":
        # logging is file
        ls_logging = open("{}/logs/{}-ls1-{}-{}.txt".format(RESULTS_DIR, datetime.datetime.now(), liteserv_platform, test_name), "w")
    else:
        # logging is name
        ls_logging = "{}/logs/{}-ls1-{}-{}.txt".format(RESULTS_DIR, datetime.datetime.now(), liteserv_platform, test_name)

    ls_url, ls_handle = ls.start_liteserv(
        platform=liteserv_platform,
        version=liteserv_version,
        host=liteserv_host,
        port=liteserv_port,
        storage_engine=liteserv_storage_engine,
        logfile=ls_logging,
        cluster_config=ls_cluster_target
    )

    cluster_helper = ClusterKeywords()
    sg_helper = SyncGateway()

    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])

    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_one_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_two_url = cluster_hosts["sync_gateways"][1]["public"]
    sg_two_admin_url = cluster_hosts["sync_gateways"][1]["admin"]

    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_two_url)

    # Yield values to test case via fixture argument
    yield {
        "cluster_config": os.environ["CLUSTER_CONFIG"],
        "ls_url": ls_url,
        "sg_one_url": sg_one_url,
        "sg_one_admin_url": sg_one_admin_url,
        "sg_two_url": sg_two_url,
        "sg_two_admin_url": sg_two_admin_url
    }

    log_info("Tearing down test")

    # Teardown test
    client.delete_databases(ls_url)
    ls.shutdown_liteserv(host=liteserv_host,
                         platform=liteserv_platform,
                         version=liteserv_version,
                         storage_engine=liteserv_storage_engine,
                         process_handle=ls_handle,
                         logfile=ls_logging,
                         cluster_config=ls_cluster_target)

    # Verify LiteServ is killed
    ls.verify_liteserv_not_running(host=liteserv_host, port=liteserv_port)

    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_two_url)

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=os.environ["CLUSTER_CONFIG"], test_name=test_name)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.usefixtures("setup_client_2sgs_suite")
def test_listener_two_sync_gateways(setup_client_2sgs_test):
    """
    Port of https://github.com/couchbaselabs/sync-gateway-tests/blob/master/tests/cbl-replication-mismatch-2-gateways.js
    Scenario:
      1. Start 2 sync_gateways
      2. Create sg_db_one db on sync_gateway one
      3. Create sg_db_two db on sync_gateway two
      4. Create ls_db_one and ls_db_two on Liteserv
      5. Setup continuous push / pull replication from ls_db_one <-> sg_db_one
      6. Setup continuous push / pull replication from ls_db_two <-> sg_db_two
      7. Setup continuous push / pull replication from sg_db_one <-> ls_db_two
      8. Setup continuous push / pull replication from sg_db_two <-> ls_db_one
      9. Add num_docs / 2 to each liteserv database
      10. Verify each database has num_docs docs
      11. Verify all_docs in all dbs
      12. Verify changes feed for sg_db_one and sg_db_two
      13. Verify chnages feed for ls_db_one and ls_db_two
    """

    num_docs = 500

    ls_url = setup_client_2sgs_test["ls_url"]
    cluster_config = setup_client_2sgs_test["cluster_config"]
    sg_one_admin_url = setup_client_2sgs_test["sg_one_admin_url"]
    sg_two_admin_url = setup_client_2sgs_test["sg_two_admin_url"]

    sg_util = SyncGateway()
    sg_util.start_sync_gateway(cluster_config=cluster_config, url=sg_one_admin_url, config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS))
    sg_util.start_sync_gateway(cluster_config=cluster_config, url=sg_two_admin_url, config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS))

    ls_db_one = "ls_db1"
    ls_db_two = "ls_db2"
    sg_db_one = "sg_db1"
    sg_db_two = "sg_db2"

    log_info("ls_url: {}".format(ls_url))
    log_info("sg_one_admin_url: {}".format(sg_one_admin_url))
    log_info("sg_two_admin_url: {}".format(sg_two_admin_url))
    log_info("num_docs: {}".format(num_docs))
    log_info("Running 'test_listener_two_sync_gateways' ...")

    client = MobileRestClient()

    # Create dbs on sync_gateway
    client.create_database(sg_one_admin_url, sg_db_one, "walrus:")
    client.create_database(sg_two_admin_url, sg_db_two, "walrus:")

    # Create dbs on LiteServ
    client.create_database(ls_url, ls_db_one)
    client.create_database(ls_url, ls_db_two)

    # Start continuous push pull replication ls_db_one <-> sg_db_one
    client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_one,
        to_url=sg_one_admin_url, to_db=sg_db_one
    )
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_one_admin_url, from_db=sg_db_one,
        to_db=ls_db_one
    )

    # Start continuous push pull replication ls_db_two <-> sg_db_two
    client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_two,
        to_url=sg_two_admin_url, to_db=sg_db_two
    )
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_two_admin_url, from_db=sg_db_two,
        to_db=ls_db_two
    )

    # Start continuous push pull replication sg_db_one <-> ls_db_two
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_one_admin_url, from_db=sg_db_one,
        to_db=ls_db_two
    )
    client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_two,
        to_url=sg_one_admin_url, to_db=sg_db_one
    )

    # Start continuous push pull replication sg_db_two <-> ls_db_one
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_two_admin_url, from_db=sg_db_two,
        to_db=ls_db_one
    )
    client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_one,
        to_url=sg_two_admin_url, to_db=sg_db_two
    )

    ls_db_one_docs, errors = client.add_docs(url=ls_url, db=ls_db_one, number=num_docs / 2, id_prefix="ls_db_one_doc")
    assert len(ls_db_one_docs) == num_docs / 2
    assert len(errors) == 0

    ls_db_two_docs, errors = client.add_docs(url=ls_url, db=ls_db_two, number=num_docs / 2, id_prefix="ls_db_two_doc")
    assert len(ls_db_two_docs) == num_docs / 2
    assert len(errors) == 0

    all_docs = client.merge(ls_db_one_docs, ls_db_two_docs)
    assert len(all_docs) == 500

    # Verify docs replicate to each db
    client.verify_docs_present(url=ls_url, db=ls_db_one, expected_docs=all_docs)
    client.verify_docs_present(url=ls_url, db=ls_db_two, expected_docs=all_docs)
    client.verify_docs_present(url=sg_one_admin_url, db=sg_db_one, expected_docs=all_docs)
    client.verify_docs_present(url=sg_two_admin_url, db=sg_db_two, expected_docs=all_docs)

    # Verify changes feeds for each db
    client.verify_docs_in_changes(url=ls_url, db=ls_db_one, expected_docs=all_docs)
    client.verify_docs_in_changes(url=ls_url, db=ls_db_two, expected_docs=all_docs)
    client.verify_docs_in_changes(url=sg_one_admin_url, db=sg_db_one, expected_docs=all_docs)
    client.verify_docs_in_changes(url=sg_two_admin_url, db=sg_db_two, expected_docs=all_docs)
