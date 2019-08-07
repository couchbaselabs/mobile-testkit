import pytest

from time import sleep

from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.utils import log_info, random_string
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient

from testsuites.CBLTester.CBL_Functional_tests.TestSetup_FunctionalTests.test_delta_sync import property_updater


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
@pytest.mark.parametrize("replicator_type", [
    "pull",
    "push_pull"
])
def test_local_wins_custom_conflicts(params_from_base_test_setup, replicator_type):
    """
    @summary: resolve conflicts as per local doc
    1. Create few docs in app and get them replicated to SG. Stop the replication once docs are replicated.
    2. Update docs couple of times with different updates on both SG and CBL app. This will create conflict.
    3. Start the replication with local_win CCR algorithm
    4. Verifies that CBL has retains its changes. For push and pull replication SG changes should be override with
    that of CBL
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "local_win_conflicts", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG url: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]

    # creating conflict for docs on SG
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2,
                          property_updater=property_updater, auth=session)

    # creating conflict for docs on CBL
    doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            data["cbl_random"] = random_string(length=10, printable=True)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type=replicator_type, conflict_resolver="local_wins")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    # printing doc content before replication conflicted docs
    sg_docs_content = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    if replicator_type == "pull":
        for sg_doc in sg_docs_content:
            doc_id = sg_doc["_id"]
            cbl_doc = cbl_docs[doc_id]
            assert sg_doc["sg_new_update1"] != cbl_doc["sg_new_update1"], "CCR failed to resolve conflict " \
                                                                          "with local win"
            assert sg_doc["sg_new_update2"] != cbl_doc["sg_new_update2"], "CCR failed to resolve conflict " \
                                                                          "with local win"
            assert sg_doc["sg_new_update3"] != cbl_doc["sg_new_update3"], "CCR failed to resolve conflict " \
                                                                          "with local win"
            assert "random" not in cbl_doc, "CCR failed to resolve conflict with local win"
            assert "cbl_random" not in sg_doc, "CCR failed to resolve conflict with local win"
    elif replicator_type == "push_pull":
        for sg_doc in sg_docs_content:
            doc_id = sg_doc["_id"]
            cbl_doc = cbl_docs[doc_id]
            assert sg_doc["sg_new_update1"] == cbl_doc["sg_new_update1"], "CCR failed to resolve conflict " \
                                                                          "with local win"
            assert sg_doc["sg_new_update2"] == cbl_doc["sg_new_update2"], "CCR failed to resolve conflict " \
                                                                          "with local win"
            assert sg_doc["sg_new_update3"] == cbl_doc["sg_new_update3"], "CCR failed to resolve conflict " \
                                                                          "with local win"
            assert "random" not in sg_doc, "CCR failed to resolve conflict with local win"
            assert "cbl_random" in sg_doc, "CCR failed to resolve conflict with local win"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
@pytest.mark.parametrize("replicator_type", [
    "pull",
    "push_pull"
])
def test_remote_wins_custom_conflicts(params_from_base_test_setup, replicator_type):
    """
    @summary: resolve conflicts as per local doc
    1. Create few docs in app and get them replicated to SG. Stop the replication once docs are replicated.
    2. Update docs couple of times with different updates on both SG and CBL app. This will create conflict.
    3. Start the replication with remote_win CCR algorithm
    4. Verifies that CBL has synced SG changes. For push and pull replication SG changes would override changes of CBL
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "remote_win_conflicts", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG url: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]

    # creating conflict for docs on SG
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2,
                          property_updater=property_updater, auth=session)

    # creating conflict for docs on CBL
    doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type=replicator_type, conflict_resolver="remote_wins")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    # printing doc content before replication conflicted docs
    sg_docs_content = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for sg_doc in sg_docs_content:
        doc_id = sg_doc["_id"]
        cbl_doc = cbl_docs[doc_id]
        assert sg_doc["sg_new_update1"] == cbl_doc["sg_new_update1"], "CCR failed to resolve conflict with remote win"
        assert sg_doc["sg_new_update2"] == cbl_doc["sg_new_update2"], "CCR failed to resolve conflict with remote win"
        assert sg_doc["sg_new_update3"] == cbl_doc["sg_new_update3"], "CCR failed to resolve conflict with remote win"
        assert sg_doc["random"] == cbl_doc["random"], "CCR failed to resolve conflict with remote win"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
