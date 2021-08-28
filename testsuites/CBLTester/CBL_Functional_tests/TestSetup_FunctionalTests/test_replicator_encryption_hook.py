import pytest
import time

from keywords.MobileRestClient import MobileRestClient
# from keywords.ClusterKeywords import ClusterKeywords
# from keywords import couchbaseserver
# from keywords.utils import log_info, random_string, get_embedded_asset_file_path
# from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Document import Document
# from CBLClient.Authenticator import Authenticator
# from concurrent.futures import ThreadPoolExecutor
# from CBLClient.Blob import Blob
# from CBLClient.Dictionary import Dictionary
# from libraries.testkit.prometheus import verify_stat_on_prometheus
# from keywords.SyncGateway import sync_gateway_config_path_for_mode
# from keywords import document, attachment
from libraries.testkit import cluster
# from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
# from keywords.attachment import generate_2_png_100_100
# from keywords.SyncGateway import SyncGateway


@pytest.mark.listener
@pytest.mark.parametrize("type", [
    ("push")
])
def test_replication_with_encryption(params_from_base_test_setup, type):
    """
    @summary:
    1. Have SG and CBL up and running
    2. Create a simple document with encryption property
    3. Start the replicator and make sure documents are
    replicated on SG

    7. Update the normal data
    8. Start the replicator and verify the docs on CBL

    10.Delete the document on CBL and replicate
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
    num_of_docs = 1
    number_of_updates = 2
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannot run with sg version below 2.0')
    channels_sg = ["ABC"]
    username = "autotest"
    password = "password"

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create docs in CBL
    channel = ["Replication-1"]
    db.create_bulk_docs(num_of_docs, "cbl", db=cbl_db, channels=channels_sg)
    doc_id = "doc_1"
    documentObj = Document(base_url)
    doc_body = document.create_doc(doc_id=doc_id, content="doc1", channels=channel, cbl=True, encrypted=True)
    doc1 = documentObj.create(doc_id, doc_body)
    db.saveDocument(cbl_db, doc1)

    # Configure replication with push/pull
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, channels_sg, sg_client, cbl_db, sg_blip_url,
        continuous=True, replication_type=type)

    # Update the doc in SG
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs["rows"], number_updates=number_of_updates, auth=session)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "total is not equal to completed"
    time.sleep(2)  # wait until replication is done
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
    sg_docs = sg_docs["rows"]

    # Verify database doc counts in CBL
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    # update docs in CBL
    db.update_bulk_docs(database=cbl_db, number_of_updates=number_of_updates)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    print(cbl_db_docs)
    for doc in cbl_doc_ids:
        assert cbl_db_docs[doc]["updates-cbl"] == number_of_updates, "updates-cbl did not get updated"

    # Delete all documents
    db.cbl_delete_bulk_docs(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    assert len(cbl_docs) == 0, "did not delete docs after delete operation"