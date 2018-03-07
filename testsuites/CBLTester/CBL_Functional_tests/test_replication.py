import pytest
import time
import os
import random

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Document import Document
from CBLClient.Authenticator import Authenticator
from concurrent.futures import ThreadPoolExecutor

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords import document, attachment
from libraries.testkit import cluster


@pytest.fixture(scope="function")
def setup_teardown_test(params_from_base_test_setup):
    cbl_db_name = "cbl_db"
    base_url = params_from_base_test_setup["base_url"]
    db = Database(base_url)
    db_config = db.configure()
    log_info("Creating db")
    cbl_db = db.create(cbl_db_name, db_config)

    yield{
        "db": db,
        "cbl_db": cbl_db,
        "cbl_db_name": cbl_db_name
    }

    log_info("Deleting the db")
    # db.close(cbl_db)
    db.deleteDB(cbl_db)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs, continuous", [
    (10, True),
    (10, False),
    (100, True),
    (100, False),
    (1000, True),
    (1000, False)
])
def test_replication_configuration_valid_values(params_from_base_test_setup, num_of_docs, continuous):
    """
        @summary:
        1. Create CBL DB and create bulk doc in CBL
        2. Configure replication with valid values of valid cbl Db, valid target url
        3. Start replication with push and pull
        4. Verify replication is successful and verify docs exist
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')
    channels_sg = ["ABC"]
    username = "autotest"
    password = "password"
    number_of_updates = 2

    # Create CBL database
    sg_client = MobileRestClient()

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels_sg)

    # Configure replication with push_pull
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, channels_sg, sg_client, cbl_db, sg_blip_url, continuous=continuous)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs["rows"], number_updates=number_of_updates, auth=session)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"
    time.sleep(2)  # wait until re
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
    sg_docs = sg_docs["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    # Check that all docs of CBL got replicated to CBL
#     for doc in sg_docs["rows"]:
#         assert db.contains(cbl_db, str(doc["id"]))
    time.sleep(2)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for doc in cbl_doc_ids:
        if continuous:
            assert cbl_db_docs[doc]["updates"] == number_of_updates, "updates did not get updated"
        else:
            assert cbl_db_docs[doc]["updates"] == 0, "sync-gateway updates got pushed to CBL for one shot replication"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("authenticator_type", [
    ('session'),
    ('basic')
])
def test_replication_configuration_with_pull_replication(params_from_base_test_setup, authenticator_type):
    """
        @summary:
        1. Create CBL DB and create bulk doc in CBL
        2. Configure replication.
        3. Create docs in SG.
        4. pull docs to CBL.
        5. Verify all docs replicated and pulled to CBL.

    """
    sg_db = "db"

    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    channels = ["ABC"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    # Add 5 docs to CBL
    # Add 10 docs to SG
    # One shot replication
    sg_added_doc_ids, cbl_added_doc_ids, session = setup_sg_cbl_docs(params_from_base_test_setup, sg_db=sg_db, base_url=base_url, db=db,
                                                                     cbl_db=cbl_db, sg_url=sg_url, sg_admin_url=sg_admin_url, sg_blip_url=sg_blip_url,
                                                                     replication_type="pull", channels=channels, replicator_authenticator_type=authenticator_type)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)

    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)

    assert len(sg_docs["rows"]) == 10, "Number of sg docs is not equal to total number of cbl docs and sg docs"
    assert cbl_doc_count == 15, "Did not get expected number of cbl docs"

    # Check that CBL docs are not pushed to SG as it is just a pull
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc in cbl_added_doc_ids:
        assert doc not in sg_ids

    # Verify SG docs are pulled to CBL
    for id in sg_added_doc_ids:
        assert id in cbl_doc_ids


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("authenticator_type", [
    ('session'),
    ('basic')
])
def test_replication_configuration_with_push_replication(params_from_base_test_setup, authenticator_type):
    """
        @summary:
        1. Create docs in SG
        2. Create docs in CBL
        3. Do push replication with session authenticated user
        4. Verify CBL docs got replicated to SG
        5. Verify sg docs not replicated to CBL

    """
    sg_db = "db"

    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    channels = ["ABC"]

    sg_client = MobileRestClient()
    sg_added_doc_ids, cbl_added_doc_ids, session = setup_sg_cbl_docs(params_from_base_test_setup, sg_db=sg_db, base_url=base_url, db=db,
                                                                     cbl_db=cbl_db, sg_url=sg_url, sg_admin_url=sg_admin_url, sg_blip_url=sg_blip_url,
                                                                     replication_type="push", channels=channels, replicator_authenticator_type=authenticator_type)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)

    assert len(sg_docs["rows"]) == 15, "Number of sg docs is not equal to total number of cbl docs and sg docs"
    assert cbl_doc_count == 5, "Did not get expected number of cbl docs"

    # Check that all doc ids in SG are also present in CBL
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc in cbl_doc_ids:
        assert doc in sg_ids

    # Verify sg docs does not exist in CBL as it is just a push replication
    for doc_id in sg_added_doc_ids:
        assert doc_id not in cbl_doc_ids


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
def test_replication_push_replication_without_authentication(params_from_base_test_setup):
    """
        @summary:
        1. Create docs in CBL
        2. Create docs in SG
        3. Do push replication without authentication.
        4. Verify docs are not replicated without authentication

    """
    sg_db = "db"

    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    channels = ["ABC"]
    sg_client = MobileRestClient()

    db.create_bulk_docs(5, "cbl", db=cbl_db, channels=channels)
    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    session = sg_client.create_session(sg_admin_url, sg_db, "autotest")

    sg_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=10, id_prefix="sg_doc", channels=channels, auth=session)
    sg_ids = [row["id"] for row in sg_docs]

    replicator = Replication(base_url)
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True, replication_type="push", replicator_authenticator=None)

    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl, err_check=False)
    error = replicator.getError(repl)

    assert "401" in error, "expected error did not occurred"

    replicator.stop(repl)

    cbl_doc_ids = db.getDocIds(cbl_db)
    # Check that all doc ids in CBL are not replicated to SG
    for doc in cbl_doc_ids:
        assert doc not in sg_ids


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize(
    'replicator_authenticator, invalid_username, invalid_password, invalid_session, invalid_cookie',
    [
        ('basic', 'invalid_user', 'password', None, None),
        ('session', None, None, 'invalid_session', 'invalid_cookie'),
    ]
)
def test_replication_push_replication_invalid_authentication(params_from_base_test_setup, replicator_authenticator,
                                                             invalid_username, invalid_password, invalid_session, invalid_cookie):
    """
        @summary:
        1. Create docs in CBL
        2. Create docs in SG
        3. Do push replication with invalid authentication.
        4. Verify replication configuration fails.

    """
    sg_db = "db"

    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    channels = ["ABC"]
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)

    db.create_bulk_docs(5, "cbl", db=cbl_db, channels=channels)
    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session = sg_client.create_session(sg_admin_url, sg_db, "autotest")

    replicator = Replication(base_url)
    if replicator_authenticator == "session":
        replicator_authenticator = authenticator.authentication(invalid_session, invalid_cookie, authentication_type="session")
    elif replicator_authenticator == "basic":
        replicator_authenticator = authenticator.authentication(username=invalid_username, password=invalid_password, authentication_type="basic")
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True, replication_type="push", replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl, err_check=False)
    error = replicator.getError(repl)

    assert "401" in error, "expected error did not occurred"
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
def test_replication_configuration_with_filtered_doc_ids(params_from_base_test_setup):
    """
        @summary:
        1. Create docs in SG
        2. Create docs in CBL
        3. PushPull Replicate one shot from CBL -> SG with doc id filters set
        4. Verify SG only has the doc ids set in the replication from CBL
        5. Add new docs to SG
        6. PushPull Replicate one shot from SG -> CBL with doc id filters set
        7. Verify CBL only has the doc ids set in the replication from SG
        NOTE: Only works with one shot replication
    """
    sg_db = "db"

    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    channels = ["ABC"]
    sg_client = MobileRestClient()
    replicator = Replication(base_url)

    db.create_bulk_docs(number=10, id_prefix="cbl_filter", db=cbl_db, channels=channels)
    cbl_added_doc_ids = db.getDocIds(cbl_db)
    num_of_filtered_ids = 5
    list_of_filtered_ids = random.sample(cbl_added_doc_ids, num_of_filtered_ids)

    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_added_doc_ids, cbl_added_doc_ids, session = setup_sg_cbl_docs(params_from_base_test_setup, sg_db=sg_db, base_url=base_url, db=db,
                                                                     cbl_db=cbl_db, sg_url=sg_url, sg_admin_url=sg_admin_url, sg_blip_url=sg_blip_url, document_ids=list_of_filtered_ids,
                                                                     replicator_authenticator_type="basic", channels=channels)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    # Verify sg docs count
    sg_added_docs = len(sg_added_doc_ids)
    total_sg_docs = sg_added_docs + num_of_filtered_ids

    assert len(sg_docs["rows"]) == total_sg_docs, "Number of sg docs is not expected"

    list_of_non_filtered_ids = set(cbl_added_doc_ids) - set(list_of_filtered_ids)

    # Verify only filtered cbl doc ids are replicated to sg
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for sg_id in list_of_filtered_ids:
        assert sg_id in sg_ids

    # Verify non filtered docs ids are not replicated in sg
    for doc_id in list_of_non_filtered_ids:
        assert doc_id not in sg_ids

    cbl_doc_ids = db.getDocIds(cbl_db)

    # Now filter doc ids
    authenticator = Authenticator(base_url)
    cookie, session_id = session
    log_info("Authentication cookie: {}".format(cookie))
    log_info("Authentication session id: {}".format(session_id))
    replicator_authenticator = authenticator.authentication(session_id, cookie,
                                                            authentication_type="session")
    sg_new_added_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=10, id_prefix="sg_doc_filter",
                                           channels=channels, auth=session)
    sg_new_added_ids = [row["id"] for row in sg_new_added_docs]
    list_of_sg_filtered_ids = random.sample(sg_new_added_ids, num_of_filtered_ids)
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=False,
                                       documentIDs=list_of_sg_filtered_ids, channels=channels,
                                       replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    log_info("Starting replicator")
    replicator.start(repl)
    log_info("Waiting for replicator to go idle")
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # Verify only filtered sg ids are replicated to cbl
    cbl_doc_ids = db.getDocIds(cbl_db)
    list_of_non_sg_filtered_ids = set(sg_new_added_ids) - set(list_of_sg_filtered_ids)
    for sg_id in list_of_sg_filtered_ids:
        assert sg_id in cbl_doc_ids

    # Verify non filtered docs ids are not replicated in cbl
    for doc_id in list_of_non_sg_filtered_ids:
        assert doc_id not in cbl_doc_ids


def test_replication_configuration_with_headers(params_from_base_test_setup):
    """
        @summary:
        1. Create docs in CBL
        2. Make replication configuration by authenticating through headers
        4. Verify CBL docs with doc ids sent in configuration got replicated to SG

    """
    sg_db = "db"
    num_of_docs = 10

    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    channels = ["ABC"]
    sg_client = MobileRestClient()

    db.create_bulk_docs(num_of_docs, "cbll", db=cbl_db, channels=channels)

    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    auth_session = cookie, session
    sync_cookie = "{}={}".format(cookie, session)

    session_header = {"Cookie": sync_cookie}

    replicator = Replication(base_url)
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True, headers=session_header)
    repl = replicator.create(repl_config)
    repl_change_listener = replicator.addChangeListener(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    changes_count = replicator.getChangesCount(repl_change_listener)
    # changes = replicator.getChangesChangeListener(repl_change_listener)
    replicator.stop(repl)
    assert changes_count > 0, "did not get any changes"
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auth_session)

    # Verify database doc counts
    cbl_doc_ids = db.getDocIds(cbl_db)

    assert len(sg_docs["rows"]) == num_of_docs, "Number of sg docs should be equal to cbl docs"
    assert len(cbl_doc_ids) == num_of_docs, "Did not get expected number of cbl docs"

    # Check that all doc ids in CBL are replicated to SG
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc in cbl_doc_ids:
        assert doc in sg_ids


def setup_sg_cbl_docs(params_from_base_test_setup, sg_db, base_url, db, cbl_db, sg_url,
                      sg_admin_url, sg_blip_url, replication_type=None, document_ids=None,
                      channels=None, replicator_authenticator_type=None, headers=None,
                      cbl_id_prefix="cbl", sg_id_prefix="sg_doc",
                      num_cbl_docs=5, num_sg_docs=10):

    sg_client = MobileRestClient()

    db.create_bulk_docs(number=num_cbl_docs, id_prefix=cbl_id_prefix, db=cbl_db, channels=channels)
    cbl_added_doc_ids = db.getDocIds(cbl_db)
    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    auth_session = cookie, session
    sg_added_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=num_sg_docs, id_prefix=sg_id_prefix, channels=channels, auth=auth_session)
    sg_added_ids = [row["id"] for row in sg_added_docs]

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    if replicator_authenticator_type == "session":
        replicator_authenticator = authenticator.authentication(session, cookie, authentication_type="session")
    elif replicator_authenticator_type == "basic":
        replicator_authenticator = authenticator.authentication(username="autotest", password="password", authentication_type="basic")
    else:
        replicator_authenticator = None
    log_info("Configuring replicator")
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, replication_type=replication_type, continuous=False,
                                       documentIDs=document_ids, channels=channels, replicator_authenticator=replicator_authenticator, headers=headers)
    repl = replicator.create(repl_config)
    log_info("Starting replicator")
    replicator.start(repl)
    log_info("Waiting for replicator to go idle")
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    return sg_added_ids, cbl_added_doc_ids, auth_session


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("num_of_docs", [
    (10),
    (100),
    (10000)
])
def test_CBL_tombstone_doc(params_from_base_test_setup, num_of_docs):
    """
        @summary:
        1. Create docs in SG.
        2. pull replication to CBL with continuous
        3. tombstone doc in sG.
        4. wait for replication to finish
        5. Verify that tombstone doc is deleted in CBL too

    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    channels = ["Replication"]
    sg_client = MobileRestClient()

    # Modify sync-gateway config to use no-conflicts config
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Add docs to SG.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                   attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    assert len(sg_docs) == num_of_docs

    # 2. Pull replication to CBL
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="pull", replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # 3. tombstone doc in SG.
    doc_id = "sg_docs_6"
    doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=session)
    sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=doc_id, rev=doc['_rev'], auth=session)

    # 4. wait for replication to finish
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    cbl_doc_ids = db.getDocIds(cbl_db)
    assert doc_id not in cbl_doc_ids, "doc is expected to be deleted in CBL ,but not deleted"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("sg_conf_name, delete_doc_type", [
    ('listener_tests/listener_tests_no_conflicts', "purge"),
    ('listener_tests/listener_tests_no_conflicts', "expire")
])
def test_CBL_for_purged_doc(params_from_base_test_setup, sg_conf_name, delete_doc_type):
    """
        @summary:
        1. Create docs in SG.
        2. pull replication to CBL with continuous
        3. Purge doc or expire doc in SG.
        4. wait for replication to finish.
        5. Stop replication
        6. Verify that purged doc or expired doc is not deleted in CBL

    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    num_of_docs = 10

    if sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    channels = ["Replication"]
    sg_client = MobileRestClient()

    # Modify sync-gateway config to use no-conflicts config
    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    cl = cluster.Cluster(config=cluster_config)
    cl.reset(sg_config_path=sg_config)

    # 1. Add docs to SG.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                   attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    assert len(sg_docs) == num_of_docs

    # Create an expiry doc
    if delete_doc_type == "expire":
        doc_exp_3_body = document.create_doc(doc_id="exp_3", expiry=3, channels=channels)
        sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_exp_3_body, auth=session)
        doc_id = "exp_3"

    # 2. Pull replication to CBL
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="pull", replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # 3. Purge doc in SG.
    if delete_doc_type == "purge":
        doc_id = "sg_docs_7"
        doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=session)
        sg_client.purge_doc(url=sg_admin_url, db=sg_db, doc=doc)

    # expire doc
    if delete_doc_type == "expire":
        time.sleep(5)

    # 4. wait for replication to finish
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    cbl_doc_ids = db.getDocIds(cbl_db)
    assert doc_id in cbl_doc_ids, "{} document in did not existed in CBL after replication".format(delete_doc_type)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, delete_doc_type", [
    ('listener_tests/listener_tests_no_conflicts', "purge"),
    # ('listener_tests/listener_tests_no_conflicts', "expire") # not supported yet
])
def test_replication_purge_in_CBL(params_from_base_test_setup, sg_conf_name, delete_doc_type):
    """
        @summary:
        1. Create docs in CBL
        2. Push replication to SG.
        3. Purge or expire doc in CBL
        4. Continue  replication to SG
        5. Stop replication .
        6. Verify docs did not get removed in SG

    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    num_of_docs = 10
    doc_obj = Document(base_url)
    exp_doc_id = "exp_doc"

    if sync_gateway_version < "2.0":
        pytest.skip('It does not work with sg < 2.0 , so skipping the test')

    channels = ["Replication"]
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    # Modify sync-gateway config to use no-conflicts config

    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create CBL database
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # Create an expiry doc
    if delete_doc_type == "expire":
        doc_exp_3_body = document.create_doc(doc_id=exp_doc_id, expiry=3, channels=channels)
        mutable_doc = doc_obj.create(exp_doc_id, doc_exp_3_body)
        db.saveDocument(cbl_db, mutable_doc)

    # 2. push replication to SG.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="push", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    # 3. Purge doc in CBL
    cbl_doc_ids = db.getDocIds(cbl_db)
    removed_cbl_id = random.choice(cbl_doc_ids)
    if delete_doc_type == "purge":
        random_cbl_doc = db.getDocument(cbl_db, doc_id=removed_cbl_id)
        mutable_doc = doc_obj.toMutable(random_cbl_doc)
        db.purge(cbl_db, mutable_doc)

    # 3. Expire doc in CBL
    if delete_doc_type == "expire":
        time.sleep(10)
        removed_cbl_id = exp_doc_id

    cbl_doc_ids = db.getDocIds(cbl_db)
    assert removed_cbl_id not in cbl_doc_ids

    # 4. Continue  replication to SG
    replicator.wait_until_replicator_idle(repl)
    # 5. Stop replication
    replicator.stop(repl)

    # 6. Verify docs did not  purged in SG
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    assert removed_cbl_id in sg_doc_ids, "{} document got {}ed in SG".format(delete_doc_type, delete_doc_type)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name", [
    ('listener_tests/listener_tests_no_conflicts')
])
def test_replication_delete_in_CBL(params_from_base_test_setup, sg_conf_name):
    """
        @summary:
        1. Create docs in CBL
        2. Push replication to SG.
        3. Delete doc in CBL
        4. Continue replication to SG
        5. Stop replication .
        6. Verify deleted doc in CBL got removed in SG too

    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    num_of_docs = 10
    doc_obj = Document(base_url)

    if sync_gateway_version < "2.0":
        pytest.skip('It does not work with sg < 2.0 , so skipping the test')

    channels = ["Replication"]
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)

    # Modify sync-gateway config to use no-conflicts config
    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create CBL database
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # 2. push replication to SG.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="push", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    # 3. Delete doc in CBL
    cbl_doc_ids = db.getDocIds(cbl_db)
    random_cbl_id = random.choice(cbl_doc_ids)
    random_cbl_doc = db.getDocument(cbl_db, doc_id=random_cbl_id)
    mutable_doc = doc_obj.toMutable(random_cbl_doc)
    log_info("Deleting doc: {}".format(random_cbl_id))
    db.delete(database=cbl_db, document=mutable_doc)
    cbl_doc_ids = db.getDocIds(cbl_db)
    assert random_cbl_id not in cbl_doc_ids

    # 4. Continue  replication to SG
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # 6. Verify deleted doc in CBL got removed in SG too
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    assert random_cbl_id not in sg_doc_ids, "deleted doc in CBL did not removed in SG"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 4),
    ('listener_tests/listener_tests_no_conflicts', 100, 10),
    ('listener_tests/listener_tests_no_conflicts', 1000, 10)
])
def test_CBL_push_pull_with_sgAccel_down(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Have SG and SG accel up
        2. Create docs in CBL.
        3. push replication to SG
        4. update docs in SG.
        5. Bring down sg Accel
        6. Now Get pull replication to SG
        7. update docs in CBL
        8. Verify CBL can update docs successfully
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    username = "autotest"
    password = "password"

    if sync_gateway_version < "2.0" or sg_mode.lower() != "di":
        pytest.skip('sg < 2.0 or mode is not in di , so skipping the test')

    channels = ["Replication"]
    sg_client = MobileRestClient()

    # 1. Have SG and SG accel up
    # Modify sync-gateway config to use no-conflicts config
    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 2. Create docs in CBL.
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # 3. push replication to SG
    replication_type = "push"
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, channels, sg_client, cbl_db, sg_blip_url, replication_type)
    replicator.stop(repl)  # todo : trying removing this

    # 4. update docs in SG.
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs["rows"], number_updates=number_of_updates, auth=session)

    # 5. Bring down sg Accel
    c.sg_accels[0].stop()

    # 6. Now Get pull replication to SG
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False,
                                       replication_type="pull", channels=channels, replicator_authenticator=replicator_authenticator)

    repl1 = replicator.create(repl_config)
    replicator.start(repl1)
    replicator.wait_until_replicator_idle(repl1)
    replicator.stop(repl1)

    # update docs in CBL
    db.update_bulk_docs(database=cbl_db, number_of_updates=number_of_updates)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for doc in cbl_doc_ids:
        assert cbl_db_docs[doc]["updates-cbl"] == number_of_updates, "updates-cbl did not get updated"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs", [
    ('listener_tests/listener_tests_no_conflicts', 10)
])
def CBL_offline_test(params_from_base_test_setup, sg_conf_name, num_of_docs):
    """
        @summary:
        This test is meant to be run locally only, not on jenkins.
        1. Create docs in CBL1.
        2. push replication to SG.
        3. CBL goes offline(block outbound requests
        to SG through IPtables)
        4. Do updates on CBL
        5. Continue push replication to SG from CBL
        6. CBL comes online( unblock ports)
        7. push replication and do pull replication
        8. Verify conflicts resolved on CBL.
    """
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sg_config = params_from_base_test_setup["sg_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    channels = ["Replication"]
    username = "autotest"
    password = "password"
    number_of_updates = 3

    sg_client = MobileRestClient()
    db = Database(base_url)
    replicator = Replication(base_url)

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Create docs in CBL.
    cbl_db = db.create(cbl_db_name)
    # db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, generator="simple_user", attachments_generator=attachment.generate_png_100_100, channels=channels)
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)
    # 2. push replication to SG
    replication_type = "push"
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, channels, sg_client, cbl_db, sg_blip_url, replication_type)

    # 3. CBL goes offline(Block incomming requests of CBL to Sg)
    command = "mode=\"100% Loss\" osascript run_scripts/network_link_conditioner.applescript"
    return_val = os.system(command)
    if return_val != 0:
        raise Exception("{0} failed".format(command))

    # 4. Do updates on CBL
    time.sleep(180)
    db.update_bulk_docs(cbl_db, number_of_updates=number_of_updates)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # 6. CBL comes online( unblock ports)
    time.sleep(180)
    command = "mode=\"Wi-Fi\" osascript run_scripts/network_link_conditioner.applescript"
    return_val = os.system(command)
    if return_val != 0:
        raise Exception("{0} failed".format(command))

    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    # 8. Verify replication happened in sync_gateway
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    for doc in sg_docs["rows"]:
        assert doc["updates-cbl"] == number_of_updates, "sync gateway is not replicated after CBL is back online"

    # 7. Do pull replication
    replication_type = "pull"
    repl = replicator.configure_and_replicate(cbl_db, replicator_authenticator, target_url=sg_blip_url, replication_type=replication_type, continuous=True,
                                              channels=channels)
    replicator.stop(repl)

    # 8. Get Documents from CBL
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)

    db.update_bulk_docs(cbl_db, number_of_updates=1)

    # 9 Verify CBL updated successfully
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for doc in cbl_doc_ids:
        assert cbl_db_docs[doc]["updates-cbl"] == number_of_updates + 1, "updates-cbl did not get updated"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.session
@pytest.mark.parametrize("num_docs, need_attachments, replication_after_backgroundApp", [
    (1000, True, False),
    (10000, False, False),
    # (10000, False, True),
    # (1000, True, True)
])
def test_initial_pull_replication_background_apprun(params_from_base_test_setup, num_docs, need_attachments,
                                                    replication_after_backgroundApp):
    """
    @summary
    1. Add specified number of documents to sync-gateway.
    2. Start continous pull replication to pull the docs from a sync_gateway database.
    3. While docs are getting replicated , push the app to the background
    4. Verify if all of the docs got pulled and replication completed when app goes background
    """

    sg_db = "db"

    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    device_enabled = params_from_base_test_setup["device_enabled"]
    cbl_db = params_from_base_test_setup["source_db"]
    base_url = params_from_base_test_setup["base_url"]
    testserver = params_from_base_test_setup["testserver"]
    sg_config = params_from_base_test_setup["sg_config"]

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # No command to push the app to background on device, so avoid test to run on ios device
    if((liteserv_platform.lower() != "ios" and liteserv_platform.lower() != "android") or
       (liteserv_platform.lower() == "ios" and device_enabled)):
        pytest.skip('This test only valid for mobile')

    client = MobileRestClient()
    client.create_user(sg_admin_url, sg_db, "testuser", password="password", channels=["ABC", "NBC"])
    cookie, session_id = client.create_session(sg_admin_url, sg_db, "testuser")
    session = cookie, session_id
    # Add 'number_of_sg_docs' to Sync Gateway
    bulk_docs_resp = []
    if need_attachments:
        sg_doc_bodies = document.create_docs(
            doc_id_prefix="seeded_doc",
            number=num_docs,
            attachments_generator=attachment.generate_2_png_10_10,
            channels=["ABC"]
        )
    else:
        sg_doc_bodies = document.create_docs(doc_id_prefix='seeded_doc', number=num_docs, channels=["ABC"])
    # if adding bulk docs with huge attachment more than 5000 fails
    for x in xrange(0, len(sg_doc_bodies), 100000):
        chunk_docs = sg_doc_bodies[x:x + 100000]
        ch_bulk_docs_resp = client.add_bulk_docs(url=sg_admin_url, db=sg_db, docs=chunk_docs, auth=session)
        log_info("length of bulk docs resp{}".format(len(ch_bulk_docs_resp)))
        bulk_docs_resp += ch_bulk_docs_resp
    # docs = client.add_bulk_docs(url=sg_one_public, db=sg_db, docs=sg_doc_bodies, auth=session)
    assert len(bulk_docs_resp) == num_docs

    # Add a poll to make sure all of the docs have propagated to sync_gateway's _changes before initiating
    # the one shot pull replication to ensure that the client is aware of all of the docs to pull
    client.verify_docs_in_changes(url=sg_admin_url, db=sg_db, expected_docs=bulk_docs_resp, auth=session,
                                  polling_interval=10)

    db = Database(base_url)
    # Replicate to all CBL
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=False,
                                       replication_type="pull", replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl_config)
    replicator.start(repl)
    time.sleep(3)  # let replication go for few seconds and then make app go background
    testserver.close_app()
    time.sleep(10)  # wait until all replication is done
    testserver.open_app()
    # Verify docs replicated to client
    cbl_doc_ids = db.getDocIds(cbl_db)
    assert len(cbl_doc_ids) == len(bulk_docs_resp)
    sg_docs = client.get_all_docs(url=sg_admin_url, db=sg_db)
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc in cbl_doc_ids:
        assert doc in sg_ids

    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_docs, need_attachments, replication_after_backgroundApp", [
    (100, True, False),
    (10000, False, False),
    # (1000000, False, False)  you can run this locally if needed, jenkins cannot run more than 15 mins
])
def test_push_replication_with_backgroundApp(params_from_base_test_setup, num_docs, need_attachments,
                                             replication_after_backgroundApp):
    """
    @summary
    1. Prepare Testserver to have specified number of documents.
    2. Start continous push replication to push the docs into a sync_gateway database.
    3. While docs are getting replecated , push the app to the background
    4. Verify if all of the docs get pushed and replication continous when app goes background
    """

    sg_db = "db"

    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    device_enabled = params_from_base_test_setup["device_enabled"]
    cbl_db = params_from_base_test_setup["source_db"]
    base_url = params_from_base_test_setup["base_url"]
    testserver = params_from_base_test_setup["testserver"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    sg_url = params_from_base_test_setup["sg_url"]
    channels = ["ABC"]

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # No command to push the app to background on device, so avoid test to run on ios device
    if((liteserv_platform.lower() != "ios" and liteserv_platform.lower() != "android") or
       (liteserv_platform.lower() == "ios" and device_enabled)):
        pytest.skip('This test only valid for mobile and cannot run on iOS device')

    client = MobileRestClient()
    client.create_user(sg_admin_url, sg_db, "testuser", password="password", channels=channels)
    cookie, session_id = client.create_session(sg_admin_url, sg_db, "testuser")
    session = cookie, session_id

    # liteserv cannot handle bulk docs more than 100000, if you run more than 100000, it will chunk the
    # docs into set of 100000 and call add bulk docs
    if need_attachments:
        for x in xrange(0, num_docs, 100000):
            cbl_prefix = "cbl" + str(x)
            db.create_bulk_docs(num_docs, cbl_prefix, db=cbl_db, generator="simple_user",
                                attachments_generator=attachment.generate_png_100_100, channels=channels)
    else:
        cbl_prefix = "cbl" + str(x)
        db.create_bulk_docs(num_docs, cbl_prefix, db=cbl_db, channels=channels)

    cbl_doc_ids = db.getDocIds(cbl_db)
    assert len(cbl_doc_ids) == num_docs

    # Start replication after app goes background. So close app first and start replication
    db = Database(base_url)
    # Replicate to all CBL
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=False,
                                       replication_type="push", replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl_config)
    replicator.start(repl)
    time.sleep(3)  # let replication go for few seconds and then make app go background
    testserver.close_app()
    time.sleep(10)  # wait until all replication is done
    testserver.open_app()

    # Verify docs replicated to sync_gateway
    sg_docs = client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc_id in cbl_doc_ids:
        assert doc_id in sg_ids


@pytest.mark.sanity
@pytest.mark.listener
def test_replication_wrong_blip(params_from_base_test_setup):
    """
        @summary:
        1. Create docs in CBL
        2. Push replication to SG with wrong blip
        3. Verify it fails .
    """
    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    sg_blip_url = sg_blip_url.replace("ws", "http")
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    num_of_docs = 10
    username = "autotest"
    password = "password"

    channels = ["Replication"]
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)

    # Modify sync-gateway config to use no-conflicts config
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Create docs in CBL.
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # 2. Push replication to SG with wrong blip
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    with pytest.raises(Exception) as ex:
        replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    assert ex.value.message.startswith('400 Client Error: Bad Request for url:')
    assert "unsupported" in ex.value.message or "Invalid" in ex.value.message
    assert "ws" in ex.value.message and "wss" in ex.value.message


@pytest.mark.listener
@pytest.mark.parametrize("delete_source, attachments, number_of_updates", [
    ('sg', True, 1),
    ('cbl', True, 1),
    ('sg', False, 1),
    ('cbl', False, 1),
    ('sg', False, 5),
    ('cbl', False, 5),
])
def test_default_conflict_scenario_delete_wins(params_from_base_test_setup, delete_source, attachments, number_of_updates):
    """
        @summary:
        1. Create docs in CBL.
        2. Replicate docs to SG with push_pull and continous False
        3. Wait until replication is done and stop replication
        4. update doc in Sg and delete doc in CBL/ delete doc in Sg and update doc in CBL
        5. Verify delete wins
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    channels = ["replication-channel"]
    num_of_docs = 10
    username = "autotest"
    password = "password"

    # Reset cluster to clean the data
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    if attachments:
        db.create_bulk_docs(num_of_docs, "replication", db=cbl_db, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db.create_bulk_docs(num_of_docs, "replication", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()

    # Start and stop continuous replication
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(baseUrl=base_url, sg_admin_url=sg_admin_url, sg_db=sg_db, username=username, password=password,
                                                                                            channels=channels, sg_client=sg_client, cbl_db=cbl_db, sg_blip_url=sg_blip_url, replication_type="push_pull", continuous=False)
    replicator.stop(repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    if delete_source == 'cbl':
        with ThreadPoolExecutor(max_workers=4) as tpe:
            sg_updateDocs_task = tpe.submit(
                sg_client.update_docs, url=sg_url, db=sg_db, docs=sg_docs,
                number_updates=number_of_updates, auth=session
            )
            cbl_delete_task = tpe.submit(
                db.cbl_delete_bulk_docs, cbl_db=cbl_db
            )
            sg_updateDocs_task.result()
            cbl_delete_task.result()

    if delete_source == 'sg':
        with ThreadPoolExecutor(max_workers=4) as tpe:
            sg_delete_task = tpe.submit(
                sg_client.delete_docs, url=sg_url, db=sg_db, docs=sg_docs, auth=session
            )
            cbl_update_task = tpe.submit(
                db.update_bulk_docs, cbl_db, number_of_updates=number_of_updates
            )
            sg_delete_task.result()
            cbl_update_task.result()

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    assert len(cbl_docs) == 0, "did not delete docs after delete operation"
    repl_config = replicator.configure(cbl_db, sg_blip_url, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    assert len(cbl_docs) == 0, "did not delete docs after delete operation"
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    assert len(sg_docs) == 0, "did not delete docs in sg after delete operation in CBL"
    replicator.stop(repl)

    # create docs with deleted docs id and verify replication happens without any issues.
    if attachments:
        db.create_bulk_docs(num_of_docs, "replication", db=cbl_db, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db.create_bulk_docs(num_of_docs, "replication", db=cbl_db, channels=channels)

    replicator.configure_and_replicate(source_db=cbl_db, replicator_authenticator=replicator_authenticator, target_url=sg_blip_url, continuous=False,
                                       channels=channels)

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    # assert len(cbl_docs) == le "did not delete docs after delete operation"
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    assert len(cbl_docs) == num_of_docs
    assert len(sg_docs) == len(cbl_docs), "new doc created with same doc id as deleted docs are not created and replicated"


@pytest.mark.listener
@pytest.mark.parametrize("highrev_source, attachments", [
    ('sg', True),
    ('cbl', True),
    ('sg', False),
    ('cbl', False),
])
def test_default_conflict_scenario_highRevGeneration_wins(params_from_base_test_setup, highrev_source, attachments):

    """
        @summary:
        1. Create docs in CBL.
        2. Replicate docs to SG with push_pull and continous false
        3. Wait unitl replication done and stop replication.
        4. update doc 1 times in Sg and update doc 2 times in CBL and vice versa in 2nd scenario
        5. Start replication with push pull and continous False.
        6. Wait until replication done
        7. Verfiy doc with higher rev id is updated in CBL.
        8. Now update docs in sync gateway 3 times.
        9. Start replication with push pull and continous False.
        10. Wait until replication is done
        11. As sync-gateway revision id is higher, docs from
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    channels = ["replication-channel"]
    num_of_docs = 10

    # Reset cluster to clean the data
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    if attachments:
        db.create_bulk_docs(num_of_docs, "replication", db=cbl_db, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db.create_bulk_docs(num_of_docs, "replication", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()

    # Start and stop continuous replication
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username="autotest", password="password", channels=channels)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(
        baseUrl=base_url, sg_admin_url=sg_admin_url, sg_db=sg_db, channels=channels, sg_client=sg_client, cbl_db=cbl_db, sg_blip_url=sg_blip_url, username="autotest", password="password", replication_type="push_pull", continuous=False)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    if highrev_source == 'cbl':
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=session)
        db.update_bulk_docs(cbl_db, number_of_updates=2)

    if highrev_source == 'sg':
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session, number_updates=2)
        db.update_bulk_docs(cbl_db)

    repl_config = replicator.configure(cbl_db, sg_blip_url, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session, include_docs=True)
    sg_docs = sg_docs["rows"]
    sg_docs_values = [doc['doc'] for doc in sg_docs]
    print "\n\nsg docs are ", sg_docs_values

    if highrev_source == 'cbl':
        for doc in cbl_docs:
            assert cbl_docs[doc]["updates-cbl"] == 2, "cbl with high rev id is not updated "
    if highrev_source == 'sg':
        for doc in cbl_docs:
            assert cbl_docs[doc]["updates"] == 2, "cbl with high rev id is not updated "
        for i in xrange(len(sg_docs_values)):
            assert sg_docs_values[i]["updates"] == 2, "sg with high rev id is not updated"

    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=3, auth=session)
    repl_config = replicator.configure(cbl_db, sg_blip_url, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    print "\n\ncbl docs are ", cbl_docs
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session, include_docs=True)
    sg_docs = sg_docs["rows"]
    sg_docs_values = [doc['doc'] for doc in sg_docs]
    for doc in cbl_docs:
        if highrev_source == 'cbl':
            verify_updates = 4
        if highrev_source == 'sg':
            verify_updates = 5
        assert cbl_docs[doc]["updates"] == verify_updates, "cbl with high rev id is not updated "
        for i in xrange(len(sg_docs_values)):
            assert sg_docs_values[i]["updates"] == verify_updates, "sg with high rev id is not updated"

    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.parametrize("highrevId_source, attachments", [
    ('sg', True),
    ('cbl', True),
    ('sg', False),
    ('cbl', False),
])
def test_default_conflict_scenario_highRevID_wins(params_from_base_test_setup, highrevId_source, attachments):
    """
        @summary:
        1. Create docs in CBL.
        2. Replicate docs to SG with push_pull and continous false
        3. Wait unitl replication done and stop replication.
        4. For high revision id in Sg: update doc 1 time in Sg and and create a conflict with lowest revision id to have higher revision in CBL
           For high revision id in Sg : update doc 1 time in Sg and and create a conflict with highest revision id to have lower revision in CBL
        5. Start replication pull with one shot replication
        6. Wait until replication done
        7. Verfiy doc with higher rev id is updated in CBL.
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    channels = ["replication-channel"]
    num_of_docs = 10

    # Reset cluster to clean the data
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    if attachments:
        db.create_bulk_docs(num_of_docs, "replication", db=cbl_db, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db.create_bulk_docs(num_of_docs, "replication", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()

    # Start and stop continuous replication
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username="autotest", password="password", channels=channels)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(
        baseUrl=base_url, sg_admin_url=sg_admin_url, sg_db=sg_db, channels=channels, sg_client=sg_client, cbl_db=cbl_db, sg_blip_url=sg_blip_url, username="autotest", password="password", replication_type="push_pull", continuous=False)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    db.update_bulk_docs(database=cbl_db, number_of_updates=2)
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=session)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    if highrevId_source == 'cbl':
        new_revision = "3-00000000000000000000000000000000"
    if highrevId_source == 'sg':
        new_revision = "3-ffffffffffffffffffffffffffffffff"
        for i in xrange(len(sg_docs)):
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=sg_docs[i]["id"], parent_revisions=sg_docs[i]["value"]["rev"], new_revision=new_revision, auth=session)
        replicator.configure_and_replicate(source_db=cbl_db, replicator_authenticator=replicator_authenticator, target_url=sg_blip_url, replication_type="push_pull", continuous=False,
                                           channels=channels, err_check=True)

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)

    if highrevId_source == 'cbl':
        for doc in cbl_docs:
            assert cbl_docs[doc]["updates-cbl"] == 2, "higher revision id on CBL did not win with conflict resolution in cbl"
            assert cbl_docs[doc]["updates"] == 0, "higher revision id on CBL did not win with conflict resolution in cbl"
    if highrevId_source == 'sg':
        for doc in cbl_docs:
            assert cbl_docs[doc]["updates"] == 1, "higher revision id on SG did not win with conflict resolution in cbl"
            try:
                cbl_docs[doc]["updates-cbl"]
                assert False, "higher revision id on SG did not win with conflict resolution in cbl"
            except KeyError:
                assert True


@pytest.mark.listener
def test_default_conflict_scenario_1(params_from_base_test_setup):
    """
        @summary:
        1. create docs in sg.
        2. Create two conflicts with 2-hex in sg.
        3. update doc in sg to have new revision to one of the conflicted branch of sg.
        4. pull to CBL.
        5. Verify that default conflict resolver resolved appropriately.
        6. start replication and push to SG.
        7. Verify the docs in CBL got replicated to sg.
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]

    if no_conflicts_enabled:
        pytest.skip('--no-conflicts is not  enabled , so skipping the test')
    channels = ["replication-channel"]
    num_of_docs = 1
    username = "autotest"
    password = "password"

    # Reset cluster to clean the data
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Create docs in SG.
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session = cookie, session_id
    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    print "sg docs after adding is ", sg_docs
    # 2. Create two conflicts with 2-hex in sg.
    for i in xrange(len(sg_docs)):
        sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=sg_docs[i]["id"], parent_revisions=sg_docs[i]["rev"],
                               new_revision="2-41FA", auth=session)
        sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=sg_docs[i]["id"], parent_revisions=sg_docs[i]["rev"],
                               new_revision="2-41FA9B", auth=session)

    # 3. update doc in sg to have new revision to one of the conflicted branch of sg.
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                          auth=session, channels=channels)

    # 4. pull replication to CBL
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db, replicator_authenticator=replicator_authenticator, target_url=sg_blip_url,
                                              replication_type="push_pull", continuous=True, channels=channels)

    # Now update doc in cbl and replicate to sync_gateway
    db.update_bulk_docs(database=cbl_db, number_of_updates=1)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    # 5. Verify updated doc from cbl is pushed to sg.
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session, include_docs=True)
    sg_docs = sg_docs["rows"]
    for doc in sg_docs:
        doc["doc"]["updates-cbl"] == 1, "cbl update did not pushed to sg"


@pytest.mark.listener
def test_CBL_push_pull_with_sg_down(params_from_base_test_setup):
    """
        @summary:
        1. Have SG and SG accel up
        2. Create docs in CBL.
        3. push replication to SG
        4. update docs in SG.
        5. Bring down sg Accel
        6. Now Get pull replication to SG
        7. update docs in CBL
        8. Verify CBL can update docs successfully
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    username = "autotest"
    password = "password"
    num_of_docs = 1000

    channels = ["Replication"]
    sg_client = MobileRestClient()

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 2. Create docs in CBL.
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels, attachments_generator=attachment.generate_2_png_10_10)

    # 3. push replication to SG
    replicator = Replication(base_url)

    authenticator = Authenticator(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    with ThreadPoolExecutor(max_workers=4) as tpe:
        wait_until_replicator_completes = tpe.submit(
            replicator.configure_and_replicate,
            source_db=cbl_db, replicator_authenticator=replicator_authenticator, target_db=None, target_url=sg_blip_url, replication_type="push_pull", continuous=True,
            channels=channels, err_check=False
        )

        start_sg_task = tpe.submit(
            restart_sg,
            c=c,
            sg_conf=sg_config,
            cluster_config=cluster_config
        )
        repl = wait_until_replicator_completes.result()
        start_sg_task.result()

    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    # print "cbl docs are ", cbl_db_docs
    assert len(sg_docs) == len(cbl_doc_ids), "docs did not replicated when sync-gateway restarted"
    assert len(sg_docs) == num_of_docs
    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.parametrize("topology_type, num_of_docs, attachments", [
    ('1cbl_1sg', 10, True),
    ('3cbl_1sg', 10, True),
    ('1cbl_1sg', 10, False),
    ('3cbl_1sg', 10, False)
])
def test_replication_with_3Channels(params_from_base_test_setup, setup_customized_teardown_test, topology_type, num_of_docs, attachments):
    """
        @summary:
        1. Create 3 users in SG with 3 differrent channels.
        2. Create docs in sg in all 3 channels
        3. replication to CBL with continous true and push_pull on 3 CBL DBs assosciated with each sg channel.
        4. verify in CBL , docs got replicated to each DB appropirately

    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    num_of_docs = 10

    channel1 = ["Replication-1"]
    channel2 = ["Replication-2"]
    channel3 = ["Replication-3"]

    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]

    if topology_type == "1cbl_1sg":
        cbl_db1 = cbl_db
        cbl_db2 = cbl_db
        cbl_db3 = cbl_db

    username1 = "autotest"
    username2 = "autotest2"
    username3 = "autotest3"
    password = "password"

    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Create 3 users in SG with 3 differrent channels.
    sg_client.create_user(sg_admin_url, sg_db, username1, password=password, channels=channel1)
    cookie1, session_id1 = sg_client.create_session(sg_admin_url, sg_db, username1)
    session1 = cookie1, session_id1

    sg_client.create_user(sg_admin_url, sg_db, username2, password=password, channels=channel2)
    cookie2, session_id2 = sg_client.create_session(sg_admin_url, sg_db, username2)
    session2 = cookie2, session_id2

    sg_client.create_user(sg_admin_url, sg_db, username3, password=password, channels=channel3)
    cookie3, session_id3 = sg_client.create_session(sg_admin_url, sg_db, username3)
    session3 = cookie3, session_id3

    # 2. Create docs in sg in all 3 channels
    sg_docs = document.create_docs(doc_id_prefix='sg_docs-1', number=num_of_docs, channels=channel1)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session1)

    sg_docs2 = document.create_docs(doc_id_prefix='sg_docs-2', number=num_of_docs, channels=channel2)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs2, auth=session2)

    sg_docs3 = document.create_docs(doc_id_prefix='sg_docs-3', number=num_of_docs, channels=channel3)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs3, auth=session3)

    # 3. replication to CBL with continous true and push_pull on 3 CBL DBs assosciated with each sg channel.
    replicator = Replication(base_url)
    replicator_authenticator1 = authenticator.authentication(session_id1, cookie1, authentication_type="session")
    repl1 = replicator.configure_and_replicate(source_db=cbl_db1, replicator_authenticator=replicator_authenticator1, target_url=sg_blip_url,
                                               replication_type="pull", continuous=False, channels=channel1)
    replicator_authenticator2 = authenticator.authentication(session_id2, cookie2, authentication_type="session")
    repl2 = replicator.configure_and_replicate(source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg_blip_url,
                                               replication_type="pull", continuous=False, channels=channel2)
    replicator_authenticator3 = authenticator.authentication(session_id3, cookie3, authentication_type="session")
    repl3 = replicator.configure_and_replicate(source_db=cbl_db3, replicator_authenticator=replicator_authenticator3, target_url=sg_blip_url,
                                               replication_type="pull", continuous=False, channels=channel3)

    # 4. verify in CBL , docs got replicated to each DB appropirately
    verify_sgDocIds_cblDocIds(sg_client, sg_url, sg_db, session1, cbl_db1, db)
    verify_sgDocIds_cblDocIds(sg_client, sg_url, sg_db, session2, cbl_db2, db)
    verify_sgDocIds_cblDocIds(sg_client, sg_url, sg_db, session3, cbl_db3, db)
    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


@pytest.mark.listener
@pytest.mark.parametrize("topology_type", [
    ('2cbl_2sg'),
    ('1cbl_2sg')
])
def test_replication_withChannels1_withMultipleSgDBs(params_from_base_test_setup, setup_customized_teardown_test, topology_type):
    """
        @summary:
        1. Create 2 users in SG with 2 SG dbs with 2 differrent channels.
        2. Create docs in sg in all 2 channels with 2 sg DBs
        3. replication to CBL with continous False and push_pull on 2 CBL DBs assosciated with each sg Dbs.
        4. verify in CBL , docs got replicated to each DB appropirately

    """
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_mode = params_from_base_test_setup["mode"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    num_of_docs = 10
    sg_blip_url1 = sg_blip_url.replace("db", "sg_db1")
    sg_blip_url2 = sg_blip_url.replace("db", "sg_db2")

    channel1 = ["Replication-1"]
    channel2 = ["Replication-2"]

    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]

    username1 = "autotest"
    username2 = "autotest2"
    password = "password"

    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)

    c = cluster.Cluster(config=cluster_config)
    sg_config = sg_config = sync_gateway_config_path_for_mode("listener_tests/multiple_sync_gateways", sg_mode)
    c.reset(sg_config_path=sg_config)

    # 1. Create 2 users in SG with 2 differrent channels.
    sg_client.create_user(sg_admin_url, sg_db1, username1, password=password, channels=channel1)
    cookie1, session_id1 = sg_client.create_session(sg_admin_url, sg_db1, username1)
    session1 = cookie1, session_id1

    sg_client.create_user(sg_admin_url, sg_db2, username2, password=password, channels=channel2)
    cookie2, session_id2 = sg_client.create_session(sg_admin_url, sg_db2, username2)
    session2 = cookie2, session_id2

    # 2. Create docs in sg in 2 channels
    sg_docs = document.create_docs(doc_id_prefix='sg_docs-1', number=num_of_docs, channels=channel1)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db1, docs=sg_docs, auth=session1)

    sg_docs2 = document.create_docs(doc_id_prefix='sg_docs-2', number=num_of_docs, channels=channel2)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db2, docs=sg_docs2, auth=session2)

    # 3. replication to CBL with continous true and push_pull on 2 CBL DBs assosciated with each sg channel.
    if topology_type == "1cbl_2sg":
        cbl_db1 = cbl_db
        cbl_db2 = cbl_db
    replicator = Replication(base_url)
    replicator_authenticator1 = authenticator.authentication(session_id1, cookie1, authentication_type="session")
    repl1 = replicator.configure_and_replicate(source_db=cbl_db1, replicator_authenticator=replicator_authenticator1, target_url=sg_blip_url1,
                                               replication_type="pull", continuous=False, channels=channel1)
    replicator_authenticator2 = authenticator.authentication(session_id2, cookie2, authentication_type="session")
    repl2 = replicator.configure_and_replicate(source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg_blip_url2,
                                               replication_type="pull", continuous=False, channels=channel2)

    # 4. verify in CBL , docs got replicated to each DB appropirately
    verify_sgDocIds_cblDocIds(sg_client, sg_url, sg_db1, session1, cbl_db1, db)
    verify_sgDocIds_cblDocIds(sg_client, sg_url, sg_db2, session2, cbl_db2, db)
    replicator.stop(repl1)
    replicator.stop(repl2)


def restart_sg(c, sg_conf, cluster_config):
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=cluster_config)
    log_info("starting sg ....")
    assert status == 0, "sync_gateway did not start"


def verify_sgDocIds_cblDocIds(sg_client, url, sg_db, session, cbl_db, db):
    sg_docs = sg_client.get_all_docs(url=url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    sg_doc_ids = [row["id"] for row in sg_docs]
    cbl_doc_ids = db.getDocIds(cbl_db)
    for id in sg_doc_ids:
        assert id in cbl_doc_ids, "sg doc is not replicated to cbl "
