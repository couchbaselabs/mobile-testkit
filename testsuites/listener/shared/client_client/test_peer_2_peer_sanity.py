import pytest
import logging
import datetime

from keywords.utils import log_info

from keywords.constants import RESULTS_DIR
from keywords.LiteServ import LiteServ
from keywords.MobileRestClient import MobileRestClient


@pytest.fixture(scope="module")
def suite_setup(request):

    """Suite setup fixture for p2p client tests"""

    logging.info("Setting up P2P suite ...")

    liteserv_one_platform = request.config.getoption("--liteserv-one-platform")
    liteserv_one_version = request.config.getoption("--liteserv-one-version")
    liteserv_one_storage_engine = request.config.getoption("--liteserv-one-storage-engine")

    liteserv_two_platform = request.config.getoption("--liteserv-two-platform")
    liteserv_two_version = request.config.getoption("--liteserv-two-version")
    liteserv_two_storage_engine = request.config.getoption("--liteserv-two-storage-engine")

    ls = LiteServ()

    print("Downloading LiteServ One ...")

    # Download LiteServ One
    ls.download_liteserv(
        platform=liteserv_one_platform,
        version=liteserv_one_version,
        storage_engine=liteserv_one_storage_engine
    )

    print("Downloading LiteServ Two ...")

    # Download LiteServ Two
    ls.download_liteserv(
        platform=liteserv_two_platform,
        version=liteserv_two_version,
        storage_engine=liteserv_two_storage_engine
    )

    yield

    print("Tearing down suite ...")


@pytest.fixture(scope="function")
def test_setup(request):

    """Test setup fixture for p2p client tests"""

    logging.info("Setting up P2P test ...")

    liteserv_one_platform = request.config.getoption("--liteserv-one-platform")
    liteserv_one_version = request.config.getoption("--liteserv-one-version")
    liteserv_one_host = request.config.getoption("--liteserv-one-host")
    liteserv_one_port = request.config.getoption("--liteserv-one-port")
    liteserv_one_storage_engine = request.config.getoption("--liteserv-one-storage-engine")

    liteserv_two_platform = request.config.getoption("--liteserv-two-platform")
    liteserv_two_version = request.config.getoption("--liteserv-two-version")
    liteserv_two_host = request.config.getoption("--liteserv-two-host")
    liteserv_two_port = request.config.getoption("--liteserv-two-port")
    liteserv_two_storage_engine = request.config.getoption("--liteserv-two-storage-engine")

    ls = LiteServ()
    client = MobileRestClient()

    test_name = request.node.name

    # Verify LiteServ is not running
    ls.verify_liteserv_not_running(host=liteserv_one_host, port=liteserv_one_port)
    ls.verify_liteserv_not_running(host=liteserv_two_host, port=liteserv_two_port)

    print("Starting LiteServ One ...")
    ls_one_logging = open("{}/logs/{}-ls1-{}-{}.txt".format(RESULTS_DIR, datetime.datetime.now(), liteserv_one_platform, test_name), "w")
    ls_one_url, ls_one_handle = ls.start_liteserv(
        platform=liteserv_one_platform,
        version=liteserv_one_version,
        host=liteserv_one_host,
        port=liteserv_one_port,
        storage_engine=liteserv_one_storage_engine,
        logfile=ls_one_logging
    )

    print("Starting LiteServ Two ...")
    ls_two_logging = open("{}/logs/{}-ls1-{}-{}.txt".format(RESULTS_DIR, datetime.datetime.now(), liteserv_two_platform, test_name), "w")
    ls_two_url, ls_two_handle = ls.start_liteserv(
        platform=liteserv_two_platform,
        version=liteserv_two_version,
        host=liteserv_two_host,
        port=liteserv_two_port,
        storage_engine=liteserv_two_storage_engine,
        logfile=ls_two_logging
    )

    ls.verify_liteserv_launched(platform=liteserv_one_platform, host=liteserv_one_host, port=liteserv_one_port, version_build=liteserv_one_version)
    ls.verify_liteserv_launched(platform=liteserv_two_platform, host=liteserv_two_host, port=liteserv_two_port, version_build=liteserv_two_version)

    # Return values to the test case via setup tuple
    yield (ls_one_url, ls_two_url)

    print("Tearing down test")

    # Teardown test
    client.delete_databases(ls_one_url)
    client.delete_databases(ls_two_url)

    ls.shutdown_liteserv(process_handle=ls_one_handle, logfile=ls_one_logging)
    ls.shutdown_liteserv(process_handle=ls_two_handle, logfile=ls_two_logging)

    # Verify LiteServ is killed
    ls.verify_liteserv_not_running(host=liteserv_one_host, port=liteserv_one_port)
    ls.verify_liteserv_not_running(host=liteserv_two_host, port=liteserv_two_port)


