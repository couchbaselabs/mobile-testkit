import pytest
import random

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import random_string
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
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
    db.deleteDB(cbl_db)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    10,
    100,
    1000
])
def test_replication_push_filtering(params_from_base_test_setup, num_of_docs):
    """
        @summary:
    """
    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannnot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # Configure replication with push/pull
    replicator = Replication(base_url)
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "total is not equal to completed"
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
    updates_in_doc = {}
    for doc_id, doc_body in cbl_db_docs.items():
        doc_body = add_new_fields_to_doc(doc_body)
        updates_in_doc[doc_id] = {
            "new_field_1": doc_body["new_field_1"],
            "new_field_2": doc_body["new_field_2"],
            "new_field_3": doc_body["new_field_3"],
            }
        db.updateDocument(database=cbl_db, data=doc_body, doc_id=doc_id)
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header,
                                       replication_type="push",
                                       push_filter=True,
                                       filter_callback_func="boolean")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "total is not equal to completed"
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]
    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
    filtered_doc_ids = []
    for doc_id in cbl_db_docs:
        doc_body = cbl_db_docs[doc_id]
        if doc_body["new_field_1"] is True:
            filtered_doc_ids.append(doc_id)
    for item in sg_docs:
        sg_doc = item["doc"]
        doc_id = sg_doc["_id"]
        if doc_id in filtered_doc_ids:
            cbl_doc = cbl_db_docs[doc_id]
            assert cbl_doc["new_field_1"] == sg_doc["new_field_1"], "new_field_1 data is not matching"
            assert cbl_doc["new_field_2"] == sg_doc["new_field_2"], "new_field_2 data is not matching"
            assert cbl_doc["new_field_3"] == sg_doc["new_field_3"], "new_field_3 data is not matching"
        else:
            assert "new_field_1" not in sg_doc.keys() or "new_field_2" not in sg_doc.keys() or\
                   "new_field_3" not in sg_doc.keys(), "updated key found in doc. Push filter is not working"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    10,
    100,
    1000
])
def test_replication_pull_filtering(params_from_base_test_setup, num_of_docs):
    """
        @summary:
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

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannnot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    auth_session = cookie, session
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # Configure replication with push/pull
    replicator = Replication(base_url)
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "total is not equal to completed"
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    for item in sg_docs:
        sg_doc = item["doc"]
        sg_client.update_doc(url=sg_url, db=sg_db, doc_id=sg_doc["_id"],
                             number_updates=1, auth=auth_session,
                             property_updater=add_new_fields_to_doc)
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header,
                                       replication_type="pull",
                                       pull_filter=True,
                                       filter_callback_func="boolean")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]
    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
    filtered_doc_ids = []
    for item in sg_docs:
        sg_doc = item["doc"]
        if sg_doc["new_field_1"] is True:
            filtered_doc_ids.append(sg_doc["_id"])
    for doc_id in cbl_db_docs:
        cbl_doc = cbl_db_docs[doc_id]
        if doc_id in filtered_doc_ids:
            assert cbl_doc["new_field_1"] is True,\
                "Replication didn't update the doc properly. Doc after replication finish {}".format(cbl_doc)
        else:
            assert "new_field_1" not in cbl_doc.keys() or "new_field_2" not in cbl_doc.keys() or\
                   "new_field_3" not in cbl_doc.keys(), "updated key found in doc. Pull filter is not working"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    10,
    100,
    1000
])
def test_replication_filter_deleted_document(params_from_base_test_setup, num_of_docs):
    """
        @summary:
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
    num_of_docs_to_delete = (num_of_docs * 2) / 10

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannnot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    auth_session = cookie, session
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # Configure replication with push/pull
    replicator = Replication(base_url)
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "total is not equal to completed"
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    doc_ids = db.getDocIds(cbl_db)

    docs_to_delete = random.sample(doc_ids, num_of_docs_to_delete)
    sg_docs_to_delete = [sg_doc["doc"] for sg_doc in sg_docs if sg_doc["id"] in docs_to_delete[:len(docs_to_delete) / 2]]
    sg_docs_to_delete_ids = [doc["_id"] for doc in sg_docs_to_delete]
    cbl_docs_to_delete_ids = [sg_doc["id"] for sg_doc in sg_docs if sg_doc["id"] in docs_to_delete[len(docs_to_delete) / 2:]]
    sg_client.delete_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_to_delete,
                               auth=auth_session)
    db.delete_bulk_docs(database=cbl_db, doc_ids=cbl_docs_to_delete_ids)

    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header,
                                       replication_type="push_pull",
                                       pull_filter=True,
                                       push_filter=True,
                                       filter_callback_func="deleted")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]
    sg_doc_ids = [sg_doc["id"] for sg_doc in sg_docs]
    for doc_id in sg_docs_to_delete_ids:
        assert doc_id in cbl_doc_ids, "SG deleted docs got replicated to CBL"
    for doc_id in cbl_docs_to_delete_ids:
        assert doc_id in sg_doc_ids, "CBL deleted docs got replicated to CBL"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    10,
    100,
    1000
])
def test_replication_filter_access_revoke_document(params_from_base_test_setup, num_of_docs):
    """
        @summary:
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
    num_of_docs_to_delete = (num_of_docs * 2) / 10

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannnot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    auth_session = cookie, session
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # Configure replication with push/pull
    replicator = Replication(base_url)
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "total is not equal to completed"
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    doc_ids = db.getDocIds(cbl_db)
    docs_to_update = random.sample(doc_ids, num_of_docs_to_delete)
    for doc_id in doc_ids:
        if doc_id in docs_to_update:
            sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=auth_session,
                                 channels=[], property_updater=add_new_fields_to_doc)
        else:
            sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=auth_session,
                                 property_updater=add_new_fields_to_doc)

    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header,
                                       replication_type="pull",
                                       pull_filter=True,
                                       filter_callback_func="access_revoked")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(database=cbl_db, ids=cbl_doc_ids)

    for doc_id in cbl_doc_ids:
        if doc_id in docs_to_update:
            assert cbl_docs[doc_id]["channels"] == channels, "Replication filter was not able to filtered access revoke"
            assert "new_field_1" not in cbl_docs[doc_id] and "new_field_2" not in cbl_docs[doc_id] and\
                   "new_field_3" not in cbl_docs[doc_id]
        else:
            assert "new_field_1" in cbl_docs[doc_id] and "new_field_2" in cbl_docs[doc_id] and\
                   "new_field_3" in cbl_docs[doc_id]


def add_new_fields_to_doc(doc_body):
    doc_body["new_field_1"] = random.choice([True, False])
    doc_body["new_field_2"] = random_string(length=60)
    doc_body["new_field_3"] = random_string(length=90)
    return doc_body
