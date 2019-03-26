import pytest
import random

from keywords import attachment
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer
from keywords.utils import get_event_changes


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endpoint_type", [
    (10, True, "push_pull", False, "URLEndPoint"),
    (10, False, "push_pull", False, "URLEndPoint"),
    (10, False, "push_pull", True, "URLEndPoint"),
    (100, False, "push_pull", False, "URLEndPoint"),
    (10, True, "push_pull", False, "MessageEndPoint"),
    (10, False, "push_pull", False, "MessageEndPoint"),
    (10, False, "push_pull", True, "MessageEndPoint"),
    (100, False, "push_pull", False, "MessageEndPoint"),

])
def test_peer_to_peer_replication_eventing_valid_values(params_from_base_test_setup, server_setup, num_of_docs,
                                                        continuous, replicator_type, attachments, endpoint_type):
    """
        @summary:
        1. Create docs on client and SG.
        2. Start the server.
        3. Add Listener to replicator and start replication from client.
        4. Verify replication is completed.
        5. Verify all docs got replicated on server.
        6. Verify event listener captures all replication event and there are no error in captured events.
    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    liteserv_version = params_from_base_test_setup["liteserv_versions"].split(',')[0]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peer_to_peer_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]

    if liteserv_version < "2.5.0":
        pytest.skip("Eventing feature is available only onwards CBL 2.5.0")

    if attachments:
        client_doc_ids = db_obj_client.create_bulk_docs(num_of_docs, "client_doc", db=cbl_db_client,
                                                        channels=channels,
                                                        attachments_generator=attachment.generate_png_100_100)
        server_doc_ids = db_obj_server.create_bulk_docs(num_of_docs, "server_doc", db=cbl_db_server,
                                                        channels=channels,
                                                        attachments_generator=attachment.generate_png_100_100)
    else:
        client_doc_ids = db_obj_client.create_bulk_docs(num_of_docs, "client_doc", db=cbl_db_client,
                                                        channels=channels)
        server_doc_ids = db_obj_server.create_bulk_docs(num_of_docs, "server_doc", db=cbl_db_server,
                                                        channels=channels)

    # Now set up client

    repl = peer_to_peer_client.configure(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client,
                                         continuous=continuous, replication_type=replicator_type,
                                         endPointType=endpoint_type)
    repl_listener = peer_to_peer_client.addReplicatorEventChangeListener(repl)
    peer_to_peer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    event_changes = peer_to_peer_client.getReplicatorEventChanges(repl_listener)
    assert total == completed, "replication from client to server did not completed " + \
                               str(total) + " not equal to " + str(completed)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    client_docs_count = db_obj_client.getCount(cbl_db_client)
    assert server_docs_count == 2 * num_of_docs, "Number of docs is not equivalent to number of docs in Server "
    assert client_docs_count == 2 * num_of_docs, "Number of docs is not equivalent to number of docs in Client "
    replicator.stop(repl)
    event_dict = get_event_changes(event_changes)
    push_docs = []
    pull_docs = []
    error_docs = []
    for doc in event_dict:
        if event_dict[doc]['push'] is True:
            push_docs.append(doc)
        else:
            pull_docs.append(doc)
        if event_dict[doc]['error_code'] is not None:
            error_docs.append({doc: "{}, {}".format(event_dict[doc]['error_code'],
                                                    event_dict[doc]['error_domain'])})

    # 5. Validating the event counts and verifying the push and pull event against doc_ids
    assert sorted(push_docs) == sorted(
        client_doc_ids), "Replication event push docs are not equal to expected no. of docs to be pushed"
    assert sorted(pull_docs) == sorted(
        server_doc_ids), "Replication event pull docs are not equal to expected no. of docs to be pulled"
    assert len(error_docs) == 0, "Error found in replication events {}".format(error_docs)


@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, endpoint_type", [
    (10, "URLEndPoint"),
    (100, "URLEndPoint"),
    (10, "MessageEndPoint"),
    (100, "MessageEndPoint"),
])
def test_peer_to_peer_push_replication_error_event(params_from_base_test_setup, server_setup,
                                                   num_of_docs, endpoint_type):
    """
    @summary:
    1. Add docs to both client and server
    2. Replicate with push and pull, so that both peers have same no. of docs
    3. Update docs on both server and client to create conflicts for replication
    4. Replicate using push replication and capture events with replication event listener
    5. Verify event listener capture error events for conflict.
    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    liteserv_version = params_from_base_test_setup["liteserv_versions"].split(',')[0]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peer_to_peer_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]

    if liteserv_version < "2.5.0":
        pytest.skip("Eventing feature is available only onwards CBL 2.5.0")

    client_doc_ids = db_obj_client.create_bulk_docs(num_of_docs, "client_doc", db=cbl_db_client,
                                                    channels=channels)
    server_doc_ids = db_obj_server.create_bulk_docs(num_of_docs, "server_doc", db=cbl_db_server,
                                                    channels=channels)
    # Now set up client
    repl = peer_to_peer_client.configure(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client,
                                         replication_type="push_pull", endPointType=endpoint_type)
    peer_to_peer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    client_docs_count = db_obj_client.getCount(cbl_db_client)
    assert server_docs_count == len(client_doc_ids) + len(server_doc_ids), \
        "Number of docs is not equivalent to number of docs in Server "
    assert client_docs_count == len(client_doc_ids) + len(server_doc_ids), \
        "Number of docs is not equivalent to number of docs in Client "

    # updating doc on both server and client to create conflict
    db_obj_client.update_bulk_docs(database=cbl_db_client, number_of_updates=1, doc_ids=client_doc_ids)

    db_obj_server.update_bulk_docs(database=cbl_db_server, number_of_updates=2, doc_ids=client_doc_ids)

    # replication and waiting for conflict to create error event
    repl = peer_to_peer_client.configure(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client,
                                         replication_type="push", endPointType=endpoint_type)
    repl_listener = peer_to_peer_client.addReplicatorEventChangeListener(repl)
    peer_to_peer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    error_events = peer_to_peer_client.getReplicatorEventChanges(repl_listener)
    replicator.stop(repl)
    event_dict = get_event_changes(error_events)

    # verifying errors capture for conflicts
    assert len(event_dict) != 0, "No Event captured. Check the logs for detailed info"
    for doc_id in event_dict:
        assert '10409' in event_dict[doc_id]["error_code"], "Conflict error didn't happen. Error Code: {}".format(
            event_dict[doc_id]["error_code"])
    client_docs = db_obj_client.getBulkDocs(cbl_db_client)

    # verifying that replication doesn't overwrite the docs after conflict
    for doc in client_docs:
        if "client_doc" in doc:
            assert client_docs[doc]["updates-cbl"] == 1, \
                "Conflict error didn't stop replication of docs properly.\n {}".format(doc)


