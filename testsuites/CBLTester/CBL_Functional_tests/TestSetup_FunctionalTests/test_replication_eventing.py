import pytest
import time
import os
import random
import re

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
    100,
    1000,
    10000,
])
def test_replication_eventing_status(params_from_base_test_setup, num_of_docs):
    """
    @summary: 
    1. Create docs in CBL, Create docs in SGW
    2. Add listener for replicator.
    3. Replicate docs push/pull to SGW
    4. Get the events of replicator from listener
    5. Verify the event matches with the expected outcome
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
    cbl_docs = db.create_bulk_docs(num_of_docs, "push_cbl_docs", db=cbl_db, channels=channels)

    # 1.2 Creating Docs in SG
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    auth_session = cookie, session
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}

    sg_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=num_of_docs, id_prefix="pull_sg_docs", channels=channels, auth=auth_session)
    sg_docs = [doc["id"] for doc in sg_docs]

    # 2 Adding Listener for replicator
    replicator = Replication(base_url)
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header)
    repl = replicator.create(repl_config)
    repl_change_listener = replicator.addReplicatorEventChangeListener(repl)

    # 3. Starting Replication and waiting for it finish
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    # 4. Getting changes from the replication event listener
    doc_repl_event_changes = replicator.getReplicatorEventChanges(repl_change_listener).strip('[]')
    doc_repl_event_count = replicator.getReplicatorEventChangesCount(repl_change_listener)
    replicator.removeReplicatorEventListener(repl, repl_change_listener)
    replicator.stop(repl)

    # Processing received events
    replicated_event_changes = _get_event_changes(doc_repl_event_changes)
    push_docs = []
    pull_docs = []
    log_info("Replication Event Changes: {}".format(replicated_event_changes))
    for doc in replicated_event_changes:
        if replicated_event_changes[doc]['push'] == True:
            push_docs.append(doc)
        else:
            pull_docs.append(doc)

    # 5. Validating the event counts and verifying the push and pull event against doc_ids
    assert doc_repl_event_count == len(cbl_docs) + len(sg_docs), "replication event count is not matching with expected doc count"
    assert sorted(push_docs) == sorted(cbl_docs), "Replication event push docs are not equal to expected no. of docs to be pushed"
    assert sorted(pull_docs) == sorted(sg_docs), "Replication event pull docs are not equal to expected no. of docs to be pulled"


def _get_event_changes(event_changes):
    """
    @summary:
    A method to filter out the events.
    @return: 
    a dict containing doc_id as key and error status and replication as value,
    for a particular Replication event
    """
    event_dict = {}
    pattern = 'CouchbaseLiteSwift.DocumentReplication\((replicator: .*?), (isPush: .*?), (documentID: .*?), (error: .*?)\)'
    events = re.findall(pattern, string=event_changes)
    for event in events:
        is_push = True if event[1].split(' ')[1] == "true" else False
        doc_id = event[2].split(' ')[1].strip('""')
        error = event[3].split(' ')[1]
        event_dict[doc_id] = {"push": is_push, "error": error}
    return event_dict
