import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Dictionary import Dictionary
from CBLClient.Document import Document
from CBLClient.Query import Query
from CBLClient.Utils import Utils

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster


def test_replication_configuration_valid_values(setup_client_syncgateway_test):
    """
        @summary: 
        1. Create CBL DB and create bulk doc in CBL
        2. Configure replication with valid values of valid cbl Db, valid target url 
        3. Start replication with push and pull
        4. Verify replication is successful and verify docs exist
    """
    # source_db = None
    base_url = "http://192.168.0.103:8989"
    db = Database(base_url)
    
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_blip_url = sg_admin_url.replace("http", "blip")
    sg_blip_url = "{}/db".format(sg_blip_url)
    num_docs = 4
    channels_sg = ["ABC"]

    # Create CBL database
    cbl_db = db.create(cbl_db_name)
    log_info("Database is {}".format(cbl_db))
    sg_client = MobileRestClient()

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels_sg)
    session = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    
    db.create_bulk_docs(5, "cbl", db=cbl_db, channels=channels_sg)
    
    # Start and stop continuous replication
    replicator = Replication(base_url)
    
    repl = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True)
    replicator.start(repl)
    time.sleep(1)
    replicator.stop(repl)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    log_info("sg doc full details >><<{}".format(sg_docs["rows"]))

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    cbl_docs = db.getDocIds(cbl_db)
    assert len(sg_docs["rows"]) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    # Check that all doc ids in SG are also present in CBL
    for doc in sg_docs["rows"]:
        assert db.contains(cbl_db, str(doc["id"]))
    

@pytest.mark.sanity
@pytest.mark.listener
def test_replication_configuration_with_pull_replication(setup_client_syncgateway_test):
    """
        @summary: 
        1. Create CBL DB and create bulk doc in CBL
        2. Configure replication with empty string of source db
        3. Verify that it throws http error bad request
        4. Configure replication with source db None
        5. Verify that it throws invalid type of db
        6. Configure replication with empty target url
        7. Verify that it throws http error bad request
        8. Configure replication with target url None
        9. Verify that it throws invalid type
        10. Configure replication with empty target db
        11. Verify that it throws http error bad request
        12. Configure replication with target db None
        13. Verify that it throws invalid type
    
    """
    sg_db = "db"
    base_url = "http://10.17.0.133:8989"
    db = Database(base_url)
    cbl_db_name = "cbl_db"

    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]
    sg_blip_url = sg_admin_url.replace("http", "blip")
    sg_blip_db_url = "{}/db".format(sg_blip_url)
    channels = ["ABC"]

    sg_client = MobileRestClient()

    sg_added_doc_ids, cbl_added_doc_ids, cbl_db, session = setup_sg_cbl_docs(setup_client_syncgateway_test, sg_db=sg_db, base_url=base_url, db=db,
                                                                             cbl_db_name=cbl_db_name, sg_url=sg_url, sg_admin_url=sg_admin_url, sg_blip_url=sg_blip_db_url,
                                                                             replication_type="pull", channels=channels)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)

    assert len(sg_docs["rows"]) == 10, "Number of sg docs is not equal to total number of cbl docs and sg docs"
    assert cbl_doc_count == 15, "Did not get expected number of cbl docs"
    
    # Check that all doc ids in SG are also present in CBL
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc in cbl_added_doc_ids:
        assert doc not in sg_ids

    # Verify sg docs does not exist in CBL as it is just a push replication
    for id in sg_added_doc_ids:
        assert id in cbl_doc_ids