@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, endpoint_type", [
    (10, "URLEndPoint"),
    (100, "URLEndPoint"),
    (10, "MessageEndPoint"),
    (100, "MessageEndPoint"),
])
def test_peer_to_peer_replication_delete_event(params_from_base_test_setup, server_setup,
                                               num_of_docs, endpoint_type):
    """
    @summary:
    1. Add docs to both client and server
    2. Replicate with push and pull, so that both peers have same no. of docs
    3. Delete some docs on server
    4. Replicate using pull replication and capture events with replication event listener
    5. Verify event listener capture delete events.
    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    liteserv_version = params_from_base_test_setup["liteserv_versions"].split(',')[0]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peer_to_peer_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]

    if liteserv_version < "2.5.0":
        pytest.skip("Eventing feature is available only onwards CBL 2.5.0")

    client_doc_ids = db_obj_client.create_bulk_docs(num_of_docs, "client_doc", db=cbl_db_client,
                                                    channels=channels)
    server_doc_ids = db_obj_server.create_bulk_docs(num_of_docs, "server_doc", db=cbl_db_server,
                                                    channels=channels)
    # Now set up client
    repl = peer_to_peer_client.configure(host=server_host, server_db_name=db_name_server,
                                         client_database=cbl_db_client, replication_type="push_pull",
                                         endPointType=endpoint_type)
    peer_to_peer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    client_docs_count = db_obj_client.getCount(cbl_db_client)
    assert server_docs_count == len(client_doc_ids) + len(server_doc_ids), \
        "Number of docs is not equivalent to number of docs in Server "
    assert client_docs_count == len(client_doc_ids) + len(server_doc_ids), \
        "Number of docs is not equivalent to number of docs in Client "

    docs_to_delete = random.sample(client_doc_ids + server_doc_ids, (num_of_docs / 10) * 2)
    db_obj_server.delete_bulk_docs(database=cbl_db_server, doc_ids=docs_to_delete)

    # Starting the replication to replicate deleted docs
    repl_listener = peer_to_peer_client.addReplicatorEventChangeListener(repl)
    peer_to_peer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    error_events = peer_to_peer_client.getReplicatorEventChanges(repl_listener)
    replicator.stop(repl)
    event_dict = get_event_changes(error_events)
    assert len(event_dict) != 0, "Replication listener didn't caught events. Check app logs for detailed info"
    for doc_id in event_dict:
        assert event_dict[doc_id]["flags"] == "1" or event_dict[doc_id]["flags"] == "[DocumentFlagsDeleted]" or \
            event_dict[doc_id]["flags"] == "Deleted", \
            'Deleted flag is not tagged for document. Flag value: {}'.format(event_dict[doc_id]["flags"])
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    client_docs_count = db_obj_client.getCount(cbl_db_client)
    assert server_docs_count == client_docs_count, "Server and Client doesn't have equal no. of docs"