@pytest.mark.parametrize("replicator_type", [
    "pull",
    "push_pull"
])
def test_null_wins_custom_conflicts(params_from_base_test_setup, replicator_type):
    """
    @summary: resolve conflicts as per local doc
    1. Create few docs in app and get them replicated to SG. Stop the replication once docs are replicated.
    2. Update docs couple of times with different updates on both SG and CBL app. This will create conflict.
    3. Start the replication with NULL CCR algorithm
    4. Verifies that docs have been deleted. For push and pull replication docs will be delted at SG too.
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "null_win_conflicts", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG url: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]

    # creating conflict for docs on SG
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2,
                          property_updater=property_updater, auth=session)

    # creating conflict for docs on CBL
    doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type=replicator_type, conflict_resolver="null")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    # printing doc content before replication conflicted docs
    try:
        sg_docs_content = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]
    except Exception as err:
        log_info("Error thrown when requested for Doc from SG:\n {}".format(err))
        sg_docs_content = []
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    cbl_doc_count = db.getCount(cbl_db)
    if replicator_type == "pull":
        assert len(sg_docs_content) == num_of_docs, "NULL CCR replicated changes to SG"
        assert len(cbl_docs) == 0, "NULL CCR failed to resolve conflict with docs delete"
        assert cbl_doc_count == 0, "NULL CCR failed to resolve conflict with docs delete"
    elif replicator_type == "push_pull":
        assert len(sg_docs_content) == 0, "NULL CCR failed to resolve conflict with docs delete"
        assert len(cbl_docs) == 0, "NULL CCR failed to resolve conflict with docs delete"
        assert cbl_doc_count == 0, "NULL CCR failed to resolve conflict with docs delete"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
@pytest.mark.parametrize("replicator_type", [
    "pull",
    "push_pull"
])
def test_merge_wins_custom_conflicts(params_from_base_test_setup, replicator_type):
    """
    @summary: resolve conflicts as per local doc
    1. Create few docs in app and get them replicated to SG. Stop the replication once docs are replicated.
    2. Update docs couple of times with different updates on both SG and CBL app. This will create conflict.
    3. Start the replication with merge_wins CCR algorithm
    4. Verifies that CBL has retains its changes and have added all new keys to local doc from remote doc. For push and
    pull replication SG changes should be override with that of CBL
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "merge_win_conflicts", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG url: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]

    # creating conflict for docs on SG
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2,
                          property_updater=property_updater, auth=session)

    # creating conflict for docs on CBL
    doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            data["cbl_random"] = random_string(length=10, printable=True)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type=replicator_type, conflict_resolver="merge")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    # printing doc content before replication conflicted docs
    sg_docs_content = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    if replicator_type == "pull":
        for sg_doc in sg_docs_content:
            doc_id = sg_doc["_id"]
            cbl_doc = cbl_docs[doc_id]
            assert sg_doc["sg_new_update1"] != cbl_doc["sg_new_update1"], "CCR failed to resolve conflict " \
                                                                          "with merge win"
            assert sg_doc["sg_new_update2"] != cbl_doc["sg_new_update2"], "CCR failed to resolve conflict " \
                                                                          "with merge win"
            assert sg_doc["sg_new_update3"] != cbl_doc["sg_new_update3"], "CCR failed to resolve conflict " \
                                                                          "with merge win"
            assert sg_doc["random"] == cbl_doc["random"], "CCR failed to resolve conflict with merge win"
            assert "cbl_random" not in sg_doc, "CCR failed to resolve conflict with merge win. SG doc got " \
                                               "updated with CBL changes"
    elif replicator_type == "push_pull":
        for sg_doc in sg_docs_content:
            doc_id = sg_doc["_id"]
            cbl_doc = cbl_docs[doc_id]
            assert sg_doc["sg_new_update1"] == cbl_doc["sg_new_update1"], "CCR failed to resolve conflict " \
                                                                          "with merge win"
            assert sg_doc["sg_new_update2"] == cbl_doc["sg_new_update2"], "CCR failed to resolve conflict " \
                                                                          "with merge win"
            assert sg_doc["sg_new_update3"] == cbl_doc["sg_new_update3"], "CCR failed to resolve conflict " \
                                                                          "with merge win"
            assert sg_doc["random"] == cbl_doc["random"], "CCR failed to resolve conflict with merge win"
            assert "cbl_random" in sg_doc, "CCR failed to resolve conflict with merge win"