@pytest.mark.sanity
@pytest.mark.listener
def test_replication_configuration_with_push_replication(setup_client_syncgateway_test):
    """
        @summary:
        1. Create docs in SG
        2. Create docs in CBL
        3. Do push replication with session authenticated user
        4. Verify CBL docs got replicated to SG
        5. Verify sg docs not replicated to CBL
    
    """
    sg_db = "db"
    base_url = "http://10.17.0.133:8989"
    db = Database(base_url)
    cbl_db_name = "cbl_db"

    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]
    sg_blip_url = sg_url.replace("http", "blip")
    sg_blip_url = "{}/db".format(sg_blip_url)
    channels = ["ABC"]

    sg_client = MobileRestClient()
    sg_added_doc_ids, cbl_added_doc_ids, cbl_db = setup_sg_cbl_docs(setup_client_syncgateway_test, sg_db=sg_db, base_url=base_url, db=db,
                                                                    cbl_db_name=cbl_db_name, sg_url=sg_url, sg_admin_url=sg_admin_url, sg_blip_url=sg_blip_url,
                                                                    replication_type="push", channels=channels, replicator_authenticator="session")
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
    for id in sg_added_doc_ids:
        assert id not in cbl_doc_ids


@pytest.mark.sanity
@pytest.mark.listener
def test_replication_push_replication_without_authentication(params_from_base_test_setup):
    """
        @summary: 
        1. Create docs in CBL
        2. Create docs in SG
        3. Do push replication without authentication.
        4. Verify docs are not replicated without authentication
    
    """
    sg_db = "db"
    base_url = "http://192.168.0.103:8989"
    db = Database(base_url)
    cbl_db_name = "cbl_db"

    sg_url = params_from_base_test_setup["sg_url"]
    print "set up of conftest is done"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = sg_url.replace("http", "blip")
    sg_blip_url = "{}/db".format(sg_blip_url)
    channels = ["ABC"]

    sg_client = MobileRestClient()
    sg_added_doc_ids, cbl_added_doc_ids, cbl_db, auth_session = setup_sg_cbl_docs(params_from_base_test_setup, sg_db=sg_db, base_url=base_url, db=db,
                                                                                  cbl_db_name=cbl_db_name, sg_url=sg_url, sg_admin_url=sg_admin_url, sg_blip_url=sg_blip_url,
                                                                                  replication_type="push", channels=channels)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auth_session)
    
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)

    assert len(sg_docs["rows"]) == 10, "Number of sg docs is not same previous number before replication as authentication is not provided"

    # Check that all doc ids in CBL are not replicated to SG
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc in cbl_doc_ids:
        assert doc not in sg_ids

@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize(
    'replicator_authenticator, invalid_username, invalid_password, invalid_session, invalid_cookie',
    [
        # ('basic', 'invalid_user', 'password', None, None),
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
    base_url = "http://10.17.0.133:8989"
    db = Database(base_url)
    cbl_db_name = "cbl_db"

    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = sg_url.replace("http", "blip")
    sg_blip_url = "{}/db".format(sg_blip_url)
    channels = ["ABC"]

    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    db.create_bulk_docs(5, "cbl", db=cbl_db, channels=channels)
    cbl_added_doc_ids = db.getDocIds(cbl_db)
    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    auth_session = cookie, session
    sg_added_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=10, id_prefix="sg_doc", channels=channels, auth=auth_session)
    sg_added_ids = [row["id"] for row in sg_added_docs]

    replicator = Replication(base_url)
    if replicator_authenticator == "session":
        replicator_authenticator = replicator.authentication(invalid_session, invalid_cookie, authentication_type="session")
    elif replicator_authenticator == "basic":
        replicator_authenticator = replicator.authentication(username=invalid_username, password=invalid_password, authentication_type="basic")
    repl = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True, replication_type="push", replicator_authenticator=replicator_authenticator)
    
    log_info("replicator status  is {}".format(replicator.status))
    log_info("replicator error is {}".format(replicator.get_error))
    replicator.start(repl)
    time.sleep(1)
    replicator.stop(repl)

    """

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)

    assert len(sg_docs["rows"]) == 10, "Number of sg docs is not same as number of docs before replication"
    assert cbl_doc_count == 5, "Did not get expected number of cbl docs"

    # Check that all doc ids in SG are also present in CBL
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc in cbl_doc_ids:
        assert doc not in sg_ids
    """