@pytest.mark.usefixtures("suite_setup")
class TestPeerToPeer:

    @pytest.mark.sanity
    @pytest.mark.listener
    @pytest.mark.replication
    @pytest.mark.p2p
    @pytest.mark.changes
    def test_peer_2_peer_sanity(self, test_setup):
        """
        1. Sanity P2P Scenario
        2. Launch LiteServ 1 and LiteServ 2
        3. Create a database on each LiteServ
        4. Start continuous push pull replication from each db to the other
        5. Add docs to each db
        6. Verify the docs show up at each db
        7. Verify the docs show up in the database's changes feed.
        """

        ls_url_one = test_setup[0]
        ls_url_two = test_setup[1]

        num_docs_per_db = 1000

        log_info("ls_url_one: {}".format(ls_url_one))
        log_info("ls_url_two: {}".format(ls_url_two))

        client = MobileRestClient()

        log_info("Creating databases")
        ls_db1 = client.create_database(url=ls_url_one, name="ls_db1")
        ls_db2 = client.create_database(url=ls_url_two, name="ls_db2")

        # Setup continuous push / pull replication from LiteServ 1 ls_db1 to LiteServ 2 ls_db2
        repl_one = client.start_replication(
            url=ls_url_one,
            continuous=True,
            from_db=ls_db1,
            to_url=ls_url_two, to_db=ls_db2
        )

        repl_two = client.start_replication(
            url=ls_url_one,
            continuous=True,
            from_url=ls_url_two, from_db=ls_db2,
            to_db=ls_db1
        )

        # Setup continuous push / pull replication from LiteServ 2 ls_db2 to LiteServ 1 ls_db1
        repl_three = client.start_replication(
            url=ls_url_two,
            continuous=True,
            from_db=ls_db2,
            to_url=ls_url_one, to_db=ls_db1
        )

        repl_four = client.start_replication(
            url=ls_url_two,
            continuous=True,
            from_url=ls_url_one, from_db=ls_db1,
            to_db=ls_db2
        )

        client.wait_for_replication_status_idle(url=ls_url_one, replication_id=repl_one)
        client.wait_for_replication_status_idle(url=ls_url_one, replication_id=repl_two)
        client.wait_for_replication_status_idle(url=ls_url_two, replication_id=repl_three)
        client.wait_for_replication_status_idle(url=ls_url_two, replication_id=repl_four)

        ls_url_one_replications = client.get_replications(ls_url_one)
        assert len(ls_url_one_replications) == 2

        ls_url_two_replications = client.get_replications(ls_url_two)
        assert len(ls_url_two_replications) == 2

        ls_db1_docs = client.add_docs(url=ls_url_one, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1")
        ls_db2_docs = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2")

        all_docs = client.merge(ls_db1_docs, ls_db2_docs)
        client.verify_docs_present(url=ls_url_one, db=ls_db1, expected_docs=all_docs)
        client.verify_docs_present(url=ls_url_two, db=ls_db2, expected_docs=all_docs)

        client.verify_docs_in_changes(url=ls_url_one, db=ls_db1, expected_docs=all_docs)
        client.verify_docs_in_changes(url=ls_url_two, db=ls_db2, expected_docs=all_docs)