@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
@pytest.mark.parametrize("replicator_type", [
    "pull",
    "push_pull"
])
def test_incorrect_doc_id_custom_conflicts_resolution(params_from_base_test_setup, replicator_type):
    """
    @summary: resolve conflicts as per modified doc
    1. Create few docs in app and get them replicated to SG. Stop the replication once docs are replicated.
    2. Update docs couple of times with different updates on both SG and CBL app. This will create conflict.
    3. Start the replication with incorrect_doc_id CCR algorithm
    4. Verifies that CBL has docs with doc id corrected and have an additional field called new_value with value as
    couchbae. For push and pull replication SG changes should be override with that of CBL
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "incorrect_doc_id_conflicts", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG url: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]

    # creating conflict for docs on SG
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2,
                          property_updater=property_updater, auth=session)

    # creating conflict for docs on CBL
    doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            data["cbl_random"] = random_string(length=10, printable=True)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type=replicator_type, conflict_resolver="incorrect_doc_id")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    # printing doc content before replication conflicted docs
    try:
        sg_docs_content = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]
    except Exception as err:
        log_info("Error thrown when requested for Doc from SG:\n {}".format(err))
        sg_docs_content = []
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    cbl_doc_ids = db.getDocIds(cbl_db)
    if replicator_type == "pull":
        assert sorted(doc_ids) == sorted(cbl_doc_ids), "CCR failed to correct incorrect-doc-ids"
        for sg_doc in sg_docs_content:
            doc_id = sg_doc["_id"]
            cbl_doc = cbl_docs[doc_id]
            assert cbl_doc["new_value"] == "couchbase", "CCR failed to resolve conflict with doc with additional key"
    if replicator_type == "push_pull":
        for sg_doc in sg_docs_content:
            doc_id = sg_doc["_id"]
            cbl_doc = cbl_docs[doc_id]
            assert cbl_doc["new_value"] == "couchbase", "CCR failed to resolve conflict with doc with additional key"
            assert "new_value" in sg_doc, "CCR failed to resolve conflict with doc with additional key"


@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
@pytest.mark.parametrize("replicator_type", [
    "pull",
    "push_pull"
])
def test_non_blocking_custom_conflicts_resolution(params_from_base_test_setup, replicator_type):
    """
    @summary: resolve conflicts as per local doc
    1. Create few docs in app and get them replicated to SG. Stop the replication once docs are replicated.
    2. Update docs couple of times with different updates on both SG and CBL app. This will create conflict.
    3. Start the replication with delayed_local_win CCR algorithm which takes time to resolve conflicts. Meanwhile
    update docs on CBL and verify that updates are successful and conflict also resolves
    4. Verifies that CBL has docs with local win body. For push and pull replication SG changes should be override with
    that of CBL
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "delayed_local_conflicts", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG url: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]

    # creating conflict for docs on SG
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2,
                          property_updater=property_updater, auth=session)

    # creating conflict for docs on CBL
    doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            data["cbl_random"] = random_string(length=10, printable=True)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type=replicator_type,
                                       conflict_resolver="delayed_local_win")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    # updating doc at CBL couple of times
    new_docs_body = {}
    log_info("Updating CBL docs during conflict resolution")
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            new_docs_body[doc_id] = [data]
            data = property_updater(data)
            random_value = random_string(length=10, printable=True)
            data["update_during_CCR"] = random_value
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

            # Saving the history of update to CBL doc
            new_docs_body[doc_id].append(data)

    replicator.wait_until_replicator_idle(repl, sleep_time=12)  # Added sleep time because CCR sleeps for 10 secs
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    sg_docs_content = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]
    cbl_docs = db.getDocuments(cbl_db, doc_ids)

    if replicator_type == "pull":
        for sg_doc in sg_docs_content:
            doc_id = sg_doc["_id"]
            cbl_doc = cbl_docs[doc_id]
            assert sg_doc["sg_new_update1"] != cbl_doc["sg_new_update1"], "CCR failed to resolve conflict " \
                                                                          "with delayed local win"
            assert sg_doc["sg_new_update2"] != cbl_doc["sg_new_update2"], "CCR failed to resolve conflict " \
                                                                          "with delayed local win"
            assert sg_doc["sg_new_update3"] != cbl_doc["sg_new_update3"], "CCR failed to resolve conflict " \
                                                                          "with delayed local win"
            assert "random" not in cbl_doc, "CCR failed to resolve conflict with delayed local win"
            assert "cbl_random" not in sg_doc, "CCR failed to resolve conflict with delayed local win"
            assert new_docs_body[doc_id][1]["update_during_CCR"] == cbl_doc["update_during_CCR"], "CCR failed to " \
                                                                                                  "resolve conflict " \
                                                                                                  "with delayed " \
                                                                                                  "local win"
    elif replicator_type == "push_pull":
        for sg_doc in sg_docs_content:
            doc_id = sg_doc["_id"]
            cbl_doc = cbl_docs[doc_id]
            assert sg_doc["sg_new_update1"] == cbl_doc["sg_new_update1"], "CCR failed to resolve conflict " \
                                                                          "with delayed local win"
            assert sg_doc["sg_new_update2"] == cbl_doc["sg_new_update2"], "CCR failed to resolve conflict " \
                                                                          "with delayed local win"
            assert sg_doc["sg_new_update3"] == cbl_doc["sg_new_update3"], "CCR failed to resolve conflict " \
                                                                          "with delayed local win"
            assert "random" not in sg_doc, "CCR failed to resolve conflict with delayed local win"
            assert "cbl_random" in sg_doc, "CCR failed to resolve conflict with delayed local win"
            assert cbl_doc["update_during_CCR"] == sg_doc["update_during_CCR"], "CCR failed to resolve " \
                                                                                "conflict with delayed" \
                                                                                " local win"


