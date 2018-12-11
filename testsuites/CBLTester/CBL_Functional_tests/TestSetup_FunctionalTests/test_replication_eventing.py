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
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    10,
#     100,
#     1000,
#     10000,
])
def test_replication_eventing_status(params_from_base_test_setup, num_of_docs):
    """
    @summary: 
    1. Create docs in CBL, Create docs in SGW
    2. Add listener for replicator.
    3. Replicate docs push/pull to SGW in one thread
    4. Get the status of replicator from listener  in another 
    thread
    5. Verify that replication status of docID shows 'in progress'
    Verify listerner changes 
    6. Wait until replication completes
    7. Verify the replicator status from listener
    8. Verify status shows 'completed'
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

    # Create CBL database
    sg_client = MobileRestClient()

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1.1 Creating Docs in CBL
    db.create_bulk_docs(num_of_docs, "push_cbl_docs", db=cbl_db, channels=channels)

    # 1.2 Creating Docs in SG
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    auth_session = cookie, session
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}

    sg_added_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=num_of_docs, id_prefix="pull_sg_docs", channels=channels, auth=auth_session)

    # 2 Adding Listener for replicator
    replicator = Replication(base_url)
    repl_config = replicator.configure(db=cbl_db, target_url=sg_blip_url,
                                            continuous=True, headers=session_header)
    repl = replicator.create(repl_config)
    repl_change_listener = replicator.addDocumentReplicationChangeListener(repl)

    replicator.start(repl)
    changes = replicator.getChangeDocumentReplicatorChangeListener(repl_change_listener)

    with ThreadPoolExecutor(max_workers=4) as tpe:
        replication_start_task = tpe.submit(replicator.start,
                                            replicator=repl)
        replication_status_task = tpe.submit(replicator.getChangesCount,
                                             change_listener=repl_change_listener)