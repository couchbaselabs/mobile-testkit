import pytest
import datetime

from keywords.utils import log_info

from keywords.constants import RESULTS_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient


# This will get called once before the first test and waits at the yeild
# until the last test in this file is executed. It will continue excecution
# from the yeild until the end of the method after the last test
@pytest.fixture(scope="module")
def setup_p2p_suite(request):

    """Suite setup fixture for p2p client tests"""

    log_info("Setting up P2P suite ...")

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

    liteserv_one = LiteServFactory.create(platform=liteserv_one_platform,
                                          version_build=liteserv_one_version,
                                          host=liteserv_one_host,
                                          port=liteserv_one_port,
                                          storage_engine=liteserv_one_storage_engine)

    liteserv_two = LiteServFactory.create(platform=liteserv_two_platform,
                                          version_build=liteserv_two_version,
                                          host=liteserv_two_host,
                                          port=liteserv_two_port,
                                          storage_engine=liteserv_two_storage_engine)

    liteserv_one.download()
    liteserv_one.install()

    liteserv_two.download()
    liteserv_two.install()

    yield {"liteserv_one": liteserv_one, "liteserv_two": liteserv_two}

    log_info("Tearing down suite ...")

    liteserv_one.remove()

    liteserv_two.remove()


# Runs as a setup to each test_* function in the file. It will yeild the
# dictionary to the test and execute everything after the yield once the
# test has completed
@pytest.fixture(scope="function")
def setup_p2p_test(request, setup_p2p_suite):

    """Test setup fixture for p2p client tests"""

    log_info("Setting up P2P test ...")

    liteserv_one = setup_p2p_suite["liteserv_one"]
    liteserv_two = setup_p2p_suite["liteserv_two"]

    test_name = request.node.name

    print("Starting LiteServ One ...")
    ls_logging_one = "{}/logs/{}-ls1-{}-{}.txt".format(RESULTS_DIR, type(liteserv_one).__name__, test_name, datetime.datetime.now())
    ls_url_one = liteserv_one.start(ls_logging_one)

    print("Starting LiteServ Two ...")
    ls_logging_two = "{}/logs/{}-ls2-{}-{}.txt".format(RESULTS_DIR, type(liteserv_two).__name__, test_name, datetime.datetime.now())
    ls_url_two = liteserv_two.start(ls_logging_two)

    # Yield values to test case via fixture argument
    yield {"ls_url_one": ls_url_one, "ls_url_two": ls_url_two}

    log_info("Tearing down test")

    # Teardown test
    client = MobileRestClient()
    client.delete_databases(ls_url_one)
    client.delete_databases(ls_url_two)

    liteserv_one.stop()
    liteserv_two.stop()


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.p2p
@pytest.mark.changes
def test_peer_2_peer_sanity(setup_p2p_test):
    """
    1. Sanity P2P Scenario
    2. Launch LiteServ 1 and LiteServ 2
    3. Create a database on each LiteServ
    4. Start continuous push pull replication from each db to the other
    5. Add docs to each db
    6. Verify the docs show up at each db
    7. Verify the docs show up in the database's changes feed.
    """

    ls_url_one = setup_p2p_test["ls_url_one"]
    ls_url_two = setup_p2p_test["ls_url_two"]

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
    assert len(ls_db1_docs) == num_docs_per_db

    ls_db2_docs = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2")
    assert len(ls_db2_docs) == num_docs_per_db

    all_docs = client.merge(ls_db1_docs, ls_db2_docs)
    assert len(all_docs) == 2000

    client.verify_docs_present(url=ls_url_one, db=ls_db1, expected_docs=all_docs)
    client.verify_docs_present(url=ls_url_two, db=ls_db2, expected_docs=all_docs)

    client.verify_docs_in_changes(url=ls_url_one, db=ls_db1, expected_docs=all_docs)
    client.verify_docs_in_changes(url=ls_url_two, db=ls_db2, expected_docs=all_docs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.p2p
@pytest.mark.changes
@pytest.mark.parametrize("num_docs_per_db, seeded_db", [
    (5000, False), (10000, True),
])
def test_peer_2_peer_sanity_pull(setup_p2p_test, num_docs_per_db, seeded_db):
    """
    1. Create ls_db1 database on LiteServ One
    2. Create ls_db2 database on LiteServ Two
    3. Create continuous pull replication LiteServ 1 ls_db1 <- LiteServ 2 ls_db2
    4. Add 5000 docs to LiteServ 2 ls_db2
    5. Verify all docs replicate to LiteServ 1 ls_db1
    6. Verify all docs show up in changes for LiteServ 1 ls_db1
    """

    ls_url_one = setup_p2p_test["ls_url_one"]
    ls_url_two = setup_p2p_test["ls_url_two"]

    log_info("ls_url_one: {}".format(ls_url_one))
    log_info("ls_url_two: {}".format(ls_url_two))

    client = MobileRestClient()

    log_info("Creating databases")
    ls_db1 = client.create_database(url=ls_url_one, name="ls_db1")
    ls_db2 = client.create_database(url=ls_url_two, name="ls_db2")

    if seeded_db:
        ls_db2_docs_seed = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2_seed")
        assert len(ls_db2_docs_seed) == num_docs_per_db

    # Setup continuous pull replication from LiteServ 2 ls_db2 to LiteServ 1 ls_db1
    pull_repl = client.start_replication(
        url=ls_url_one,
        continuous=True,
        from_url=ls_url_two, from_db=ls_db2,
        to_db=ls_db1
    )

    client.wait_for_replication_status_idle(url=ls_url_one, replication_id=pull_repl)

    ls_db2_docs = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2")
    assert len(ls_db2_docs) == num_docs_per_db

    total_ls_db2_docs = ls_db2_docs
    if seeded_db:
        total_ls_db2_docs += ls_db2_docs_seed

    client.verify_docs_present(url=ls_url_one, db=ls_db1, expected_docs=total_ls_db2_docs)
    client.verify_docs_in_changes(url=ls_url_one, db=ls_db1, expected_docs=total_ls_db2_docs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.p2p
@pytest.mark.changes
@pytest.mark.parametrize("num_docs_per_db, seeded_db", [
    (5000, False), (10000, True),
])
def test_peer_2_peer_sanity_push(setup_p2p_test, num_docs_per_db, seeded_db):
    """
    1. Create ls_db1 database on LiteServ One
    2. Create ls_db2 database on LiteServ Two
    3. Create continuous push replication LiteServ 1 ls_db1 -> LiteServ 2 ls_db2
    4. Add 5000 docs to LiteServ 1 ls_db1
    5. Verify all docs replicate to LiteServ 2 ls_db2
    6. Verify all docs show up in changes for LiteServ 2 ls_db2
    """

    ls_url_one = setup_p2p_test["ls_url_one"]
    ls_url_two = setup_p2p_test["ls_url_two"]

    log_info("ls_url_one: {}".format(ls_url_one))
    log_info("ls_url_two: {}".format(ls_url_two))

    client = MobileRestClient()

    log_info("Creating databases")
    ls_db1 = client.create_database(url=ls_url_one, name="ls_db1")
    ls_db2 = client.create_database(url=ls_url_two, name="ls_db2")

    if seeded_db:
        ls_db1_docs_seed = client.add_docs(url=ls_url_one, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1_seed")
        assert len(ls_db1_docs_seed) == num_docs_per_db

    # Setup continuous push replication from LiteServ 1 ls_db1 to LiteServ 2 ls_db2
    push_repl = client.start_replication(
        url=ls_url_one,
        continuous=True,
        from_db=ls_db1,
        to_url=ls_url_two, to_db=ls_db2,
    )

    client.wait_for_replication_status_idle(url=ls_url_one, replication_id=push_repl)

    ls_db1_docs = client.add_docs(url=ls_url_one, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1")
    assert len(ls_db1_docs) == num_docs_per_db

    total_ls_db1_docs = ls_db1_docs
    if seeded_db:
        total_ls_db1_docs += ls_db1_docs_seed

    client.verify_docs_present(url=ls_url_two, db=ls_db2, expected_docs=total_ls_db1_docs)
    client.verify_docs_in_changes(url=ls_url_two, db=ls_db2, expected_docs=total_ls_db1_docs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.p2p
@pytest.mark.changes
@pytest.mark.parametrize("num_docs_per_db, seeded_db", [
    (5000, False), (10000, True),
])
def test_peer_2_peer_sanity_push_pull(setup_p2p_test, num_docs_per_db, seeded_db):
    """
    1. Create ls_db1 database on LiteServ One
    2. Create ls_db2 database on LiteServ Two
    3. Create continuous push replication LiteServ 1 ls_db1 -> LiteServ 2 ls_db2
    4. Add 5000 docs to LiteServ 1 ls_db1
    5. Verify all docs replicate to LiteServ 2 ls_db2
    6. Verify all docs show up in changes for LiteServ 2 ls_db2
    """

    ls_url_one = setup_p2p_test["ls_url_one"]
    ls_url_two = setup_p2p_test["ls_url_two"]

    log_info("ls_url_one: {}".format(ls_url_one))
    log_info("ls_url_two: {}".format(ls_url_two))

    client = MobileRestClient()

    log_info("Creating databases")
    ls_db1 = client.create_database(url=ls_url_one, name="ls_db1")
    ls_db2 = client.create_database(url=ls_url_two, name="ls_db2")

    if seeded_db:
        ls_db1_docs_seed = client.add_docs(url=ls_url_one, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1_seed")
        assert len(ls_db1_docs_seed) == num_docs_per_db
        ls_db2_docs_seed = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2_seed")
        assert len(ls_db2_docs_seed) == num_docs_per_db

    # Setup continuous push replication from LiteServ 1 ls_db1 to LiteServ 2 ls_db2
    push_repl = client.start_replication(
        url=ls_url_one,
        continuous=True,
        from_db=ls_db1,
        to_url=ls_url_two, to_db=ls_db2,
    )

    # Setup continuous pull replication from LiteServ 2 ls_db2 to LiteServ 1 ls_db1
    pull_repl = client.start_replication(
        url=ls_url_one,
        continuous=True,
        from_url=ls_url_two, from_db=ls_db2,
        to_db=ls_db1
    )

    client.wait_for_replication_status_idle(url=ls_url_one, replication_id=push_repl)
    client.wait_for_replication_status_idle(url=ls_url_one, replication_id=pull_repl)

    ls_db1_docs = client.add_docs(url=ls_url_one, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1")
    assert len(ls_db1_docs) == num_docs_per_db
    ls_db2_docs = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2")
    assert len(ls_db2_docs) == num_docs_per_db

    total_docs = ls_db1_docs + ls_db2_docs
    if seeded_db:
        total_docs += ls_db1_docs_seed
        total_docs += ls_db2_docs_seed

    client.verify_docs_present(url=ls_url_two, db=ls_db2, expected_docs=total_docs)
    client.verify_docs_in_changes(url=ls_url_two, db=ls_db2, expected_docs=total_docs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.p2p
@pytest.mark.changes
def test_peer_2_peer_sanity_pull_one_shot(setup_p2p_test):
    """
    1. Create ls_db1 database on LiteServ One
    2. Create ls_db2 database on LiteServ Two
    3. Add 10000 docs to LiteServ 2 ls_db2
    4. Create one shot pull replication LiteServ 1 ls_db1 <- LiteServ 2 ls_db2
    5. Verify all docs replicate to LiteServ 1 ls_db1
    6. Verify all docs show up in changes for LiteServ 1 ls_db1
    """

    ls_url_one = setup_p2p_test["ls_url_one"]
    ls_url_two = setup_p2p_test["ls_url_two"]

    num_docs_per_db = 10000

    log_info("ls_url_one: {}".format(ls_url_one))
    log_info("ls_url_two: {}".format(ls_url_two))

    client = MobileRestClient()

    log_info("Creating databases")
    ls_db1 = client.create_database(url=ls_url_one, name="ls_db1")
    ls_db2 = client.create_database(url=ls_url_two, name="ls_db2")

    ls_db2_docs = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2")

    # Setup one shot pull replication from LiteServ 2 ls_db2 to LiteServ 1 ls_db1
    pull_repl = client.start_replication(
        url=ls_url_one,
        continuous=False,
        from_url=ls_url_two, from_db=ls_db2,
        to_db=ls_db1
    )
    log_info("Replication ID: {}".format(pull_repl))

    assert len(ls_db2_docs) == num_docs_per_db

    client.verify_docs_present(url=ls_url_one, db=ls_db1, expected_docs=ls_db2_docs)
    client.verify_docs_in_changes(url=ls_url_one, db=ls_db1, expected_docs=ls_db2_docs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.p2p
@pytest.mark.changes
def test_peer_2_peer_sanity_push_one_shot(setup_p2p_test):
    """
    1. Create ls_db1 database on LiteServ One
    2. Create ls_db2 database on LiteServ Two
    3. Add 10000 docs to LiteServ 1 ls_db1
    4. Create continuous push replication LiteServ 1 ls_db1 -> LiteServ 2 ls_db2
    5. Verify all docs replicate to LiteServ 2 ls_db2
    6. Verify all docs show up in changes for LiteServ 2 ls_db2
    """

    ls_url_one = setup_p2p_test["ls_url_one"]
    ls_url_two = setup_p2p_test["ls_url_two"]

    num_docs_per_db = 10000

    log_info("ls_url_one: {}".format(ls_url_one))
    log_info("ls_url_two: {}".format(ls_url_two))

    client = MobileRestClient()

    log_info("Creating databases")
    ls_db1 = client.create_database(url=ls_url_one, name="ls_db1")
    ls_db2 = client.create_database(url=ls_url_two, name="ls_db2")

    ls_db1_docs = client.add_docs(url=ls_url_one, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1")

    # Setup one shot push replication from LiteServ 1 ls_db1 to LiteServ 2 ls_db2
    push_repl = client.start_replication(
        url=ls_url_one,
        continuous=False,
        from_db=ls_db1,
        to_url=ls_url_two, to_db=ls_db2,
    )
    log_info("Replication ID: {}".format(push_repl))

    assert len(ls_db1_docs) == num_docs_per_db

    client.verify_docs_present(url=ls_url_two, db=ls_db2, expected_docs=ls_db1_docs)
    client.verify_docs_in_changes(url=ls_url_two, db=ls_db2, expected_docs=ls_db1_docs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.p2p
@pytest.mark.changes
def test_peer_2_peer_sanity_push_pull_one_shot(setup_p2p_test):
    """
    1. Create ls_db1 database on LiteServ One
    2. Create ls_db2 database on LiteServ Two
    3. Add 5000 docs to LiteServ 1 ls_db1
    4. Add 5000 docs to LiteServ 2 ls_db2
    5. Create continuous push replication LiteServ 1 ls_db1 -> LiteServ 2 ls_db2
    6. Create continuous pull replication LiteServ 1 ls_db1 <- LiteServ 2 ls_db2
    7. Verify all docs replicate to LiteServ 2 ls_db2
    8. Verify all docs show up in changes for LiteServ 2 ls_db2
    9. Verify all docs replicate to LiteServ 1 ls_db1
    10. Verify all docs show up in changes for LiteServ 1 ls_db1
    """

    ls_url_one = setup_p2p_test["ls_url_one"]
    ls_url_two = setup_p2p_test["ls_url_two"]

    num_docs_per_db = 5000

    log_info("ls_url_one: {}".format(ls_url_one))
    log_info("ls_url_two: {}".format(ls_url_two))

    client = MobileRestClient()

    log_info("Creating databases")
    ls_db1 = client.create_database(url=ls_url_one, name="ls_db1")
    ls_db2 = client.create_database(url=ls_url_two, name="ls_db2")

    ls_db1_docs = client.add_docs(url=ls_url_one, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1")
    ls_db2_docs = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2")

    # Setup one shot push replication from LiteServ 1 ls_db1 to LiteServ 2 ls_db2
    push_repl = client.start_replication(
        url=ls_url_one,
        continuous=False,
        from_db=ls_db1,
        to_url=ls_url_two, to_db=ls_db2,
    )
    log_info("Replication ID: {}".format(push_repl))

    # Setup one shot pull replication from LiteServ 2 ls_db2 to LiteServ 1 ls_db1
    pull_repl = client.start_replication(
        url=ls_url_one,
        continuous=False,
        from_url=ls_url_two, from_db=ls_db2,
        to_db=ls_db1
    )
    log_info("Replication ID: {}".format(pull_repl))

    assert len(ls_db1_docs) == num_docs_per_db
    assert len(ls_db2_docs) == num_docs_per_db

    client.verify_docs_present(url=ls_url_one, db=ls_db1, expected_docs=2 * ls_db2_docs)
    client.verify_docs_in_changes(url=ls_url_one, db=ls_db1, expected_docs=2 * ls_db2_docs)

    client.verify_docs_present(url=ls_url_two, db=ls_db2, expected_docs=2 * ls_db1_docs)
    client.verify_docs_in_changes(url=ls_url_two, db=ls_db2, expected_docs=2 * ls_db1_docs)