@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
def test_stop_replicator_before_ccr_completes(params_from_base_test_setup):
    """
    @summary: resolve conflicts as per local doc
    1. Create few docs in app and get them replicated to SG. Stop the replication once docs are replicated.
    2. Update docs couple of times with different updates on both SG and CBL app. This will create conflict.
    3. Start the replication with delayed_local CCR algorithm and after the sleep of of few seconds before
    ccr resolve conflicts, close replicator.
    4. Verifies that CBL has retains its changes. For push and pull replication SG changes should be override with
    that of CBL
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "stop_before_ccr", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG url: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]

    # creating conflict for docs on SG
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2,
                          property_updater=property_updater, auth=session)

    # creating conflict for docs on CBL
    doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            data["cbl_random"] = random_string(length=10, printable=True)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="pull", conflict_resolver="delayed_local_win")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    sleep(5)  # sleeping so that replicator is in Conflict resolver
    log_info("Stopping Replicator before CCR finishes - 10 sec delay for CCR")
    replicator.stop(repl, max_times=100)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "total is not equal to completed"

    # printing doc content before replication conflicted docs
    sg_docs_content = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for sg_doc in sg_docs_content:
        doc_id = sg_doc["_id"]
        cbl_doc = cbl_docs[doc_id]
        assert sg_doc["sg_new_update1"] != cbl_doc["sg_new_update1"], "Replication stopped before resolving" \
                                                                      " the conflict"
        assert sg_doc["sg_new_update2"] != cbl_doc["sg_new_update2"], "Replication stopped before resolving" \
                                                                      " the conflict"
        assert sg_doc["sg_new_update3"] != cbl_doc["sg_new_update3"], "Replication stopped before resolving" \
                                                                      " the conflict"
        assert "random" not in cbl_doc, "Replication stopped before resolving the conflict"
        assert "cbl_random" not in sg_doc, "Replication stopped before resolving the conflict"


@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
@pytest.mark.parametrize("replicator_type", [
    "pull",
    "push_pull"
])
def test_delete_not_wins_custom_conflicts(params_from_base_test_setup, replicator_type):
    """
    @summary: resolve conflicts as per local doc
    1. Create few docs in app and get them replicated to SG. Stop the replication once docs are replicated.
    2. Update docs couple of times with different updates on one side and delete on other side.
    This will create conflict.
    3. Start the replication with delete_not_wins CCR algorithm
    4. Verifies that CBL has retains its changes. For push and pull replication SG changes should be override with
    that of CBL
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "local_win_conflicts", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG url: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]

    # creating conflict for docs on SG
    sg_client.delete_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    # creating conflict for docs on CBL
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            data["cbl_random"] = random_string(length=10, printable=True)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type=replicator_type, conflict_resolver="delete_not_win")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    # printing doc content before replication conflicted docs
    try:
        sg_docs_content = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]
    except Exception as err:
        log_info("Requesting for deleted docs from SG: {}".format(err))
        sg_docs_content = []
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    if replicator_type == "pull":
        assert sg_docs_content == [], "CCR failed to resolved conflict with delete_not_win and replicated content to SG"
        assert cbl_docs, "CCR failed to resolved conflict with delete_not_win"
    elif replicator_type == "push_pull":
        for sg_doc in sg_docs_content:
            doc_id = sg_doc["_id"]
            cbl_doc = cbl_docs[doc_id]
            assert sg_doc["sg_new_update1"] == cbl_doc["sg_new_update1"], "CCR failed to resolve conflict " \
                                                                          "with delete_not_win"
            assert sg_doc["sg_new_update2"] == cbl_doc["sg_new_update2"], "CCR failed to resolve conflict " \
                                                                          "with delete_not_win"
            assert sg_doc["sg_new_update3"] == cbl_doc["sg_new_update3"], "CCR failed to resolve conflict " \
                                                                          "with delete_not_win"
            assert "random" not in sg_doc, "CCR failed to resolve conflict with delete_not_win"
            assert "cbl_random" in sg_doc, "CCR failed to resolve conflict with delete_not_win"


