import pytest
import time
import os

from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
from keywords import couchbaseserver
from keywords.utils import log_info
from keywords.utils import random_string
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
    db.deleteDB(cbl_db)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs, replication_type", [
#     (1, "pull"),
#     (10, "pull"),
    (1, "push"),
#     (10, "push"),
])
def test_delta_sync_replication_one_shot(params_from_base_test_setup, num_of_docs, replication_type):
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

#     if sync_gateway_version < "2.5.0":
#         pytest.skip('This test cannnot run with sg version below 2.5')
    channels = ["ABC"]
    username = "autotest"
    password = "password"
    number_of_updates = 2

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

    if replication_type == "push":
        doc_ids = db.getDocIds(cbl_db)
        cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
        for doc_id, doc_body  in cbl_db_docs.items():
            doc_body["new_field_1"] = random_string(length=30)
            doc_body["new_field_2"] = random_string(length=60)
            doc_body["new_field_3"] = random_string(length=90)
            db.updateDocument(database=cbl_db, data=doc_body, doc_id=doc_id)
    else:
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs["rows"], number_updates=number_of_updates, auth=session)

    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header,
                                       replication_type=replication_type)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "total is not equal to completed"
    replicator.stop(repl)

    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]
    for sg_doc, cbl_doc in zip(sg_docs, cbl_db_docs):
        cbl_doc_data = cbl_db_docs[cbl_doc]
        sg_doc_data = sg_doc["doc"]
        sg_doc_data.pop("_rev")
        assert compare_dict(sg_doc_data, cbl_doc_data) == []


def compare_dict(dict1, dict2):
    missing_keys = []
    for key in dict1:
        if key in dict2:
            assert dict1[key] == dict2[key]
        else:
            missing_keys.append(key)
    return missing_keys