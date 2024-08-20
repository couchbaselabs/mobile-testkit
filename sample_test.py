import pytest
import time
import os
import random

from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
from keywords import couchbaseserver
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Document import Document
from CBLClient.Authenticator import Authenticator
from concurrent.futures import ThreadPoolExecutor
from libraries.testkit.prometheus import verify_stat_on_prometheus
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords import document, attachment
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from keywords.attachment import generate_2_png_100_100
from keywords.SyncGateway import SyncGateway
from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config
from keywords.constants import RBAC_FULL_ADMIN

def test():
    cluster_config = "path/to/cluster/config"
    sg_config = "path/to/sg/config"
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Initialize clients
    client = MobileRestClient()

    # Set up the database
    db_name = "test"
    base_url = "http://localhost:8080"
    sync_gateway_url = "http://localhost:4985/test"
    db = Database(base_url)

    db_config = db.configure(password=None)
    db_pointer = db.create(name=db_name, config=db_config)

    # Create a session with Sync Gateway
    cookie_name, session_id = client.create_session(sync_gateway_url, db_name, "sync_gateway", "password", ttl=86400, auth=None)
    authenticator = Authenticator(base_url=sync_gateway_url)
    auth_response = authenticator.sessionAuthenticator_create(session_id, cookie_name)

    # Configure replicator (pull)
    replicator = Replication(base_url)
    replicator_config = replicator.configure(source_db=db_pointer, replication_type="pull",
                                             target_url="ws://localhost:4984/test", replicator_authenticator=auth_response)
    replicator_pointer = replicator.create(config=replicator_config)

    # Start replication
    replicator.start(replicator=replicator_pointer)

    # Wait until replication completes
    while True:
        completed_docs = replicator.getCompleted(replicator_pointer)
        total_docs = replicator.getTotal(replicator_pointer)
        if completed_docs == total_docs:
            break
        time.sleep(1)

    replicator.stop(replicator=replicator_pointer)

    # Verify number of documents
    doc_count = db.getCount(db_pointer)
    assert doc_count == 4, f"Expected 4 documents, but got {doc_count}"

    # Create a document
    doc = Document(base_url)
    doc_id = "333"
    doc_pointer = doc.create(doc_id=doc_id)

    # Save the document in the database
    db.saveDocument(database=db_pointer, document=doc_pointer)

    # Verify the document is saved
    doc_count = db.getCount(db_pointer)
    assert doc_count == 5, f"Expected 5 documents, but got {doc_count}"

    # Configure replicator (push)
    replicator_config_push = replicator.configure(source_db=db_pointer, replication_type="push",
                                                  target_url="ws://localhost:4984/test", replicator_authenticator=authenticator)
    replicator_pointer_push = replicator.create(config=replicator_config_push)

    # Start push replication
    replicator.start(replicator=replicator_pointer_push)

    # Wait until replication completes
    while True:
        completed_docs = replicator.getCompleted(replicator_pointer_push)
        total_docs = replicator.getTotal(replicator_pointer_push)
        if completed_docs == total_docs:
            break
        time.sleep(1)

    replicator.stop(replicator=replicator_pointer_push)

    # Verify document reached Sync Gateway
    response = client.get_doc(url="http://localhost:4985", db="test", doc_id="333", auth=None, rev=None, revs_info=False, scope=None, collection=None)
    assert response["_id"] == "333", "Test failed, document did not reach Sync Gateway."

    log_info("Test passed! Document successfully replicated to Sync Gateway.")