@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
@pytest.mark.parametrize("replicator_type", [
    "pull",
    "push_pull"
])
def test_exception_thrown_custom_conflicts(params_from_base_test_setup, replicator_type):
    """
    @summary: resolve conflicts as per local doc
    1. Create few docs in app and get them replicated to SG. Stop the replication once docs are replicated.
    2. Update docs couple of times with different updates on one side and delete on other side.
    This will create conflict.
    3. Start the replication with delete_not_wins CCR algorithm
    4. Verifies that CBL has retains its changes. For push and pull replication SG changes should be override with
    that of CBL
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')
    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "exception_thrown", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG url: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]

    # creating conflict for docs on SG
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2,
                          property_updater=property_updater, auth=session)

    # creating conflict for docs on CBL
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            data["cbl_random"] = random_string(length=10, printable=True)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type=replicator_type, conflict_resolver="exception_thrown")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    # printing doc content before replication conflicted docs
    try:
        sg_docs_content = sg_client.get_bulk_docs(sg_url, sg_db, doc_ids, session)[0]
    except Exception as err:
        log_info("Requesting for deleted docs from SG: {}".format(err))
        sg_docs_content = []
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for sg_doc in sg_docs_content:
        doc_id = sg_doc["_id"]
        cbl_doc = cbl_docs[doc_id]
        assert sg_doc["sg_new_update1"] != cbl_doc["sg_new_update1"], "exception_thrown ccr didn't crash the app"
        assert sg_doc["sg_new_update2"] != cbl_doc["sg_new_update2"], "exception_thrown ccr didn't crash the app"
        assert sg_doc["sg_new_update3"] != cbl_doc["sg_new_update3"], "exception_thrown ccr didn't crash the app"
        assert "random" not in cbl_doc, "exception_thrown ccr didn't crash the app"
        assert "cbl_random" not in sg_doc, "exception_thrown ccr didn't crash the app"
