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

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords import document, attachment
from libraries.testkit import cluster


@pytest.fixture(scope="function")
def setup_teardown_test(params_from_base_test_setup):
    cbl_db_name = "cbl_db"
    base_url = params_from_base_test_setup["base_url"]
    db = Database(base_url)
    db_config = db.configure()
    cbl_db = db.create(cbl_db_name, db_config)
    print "setting up db"

    yield{
        "db": db,
        "cbl_db": cbl_db,
        "cbl_db_name": cbl_db_name
    }
    print "tearing down db"
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
    print " sg docs are replication is ", sg_docs
    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    # Check that all docs of CBL got replicated to CBL
#     for doc in sg_docs["rows"]:
#         assert db.contains(cbl_db, str(doc["id"]))
    time.sleep(2)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    print "cbl db docs are ", cbl_db_docs
    for doc in cbl_doc_ids:
        if continuous == True:
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
    print "sg docs in test are ", sg_docs["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    print "cbl docs in test are ", db.getDocuments(cbl_db, cbl_doc_ids)

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
    liteserver_platform =  params_from_base_test_setup["liteserv_platform"]

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
    if liteserver_platform == "ios":
        assert "401 Unauthorized" in error, "expected error did not occurred"
    else:
        assert "code=401" in error, "expected error did not occurred"
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
    liteserver_platform =  params_from_base_test_setup["liteserv_platform"]

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
    if liteserver_platform == "ios":
        assert "401 Unauthorized" in error, "expected error did not occurred"
    else:
        assert "code=401" in error, "expected error did not occurred"
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
def test_replication_configuration_with_filtered_doc_ids(params_from_base_test_setup):
    """
        @summary:
        1. Create docs in SG
        2. Create docs in CBL
        3. Send doc ids which you want to have replication to the docs ids passed in replication configuration
        4. Verify CBL docs with doc ids sent in configuration got replicated to SG

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

    db.create_bulk_docs(10, "cbl", db=cbl_db, channels=channels)
    cbl_added_doc_ids = db.getDocIds(cbl_db)
    num_of_filtered_ids = 5
    list_of_filtered_ids = random.sample(cbl_added_doc_ids, num_of_filtered_ids)

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

    # Now filter doc ids
    authenticator = Authenticator(base_url)
    cookie, session_id = session
    print "cookie in authentication is ", cookie
    print "session id in authentication is ", session_id
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    list_of_sg_filtered_ids = random.sample(sg_added_doc_ids, num_of_filtered_ids)
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=False,
                                       documentIDs=list_of_sg_filtered_ids, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    print "replicator created , now starting"
    replicator.start(repl)
    print "replicator wait until replicator idle"
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # Verify only filtered sg ids are replicated to cbl
    cbl_doc_ids = db.getDocIds(cbl_db)
    list_of_non_sg_filtered_ids = set(sg_added_doc_ids) - set(list_of_sg_filtered_ids)
    for sg_id in list_of_sg_filtered_ids:
        assert sg_id in cbl_doc_ids

    # Verify non filtered docs ids are not replicated in cbl
    for doc_id in list_of_non_sg_filtered_ids:
        assert doc_id not in sg_ids


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
    changes = replicator.getChangesChangeListener(repl_change_listener)
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
                      sg_admin_url, sg_blip_url, replication_type=None, document_ids=None, channels=None,
                      replicator_authenticator_type=None, headers=None):

    sg_client = MobileRestClient()

    db.create_bulk_docs(5, "cbl", db=cbl_db, channels=channels)
    cbl_added_doc_ids = db.getDocIds(cbl_db)
    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    auth_session = cookie, session
    sg_added_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=10, id_prefix="sg_doc", channels=channels, auth=auth_session)
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
    print "Authentication is done, now will be doing configuration"
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, replication_type=replication_type, continuous=False,
                                       documentIDs=document_ids, channels=channels, replicator_authenticator=replicator_authenticator, headers=headers)
    repl = replicator.create(repl_config)
    print "replicator created , now starting"
    replicator.start(repl)
    print "replicator wait until replicator idle"
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    return sg_added_ids, cbl_added_doc_ids, auth_session


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("num_of_docs", [
    (10),
    (100),
    (1000)
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
    print "cbl_doc_ids are", cbl_doc_ids
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
        # TODO : complete after this issue fixed
        https://github.com/couchbase/sync_gateway/issues/3165
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
    print "CBL docs at the end is ", cbl_db_docs

    db.update_bulk_docs(cbl_db, number_of_updates=1)

    # 9 Verify CBL updated successfully
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for doc in cbl_doc_ids:
        assert cbl_db_docs[doc]["updates-cbl"] == number_of_updates + 1, "updates-cbl did not get updated"
