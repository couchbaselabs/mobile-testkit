import time

import pytest
import random

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import add_new_fields_to_doc
from CBLClient.Replication import Replication
from libraries.testkit import cluster
from keywords.constants import RBAC_FULL_ADMIN


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    pytest.param(10, marks=pytest.mark.ce_sanity),
    pytest.param(100, marks=pytest.mark.sanity),
    1000
])
def test_replication_push_filtering(params_from_base_test_setup, num_of_docs):
    """
        @summary:
        1. Create few docs at CBL.
        2. Replicate using push and pull and verify that all docs are replicated.
        3. Add new fields to docs and add boolean filter, which allow docs to replicate only if "new_field_1" is set to
        true.
        4. Verify SG has new fields added only when "new_field_1" is true
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
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Creating docs in CBL app
    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels, auth=auth)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username, auth=auth)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # 2. Replicating docs to SG
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

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    # 3. Modify docs in CBL so that we can do push replication. The replication will have filter for newly added field
    # Docs with new_field_1 value to true will only be replicated, others will be rejected by filter method
    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
    updates_in_doc = {}
    for doc_id, doc_body in list(cbl_db_docs.items()):
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

    # 4. Verify SG has new fields added only when "new_field_1" is true
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]
    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
    filtered_doc_ids = []
    for doc_id in cbl_db_docs:
        doc_body = cbl_db_docs[doc_id]
        if doc_body["new_field_1"] is True:
            filtered_doc_ids.append(doc_id)
    for item in sg_docs:
        sg_doc = item["doc"]
        doc_id = sg_doc["uni_key_id"]
        if doc_id in filtered_doc_ids:
            cbl_doc = cbl_db_docs[doc_id]
            assert cbl_doc["new_field_1"] == sg_doc["new_field_1"], "new_field_1 data is not matching"
            assert cbl_doc["new_field_2"] == sg_doc["new_field_2"], "new_field_2 data is not matching"
            assert cbl_doc["new_field_3"] == sg_doc["new_field_3"], "new_field_3 data is not matching"
        else:
            assert "new_field_1" not in list(sg_doc.keys()) or "new_field_2" not in list(sg_doc.keys()) or\
                   "new_field_3" not in list(sg_doc.keys()), "updated key found in doc. Push filter is not working"


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
        1. Create few docs at CBL.
        2. Replicate using push and pull and verify that all docs are replicated.
        3. Add new fields to docs and add boolean filter, which allow docs to replicate only if "new_field_1" is set to
        true.
        4. Verify SG has new fields added only when "new_field_1" is true
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
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannnot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Creating docs in CBL app
    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels, auth=auth)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username, auth=auth)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    auth_session = cookie, session
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # 2. Replicating docs to SG
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

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    # 3. Modify docs in SG so that we can do pull replication. The replication will have filter for newly added field
    # Docs with new_field_1 value to true will only be replicated, others will be rejected by filter method
    for item in sg_docs:
        sg_doc = item["doc"]
        sg_client.update_doc(url=sg_url, db=sg_db, doc_id=sg_doc["uni_key_id"],
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

    # 4. Verify CBL has new fields added only when "new_field_1" is true
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]
    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
    filtered_doc_ids = []
    for item in sg_docs:
        sg_doc = item["doc"]
        if sg_doc["new_field_1"] is True:
            filtered_doc_ids.append(sg_doc["uni_key_id"])
    for doc_id in cbl_db_docs:
        cbl_doc = cbl_db_docs[doc_id]
        if doc_id in filtered_doc_ids:
            assert cbl_doc["new_field_1"] is True,\
                "Replication didn't update the doc properly. Doc after replication finish {}".format(cbl_doc)
        else:
            assert "new_field_1" not in list(cbl_doc.keys()) or "new_field_2" not in list(cbl_doc.keys()) or\
                   "new_field_3" not in list(cbl_doc.keys()), "updated key found in doc. Pull filter is not working"


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
        1. Create few docs at CBL.
        2. Replicate using push and pull and verify that all docs are replicated.
        3. Delete few docs in both SG and CBL and replicate using delete callback for both push and pull filter.
        4. Verify that docs deleted in SG are still available in CBL and vice versa, as deleted filter would have
        rejected those changes
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
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    num_of_docs_to_delete = (num_of_docs * 2) // 10

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Creating docs in CBL app
    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels, auth=auth)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username, auth=auth)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    auth_session = cookie, session
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # 2. Replicating docs to SG
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

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    doc_ids = db.getDocIds(cbl_db)

    # 3. Delete few docs in both SG and CBL and replicate using delete callback for both push and pull filter.
    docs_to_delete = random.sample(doc_ids, num_of_docs_to_delete)
    sg_docs_to_delete = [sg_doc["doc"] for sg_doc in sg_docs if sg_doc["id"] in docs_to_delete[:len(docs_to_delete) // 2]]
    sg_docs_to_delete_ids = [doc["uni_key_id"] for doc in sg_docs_to_delete]
    cbl_docs_to_delete_ids = [sg_doc["id"] for sg_doc in sg_docs if sg_doc["id"] in docs_to_delete[len(docs_to_delete) // 2:]]
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

    # 4. Verify that docs deleted in SG are still available in CBL and vice versa, as deleted filter would have
    # rejected those changes
    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]
    sg_doc_ids = [sg_doc["id"] for sg_doc in sg_docs]
    for doc_id in sg_docs_to_delete_ids:
        assert doc_id in cbl_doc_ids, "SG deleted docs got replicated to CBL"
    for doc_id in cbl_docs_to_delete_ids:
        assert doc_id in sg_doc_ids, "CBL deleted docs got replicated to CBL"


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
        1. Create few docs at CBL.
        2. Replicate using push and pull and verify that all docs are replicated.
        3. Set channels for few docs to [] and replicate using access revoke callback
        4. Verify that docs with channel [] in SG are still available in CBL with their original channel value, as
        access revoke filter would have rejected those changes
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
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    num_of_docs_to_delete = (num_of_docs * 2) // 10

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannnot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Create few docs at CBL.
    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels, auth=auth)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username, auth=auth)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    auth_session = cookie, session
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels)

    # 2. Replicating docs to SG
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

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]

    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    # 3. Set channels for few docs to [] and replicate using access revoke callback
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

    # 4. Verify that docs with channel [] in SG are still available in CBL with their original channel value, as
    # access revoke filter would have rejected those changes
    for doc_id in cbl_doc_ids:
        if doc_id in docs_to_update:
            assert cbl_docs[doc_id]["channels"] == channels, "Replication filter was not able to filtered access revoke"
            assert "new_field_1" not in cbl_docs[doc_id] and "new_field_2" not in cbl_docs[doc_id] and\
                   "new_field_3" not in cbl_docs[doc_id]
        else:
            assert "new_field_1" in cbl_docs[doc_id] and "new_field_2" in cbl_docs[doc_id] and\
                   "new_field_3" in cbl_docs[doc_id]


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    10,
    100,
    1000
])
def test_filter_retrieval_with_replication_restart(params_from_base_test_setup, num_of_docs):
    """
        @summary:
        1. Create few docs at CBL and SG.
        2. Replicate using push and pull and verify that all docs are replicated.
        3. Update docs to have new fields at both SG and CBL and restart replication with the old config, so that it
        still has same filter callbacks.
        4. Verify that the filter is still applicable and only allowing replication for "new_field_1" true values
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
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Create few docs at CBL and SG.
    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels, auth=auth)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username, auth=auth)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    auth_session = cookie, session
    db.create_bulk_docs(num_of_docs, "cbl_docs", db=cbl_db, channels=channels)
    sg_client.add_docs(url=sg_url, db=sg_db, number=num_of_docs, id_prefix="sg_docs",
                       channels=channels, auth=auth_session)

    # 2. Replicate using push and pull with push and pull filter to boolean
    # Configure replication with push/pull
    replicator = Replication(base_url)
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       push_filter=True,
                                       pull_filter=True,
                                       filter_callback_func="boolean",
                                       headers=session_header)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "total is not equal to completed"
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]

    # Verify that all docs are replicated.
    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == 2 * num_of_docs, "Expected number of docs does not exist in sync-gateway after replication"
    assert cbl_doc_count == 2 * num_of_docs, "Expected number of docs does not exist in CBL app after replication"

    # 3. Update docs to have new fields at both SG and CBL and restart replication with the old config, so that it
    # still has same filter callbacks.
    doc_ids = db.getDocIds(cbl_db)
    docs = db.getDocuments(cbl_db, doc_ids)
    updates_in_doc = {}
    for doc_id, doc_body in list(docs.items()):
        if "cbl_doc" in doc_id:
            doc_body = add_new_fields_to_doc(doc_body)
            db.updateDocument(database=cbl_db, data=doc_body, doc_id=doc_id)
        else:
            sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id,
                                 auth=auth_session, property_updater=add_new_fields_to_doc)
            doc_body = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=auth_session)
        updates_in_doc[doc_id] = {
            "new_field_1": doc_body["new_field_1"],
            "new_field_2": doc_body["new_field_2"],
            "new_field_3": doc_body["new_field_3"],
        }

    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    time.sleep(2)
    replicator.stop(repl)

    # 4. Verifying that the filter is still applicable and only allowing replication for "new_field_1" true values
    doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]

    # checking only those SG docs got pulled which has "new_field_1" set to true
    for doc_id in cbl_docs:
        if "sg_doc" in doc_id:
            if updates_in_doc[doc_id]["new_field_1"] is False:
                assert "new_field_1" not in cbl_docs[doc_id] and "new_field_2" not in cbl_docs[doc_id] and\
                       "new_field_3" not in cbl_docs[doc_id]
            else:
                assert cbl_docs[doc_id]["new_field_1"] is True

    # checking only those CB docs got pushed which has "new_field_1" set to true
    for sg_doc in sg_docs:
        doc_id = sg_doc["id"]
        if "cbl_docs" in doc_id:
            doc_body = sg_doc["doc"]
            if updates_in_doc[doc_id]["new_field_1"] is False:
                assert "new_field_1" not in doc_body and "new_field_2" not in doc_body and "new_field_3" not in doc_body
            else:
                assert doc_body["new_field_1"] is True
