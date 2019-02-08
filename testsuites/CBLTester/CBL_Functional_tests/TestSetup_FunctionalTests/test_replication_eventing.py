import pytest
import random


from keywords.MobileRestClient import MobileRestClient
from keywords.utils import get_event_changes
from CBLClient.Replication import Replication
from libraries.testkit import cluster


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
    cbl_doc_ids = db.create_bulk_docs(num_of_docs, "push_cbl_docs", db=cbl_db, channels=channels)

    # 1.2 Creating Docs in SG
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    auth_session = cookie, session
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}

    sg_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=num_of_docs, id_prefix="pull_sg_docs", channels=channels,
                                 auth=auth_session)
    sg_doc_ids = [doc["id"] for doc in sg_docs]

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
    replicator.wait_until_replicator_idle(repl, max_times=5000)

    # 4. Getting changes from the replication event listener
    doc_repl_event_changes = replicator.getReplicatorEventChanges(repl_change_listener)
    replicator.removeReplicatorEventListener(repl, repl_change_listener)
    replicator.stop(repl)

    # Processing received events
    replicated_event_changes = get_event_changes(doc_repl_event_changes)
    push_docs = []
    pull_docs = []
    error_docs = []
    for doc in replicated_event_changes:
        if replicated_event_changes[doc]['push'] is True:
            push_docs.append(doc)
        else:
            pull_docs.append(doc)
        if replicated_event_changes[doc]['error_code'] is not None:
            error_docs.append({doc: "{}, {}".format(replicated_event_changes[doc]['error_code'],
                                                    replicated_event_changes[doc]['error_domain'])})

    # 5. Validating the event counts and verifying the push and pull event against doc_ids
    assert sorted(push_docs) == sorted(
        cbl_doc_ids), "Replication event push docs are not equal to expected no. of docs to be pushed"
    assert sorted(pull_docs) == sorted(
        sg_doc_ids), "Replication event pull docs are not equal to expected no. of docs to be pulled"
    assert len(error_docs) == 0, "Error found in replication events {}".format(error_docs)


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    10,
    1000,
])
def test_push_replication_error_event(params_from_base_test_setup, num_of_docs):
    """
    @summary:
    1. Create docs in CBL and replicate to SG using push one-shot replication
    2. Add update to SG and CBL to create conflict
    3. start push one-shot replication and start replication event listener
    4. Check the error is thrown in replication event changes
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

    # 1. Creating Docs in CBL
    cbl_docs = db.create_bulk_docs(num_of_docs, "cbl_docs", db=cbl_db, channels=channels)

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
    repl_conflict_config = replicator.configure(source_db=cbl_db,
                                                target_url=sg_blip_url,
                                                continuous=False,
                                                headers=session_header,
                                                replication_type="push")
    repl_conflict = replicator.create(repl_conflict_config)
    repl_error_change_listener = replicator.addReplicatorEventChangeListener(repl_conflict)
    replicator.start(repl_conflict)
    replicator.wait_until_replicator_idle(repl_conflict)

    # 5. verifying the error in the events collected
    doc_error_repl_event_changes = replicator.getReplicatorEventChanges(repl_error_change_listener)
    replicator.removeReplicatorEventListener(repl_conflict, repl_error_change_listener)
    replicator.stop(repl_conflict)
    event_dict = get_event_changes(doc_error_repl_event_changes)
    assert len(event_dict) != 0, "No Event captured. Check the logs for detailed info"
    for doc_id in event_dict:
        assert '10409' in event_dict[doc_id]["error_code"], "Conflict error didn't happen. Error Code: {}".format(
            event_dict[doc_id]["error_code"])


# @pytest.mark.sanity
# @pytest.mark.listener
# @pytest.mark.replication
# @pytest.mark.parametrize("num_of_docs", [
#     1000,
# ])
# def test_pull_replication_error_event(params_from_base_test_setup, num_of_docs):
#     """
#     @summary:
#     1. Create docs in SG and replicate to CB using pull one-shot replication
#     2. Add update to SG and CBL to create conflict
#     3. start push/pull one-shot replication and start replication event listener
#     4. Check the error is thrown in replication event changes
#     """
#     sg_db = "db"
#     sg_url = params_from_base_test_setup["sg_url"]
#     sg_admin_url = params_from_base_test_setup["sg_admin_url"]
#     cluster_config = params_from_base_test_setup["cluster_config"]
#     sg_blip_url = params_from_base_test_setup["target_url"]
#     base_url = params_from_base_test_setup["base_url"]
#     sg_config = params_from_base_test_setup["sg_config"]
#     db = params_from_base_test_setup["db"]
#     cbl_db = params_from_base_test_setup["source_db"]
#     sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
#
#     if sync_gateway_version < "2.5.0":
#         pytest.skip('This test cannnot run with sg version below 2.5')
#     channels = ["ABC"]
#     username = "autotest"
#     password = "password"
#
#     # Create CBL database
#     sg_client = MobileRestClient()
#
#     # Reset cluster to ensure no data in system
#     c = cluster.Cluster(config=cluster_config)
#     c.reset(sg_config_path=sg_config)
#
#     # 1. Creating Docs in SG
#
#     sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
#     cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
#     auth_session = cookie, session
#     sync_cookie = "{}={}".format(cookie, session)
#     session_header = {"Cookie": sync_cookie}
#     sg_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=num_of_docs, id_prefix="sg_docs", channels=channels,
#                                  auth=auth_session)
#     sg_doc_ids = [doc["id"] for doc in sg_docs]
#
#     # Replicating docs from SG
#     # Adding Listener for replicator
#     replicator = Replication(base_url)
#     repl_config = replicator.configure(source_db=cbl_db,
#                                        target_url=sg_blip_url,
#                                        continuous=False,
#                                        headers=session_header,
#                                        replication_type="pull")
#     repl_conflict = replicator.create(repl_config)
#     repl_error_change_listener = replicator.addReplicatorEventChangeListener(repl_conflict)
#
#     # 2. Starting Replication and disabling user during replication to create pull error
#     replicator.start(repl_conflict)
#     sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, disabled=True)
#     try:
#         replicator.wait_until_replicator_idle(repl_conflict)
#     except Exception, err:
#         log_info("Error occured during replication - {}".format(str(err)))
#
#     # 3. verifying the error in the events collected
#     doc_error_repl_event_changes = replicator.getReplicatorEventChanges(repl_error_change_listener)
#     replicator.removeReplicatorEventListener(repl_conflict, repl_error_change_listener)
#     replicator.stop(repl_conflict)
#     event_dict = get_event_changes(doc_error_repl_event_changes)
#     cbl_doc_ids = db.getDocIds(database=cbl_db)
#     cbl_docs = db.getDocuments(database=cbl_db, ids=cbl_doc_ids)
#     assert num_of_docs == len(cbl_docs)
#     assert num_of_docs == len(event_dict)


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    10,
    # 100,
])
def test_replication_access_revoke_event(params_from_base_test_setup, num_of_docs):
    """
    @summary:
    1. Creating Docs in CBL
    2. Starting one-shot Push Replication and waiting for it finish
    3. Changing channel of some docs, so that we get access revoked event
    4. Replicating access revoked and capturing events through listener
    5. Verifying the access revoke in event captures
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
    username = "autotest"
    password = "password"
    channels = ["ABC"]

    # Create CBL database
    sg_client = MobileRestClient()

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Creating Docs in CBL
    db.create_bulk_docs(num_of_docs, "cbl_docs", db=cbl_db, channels=channels)

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

    # 3 changing channel of some docs, so that we get access revoked event
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auth_session)["rows"]
    docs_to_modify = random.sample(sg_docs, (num_of_docs / 10) * 2)
    for sg_doc in docs_to_modify:
        sg_client.update_doc(url=sg_url, db=sg_db, doc_id=sg_doc["id"],
                             number_updates=1, auth=auth_session,
                             channels=["unknown"])

    # 4 Replicating access revoked
    repl_access_revoke_config = replicator.configure(source_db=cbl_db,
                                                     target_url=sg_blip_url,
                                                     continuous=False,
                                                     headers=session_header,
                                                     replication_type="pull")
    repl_access_revoke = replicator.create(repl_access_revoke_config)
    repl_access_revoke_change_listener = replicator.addReplicatorEventChangeListener(repl_access_revoke)
    replicator.start(repl_access_revoke)
    replicator.wait_until_replicator_idle(repl_access_revoke)

    # 5. Verifying the access revoke in event captures
    doc_revoke_access_event_changes = replicator.getReplicatorEventChanges(repl_access_revoke_change_listener)
    replicator.removeReplicatorEventListener(repl_access_revoke, repl_access_revoke_change_listener)
    replicator.stop(repl_access_revoke)
    event_dict = get_event_changes(doc_revoke_access_event_changes)
    replicator.removeReplicatorEventListener(repl_access_revoke, repl_access_revoke_change_listener)
    replicator.stop(repl_access_revoke)
    assert len(event_dict) != 0, "Replication listener didn't caught events. Check app logs for detailed info"
    for doc_id in event_dict:
        assert event_dict[doc_id]["flags"] == "2" or event_dict[doc_id]["flags"] == "[DocumentFlagsAccessRemoved]" or \
            event_dict[doc_id]["flags"] == "AccessRemoved", \
            'Access Revoked flag is not tagged for document. Flag value: {}'.format(event_dict[doc_id]["flags"])

    # Verifying if the docs, for which access has been revoked, are purged
    doc_ids = db.getDocIds(cbl_db)
    for sg_doc in docs_to_modify:
        assert sg_doc["id"] not in doc_ids, "Revoked access to channel didn't purge the docs from cbl db"


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [
    10,
    100,
])
def test_replication_delete_event(params_from_base_test_setup, num_of_docs):
    """
    @summary:
    1. Creating Docs in CBL
    2. Starting one-shot Push Replication and waiting for it finish
    3. Delete some docs on both SG and CBL and modify rest of docs
    4. Replicating with delete filter. Filter will prevent deleted document to replicate on other end
    5. Verifying the access revoke in event captures
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
    username = "autotest"
    password = "password"
    channels = ["ABC"]

    # Create CBL database
    sg_client = MobileRestClient()

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Creating Docs in CBL
    db.create_bulk_docs(num_of_docs, "cbl_docs", db=cbl_db, channels=channels)

    sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    auth_session = cookie, session
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}

    # Replicating docs to SG so that later we can create delete event
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

    # 3 deleting some docs, so that we get delete event
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auth_session)["rows"]
    docs_to_modify = random.sample(sg_docs, (num_of_docs / 10) * 2)
    for doc in docs_to_modify:
        doc_id = doc["id"]
        sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=doc_id, rev=doc["value"]["rev"], auth=auth_session)

    # 4 Replicating for deleted docs
    repl_delete_config = replicator.configure(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              headers=session_header,
                                              replication_type="pull")
    repl_delete = replicator.create(repl_delete_config)
    repl_delete_change_listener = replicator.addReplicatorEventChangeListener(repl_delete)
    replicator.start(repl_delete)
    replicator.wait_until_replicator_idle(repl_delete)

    # 5. Verifying the delete event in event captures
    doc_delete_event_changes = replicator.getReplicatorEventChanges(repl_delete_change_listener)
    replicator.removeReplicatorEventListener(repl_delete, repl_delete_change_listener)
    replicator.stop(repl_delete)
    event_dict = get_event_changes(doc_delete_event_changes)
    replicator.removeReplicatorEventListener(repl_delete, repl_delete_change_listener)
    replicator.stop(repl_delete)
    assert len(event_dict) != 0, "Replication listener didn't caught events. Check app logs for detailed info"
    for doc_id in event_dict:
        assert event_dict[doc_id]["flags"] == "1" or event_dict[doc_id]["flags"] == "[DocumentFlagsDeleted]" or \
            event_dict[doc_id]["flags"] == "Deleted", \
            'Deleted flag is not tagged for document. Flag value: {}'.format(event_dict[doc_id]["flags"])

    # Verifying if the docs, for which access has be revoked, are purged
    doc_ids = db.getDocIds(cbl_db)
    for sg_doc in docs_to_modify:
        assert sg_doc["id"] not in doc_ids, "channel access removal didn't purge the docs from cbl db"
