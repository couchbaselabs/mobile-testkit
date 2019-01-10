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
from requests.exceptions import HTTPError

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
])
def test_replication_eventing_status(params_from_base_test_setup, num_of_docs):
    """
    @summary: 
    1. Create docs in CBL, Create docs in SGW
    2. Add Document Replication Change listener for replicator.
    3. Replicate docs push/pull to SGW through one shot replication
    4. Get the events of replicator from listener
    5. Verify the event matches with the expected outcome. 
       i. Assert the total event count should be equal to no. of docs replicated
       ii. Assert no. push event are equal to pushed docs
       iii. Assert no. push event are equal to pushed docs
       iv. Assert there is no error in events
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
    doc_repl_event_changes = replicator.getReplicatorEventChanges(repl_change_listener)
    replicator.removeReplicatorEventListener(repl, repl_change_listener)
    replicator.stop(repl)

    # Processing received events
    replicated_event_changes = _get_event_changes(doc_repl_event_changes)
    push_docs = []
    pull_docs = []
    error_docs = []
    for doc in replicated_event_changes:
        if replicated_event_changes[doc]['push'] == True:
            push_docs.append(doc)
        else:
            pull_docs.append(doc)
        if replicated_event_changes[doc]['error_code'] != None:
            error_docs.append({doc: "{}, {}".format(replicated_event_changes[doc]['error_code'],
                                                    replicated_event_changes[doc]['error_domain'])})

    # 5. Validating the event counts and verifying the push and pull event against doc_ids
    assert sorted(push_docs) == sorted(cbl_docs), "Replication event push docs are not equal to expected no. of docs to be pushed"
    assert sorted(pull_docs) == sorted(sg_docs), "Replication event pull docs are not equal to expected no. of docs to be pulled"
    assert len(error_docs) == 0, "Error found in replication events {}".format(error_docs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs, conflict_direction", [
    [10, "push"],
    [10, "pull"],
    [1000, "push"],
    [1000, "pull"]
])
def test_replication_error_event(params_from_base_test_setup, num_of_docs,
                                 conflict_direction):
    '''
    @summary: 
    1. Create docs in CBL and replicate to SG using push one-shot replication
    2. Add update to SG and CBL to create conflict
    3. start push/pull one-shot replication and start replication event listener
    4. Check the error is thrown in replication event changes
    '''
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

    # 1. Creating Docs in CBL
    cbl_docs = db.create_bulk_docs(num_of_docs, "push_cbl_docs", db=cbl_db, channels=channels)

    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    auth_session = cookie, session
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}

    # Replicating docs to SG so that later we can create conflict
    # Adding Listener for replicator
    replicator = Replication(base_url)
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header,
                                       replication_type="push")
    repl = replicator.create(repl_config)
    repl_change_listener = replicator.addReplicatorEventChangeListener(repl)

    # 2. Starting Replication and waiting for it finish
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.removeReplicatorEventListener(repl, repl_change_listener)
    replicator.stop(repl)

    # 3. Adding conflicts for docs in SG
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auth_session)
    sg_docs = sg_docs["rows"]
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=auth_session)

    # Adding conflict for docs in CBL
    db.update_bulk_docs(database=cbl_db, number_of_updates=1,
                        doc_ids=cbl_docs)

    # 4. Starting one-shot replication again to create error based on conflict
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=False,
                                       headers=session_header,
                                       replication_type=conflict_direction)
    repl_conflict = replicator.create(repl_config)
    repl_error_change_listener = replicator.addReplicatorEventChangeListener(repl_conflict)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    doc_error_repl_event_changes = replicator.getReplicatorEventChanges(repl_error_change_listener).strip('[]')
    replicator.removeReplicatorEventListener(repl, repl_error_change_listener)
    replicator.stop(repl_conflict)
    log_info("Event changes: {}".format(doc_error_repl_event_changes))


def _get_event_changes(event_changes):
    """
    @summary:
    A method to filter out the events.
    @return: 
    a dict containing doc_id as key and error status and replication as value,
    for a particular Replication event
    """
    event_dict = {}
    pattern = ".*?doc_id: (\w+), error_code: (\w+), error_domain: (\w+), push: (\w+), flags: (.*?)'.*?"
    events = re.findall(pattern, string=str(event_changes))
    for event in events:
        doc_id = event[0].strip()
        error_code = event[1].strip()
        error_domain = event[2].strip()
        is_push = True if ("true" in event[3] or "True" in event[3]) else False
        flags = event[4] if event[4] != '[]' else None
        if error_code == '0' or error_code == 'nil':
            error_code = None
        if error_domain == '0' or error_domain == 'nil':
            error_domain = None
        event_dict[doc_id] = {"push": is_push, 
                              "error_code": error_code,
                              "error_domain": error_domain,
                              "flags": flags}
    return event_dict