@pytest.mark.sanity
@pytest.mark.listener
def test_replication_configuration_with_filtered_doc_ids(setup_client_syncgateway_test):
    """
        @summary:
        1. Create docs in SG
        2. Create docs in CBL
        3. Send doc ids which you want to have replication to the docs ids passed in replication configuration
        4. Verify CBL docs with doc ids sent in configuration got replicated to SG
    
    """
    sg_db = "db"
    base_url = "http://10.17.0.133:8989"
    db = Database(base_url)
    cbl_db_name = "cbl_db"

    sg_blip_url = setup_client_syncgateway_test["target_url"]
    channels = ["ABC"]

    sg_mode = setup_client_syncgateway_test["sg_mode"]
    cluster_config = setup_client_syncgateway_test["cluster_config"]
    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_blip", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    db.create_bulk_docs(5, "cbl", db=cbl_db, channels=channels)
    cbl_added_doc_ids = db.getDocIds(cbl_db)

    sg_docs = sg_client.get_all_docs(url=sg_blip_url, db=sg_db)
    
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
    # for id in sg_added_doc_ids:
    #    assert id not in cbl_doc_ids


def test_replication_configuration_with_headers(params_from_base_test_setup):
    """
        @summary:
        1. Create docs in CBL
        2. Make replication configuration by authenticating through headers
        4. Verify CBL docs with doc ids sent in configuration got replicated to SG
    
    """
    sg_db = "db"
    base_url = "http://10.17.1.161:8989"
    db = Database(base_url)
    cbl_db_name = "cbl_db"
    num_of_docs = 10

    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    channels = ["ABC"]

    # Create CBL database
    cbl_db = db.create(cbl_db_name)
    sg_client = MobileRestClient()

    db.create_bulk_docs(num_of_docs, "cbll", db=cbl_db, channels=channels)
    cbl_added_doc_ids = db.getDocIds(cbl_db)

    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    auth_session = cookie, session
    sync_cookie = "{}={}".format(cookie, session)
    
    session_header = {"Cookie": sync_cookie}
    
    replicator = Replication(base_url)
    # repl = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True, headers=session_header)
    repl = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True)
    
    replicator.start(repl)
    time.sleep(1)
    replicator.stop(repl)
    repl_status_msg = replicator.status(repl)
    repl_change_listener = replicator.add_change_listener(repl)
    replicator.get_changes_changelistener(repl, repl_change_listener)
    print " replicator status msg ", repl_status_msg
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auth_session)
    
    # Verify database doc counts
    cbl_doc_ids = db.getDocIds(cbl_db)

    assert len(sg_docs["rows"]) == num_of_docs, "Number of sg docs should be equal to cbl docs"
    assert len(cbl_doc_ids) == num_of_docs, "Did not get expected number of cbl docs"

    # Check that all doc ids in CBL are replicated to SG
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc in cbl_doc_ids:
        assert doc in sg_ids


def setup_sg_cbl_docs(params_from_base_test_setup, sg_db, base_url, db, cbl_db_name, sg_url,
                      sg_admin_url, sg_blip_url, replication_type, document_ids=None, channels=None, 
                      replicator_authenticator_type=None, headers=None):
    
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_blip", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

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
    if replicator_authenticator_type == "session":
        replicator_authenticator = replicator.authentication(session, cookie, authentication_type="session")
    elif replicator_authenticator_type == "basic":
        replicator_authenticator = replicator.authentication(username="autotest", password="password", authentication_type="basic")
    else:
        replicator_authenticator = None
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, replication_type=replication_type, continuous=True,
                                       documentIDs=document_ids, channels=channels, replicator_authenticator=replicator_authenticator, headers=headers)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    time.sleep(1)
    replicator.stop(repl)

    return sg_added_ids, cbl_added_doc_ids, cbl_db, auth_session
