import pytest
from keywords import attachment
from CBLClient.PeerToPeer import PeerToPeer
from CBLClient.Collection import Collection
from keywords.utils import log_info
from keywords.utils import add_new_fields_to_doc
from CBLClient.Replication import Replication
from keywords.utils import random_string


@pytest.mark.p2p
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection", [
    (100, False, "push", False, "URLEndPoint", random_string(6), random_string(6))
])
def test_p2p_sync_all_data(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection):
    """
        @summary: peer_server -> Peer_client
        1. Create a named collection in peer_server and peer_client
        2. Create docs on peer_client in default collection a named collection.
        3. Start the peer_server
        4. Start replication from peer_client.
        5. Verify replication is completed.
        6. Verify all docs got replicated on peer_server in all the collections and scopes
    """
    base_url_list = server_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channel = ["peerToPeer"]
    base_url_server = base_url_list[0]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    col_obj_server = Collection(base_url_list[0])
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    server_host = host_list[0]

    # 1. Create collections in peer_server and peer_client.
    collection_server = db_obj_server.createCollection(cbl_db_server, collection, scope)
    defaultCollection_server = db_obj_server.defaultCollection(cbl_db_server)
    collection_client = db_obj_client.createCollection(cbl_db_client, collection, scope)
    defaultCollection_client = db_obj_client.defaultCollection(cbl_db_client)

    # 2. Create docs on peer_client in default collection a named collection.
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel, attachments_generator=attachment.generate_2_png_10_10, collection=collection_client)
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel, attachments_generator=attachment.generate_2_png_10_10)

    else:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel, collection=collection_client)
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)

    cols_rep_server = []
    cols_rep_client = []

    cols_rep_server.append(collection_server)
    cols_rep_server.append(defaultCollection_server)
    cols_rep_client.append(collection_client)
    cols_rep_client.append(defaultCollection_client)

    # 3. Start the peer2
    if endPointType == "URLEndPoint":
        replicator_tcp_listener = peerToPeer_server.server_start(cbl_db_server, collections=cols_rep_server)
        url_listener_port = peerToPeer_server.get_url_listener_port(replicator_tcp_listener)
    else:
        url_listener_port = 5000

    # 4. Start replication from peer_client.
    repl = peerToPeer_client.configureCollection(port=url_listener_port, host=server_host, server_db_name=db_name_server, continuous=continuous, replication_type=replicator_type, endPointType=endPointType, collections=cols_rep_client)

    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)

    # 5. Verify replication is completed.
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not complete " + str(total) + " not equal to " + str(completed)

    # Verify all docs got replicated on peer_server in all the collections and scopes
    server_collection_docs_count = col_obj_server.documentCount(collection_server)
    server_default_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_collection_docs_count == num_of_docs, "Number of docs mismatch in collection"
    assert server_default_docs_count == num_of_docs, "Number of docs mismatch in default collection"
    replicator.stop(repl)
    if endPointType == "URLEndPoint":
        peerToPeer_server.server_stop(replicator_tcp_listener, endPointType)


@pytest.mark.p2p
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection", [
    (10, False, "push_pull", False, "URLEndPoint", random_string(6), random_string(6))
])
def test_p2p_sync_only_dataX(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection):
    """
        @summary: peer_server -> Peer_client
        1. Create a named collection in peer_server and peer_client
        2. Create docs on peer_client in default collection a named collection.
        3. Modify docs in CBL so that we can do push replication. The replication will have filter for newly added field
        4. Start the peer_server
        4. Start replication from peer_client.
        6. Verify replication is completed.
        7. Verify all docs got replicated on peer_server in all the collections and scopes
    """
    base_url_list = server_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_server = base_url_list[0]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    col_obj_server = Collection(base_url_list[0])
    col_obj_client = Collection(base_url_list[1])
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    server_host = host_list[0]

    # 1. Create collections in peer_server and peer_client.
    collection_server = db_obj_server.createCollection(cbl_db_server, collection, scope)
    collection_client = db_obj_client.createCollection(cbl_db_client, collection, scope)

    # 2. Create docs on peer_client in default collection a named collection.
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, attachments_generator=attachment.generate_2_png_10_10, collection=collection_client)
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, attachments_generator=attachment.generate_2_png_10_10)

    else:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, collection=collection_client)
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client)

    cols_rep_server = []
    cols_rep_client = []
    cols_client_config = []

    cols_rep_server.append(collection_server)
    cols_rep_client.append(collection_client)
    cols_client_config.append(replicator.collectionConfigure(pull_filter=True, push_filter=True, filter_callback_func="boolean", collection=collection_client))

    # 3. Modify docs in CBL so that we can do push replication. The replication will have filter for newly added field
    doc_ids = col_obj_client.getDocIds(collection_client)
    cbl_client_docs = col_obj_client.getDocuments(collection_client, doc_ids)
    updates_in_doc = {}
    for doc_id, doc_body in list(cbl_client_docs.items()):
        doc_body = add_new_fields_to_doc(doc_body)
        updates_in_doc[doc_id] = {
            "new_field_1": doc_body["new_field_1"],
            "new_field_2": doc_body["new_field_2"],
            "new_field_3": doc_body["new_field_3"],
        }
        col_obj_client.updateDocument(collection_client, data=doc_body, doc_id=doc_id)

    # 4. Start the peer2
    if endPointType == "URLEndPoint":
        replicator_tcp_listener = peerToPeer_server.server_start(cbl_db_server, collections=cols_rep_server)
        url_listener_port = peerToPeer_server.get_url_listener_port(replicator_tcp_listener)
    else:
        url_listener_port = 5000

    # 5. Start replication from peer_client.
    repl = peerToPeer_client.configureCollection(port=url_listener_port, host=server_host, server_db_name=db_name_server, continuous=continuous, replication_type=replicator_type, endPointType=endPointType, collections=cols_rep_client, collection_configuration=cols_client_config)

    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)

    # 6. Verify replication is completed.
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not complete " + str(total) + " not equal to " + str(completed)

    # 7. Verify all docs got replicated on peer_server in all the collections and scopes
    doc_ids = col_obj_server.getDocIds(collection_server)
    log_info(col_obj_server.getDocuments(collection_server, doc_ids))
    assert len(doc_ids) == num_of_docs, "Number of docs mismatch in collection"
    replicator.stop(repl)
    if endPointType == "URLEndPoint":
        peerToPeer_server.server_stop(replicator_tcp_listener, endPointType)


@pytest.mark.p2p
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection", [
    (100, False, "push", False, "URLEndPoint", random_string(6), random_string(6))
])
def test_p2p_scopeAcolA_to_scopeAcolA(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection):
    """
        @summary: peer_server -> Peer_client
        1. Create a named collection in peer_server and peer_client
        2. Create docs on peer_client in default collection a named collection.
        3. Start the peer_server
        4. Start replication from peer_client.
        5. Verify replication is completed.
        6. Verify all docs got replicated on peer_server in all the collections and scopes
    """
    base_url_list = server_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channel = ["peerToPeer"]
    base_url_server = base_url_list[0]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    col_obj_server = Collection(base_url_list[0])
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    server_host = host_list[0]

    # 1. Create collections in peer_server and peer_client.
    collection_server = db_obj_server.createCollection(cbl_db_server, collection, scope)
    collection_client = db_obj_client.createCollection(cbl_db_client, collection, scope)

    # 2. Create docs on peer_client in default collection a named collection.
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel, attachments_generator=attachment.generate_2_png_10_10, collection=collection_client)

    else:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel, collection=collection_client)

    cols_rep_server = []
    cols_rep_client = []

    cols_rep_server.append(collection_server)
    cols_rep_client.append(collection_client)

    # 3. Start the peer2
    if endPointType == "URLEndPoint":
        replicator_tcp_listener = peerToPeer_server.server_start(cbl_db_server, collections=cols_rep_server)
        url_listener_port = peerToPeer_server.get_url_listener_port(replicator_tcp_listener)
    else:
        url_listener_port = 5000

    # 4. Start replication from peer_client.
    repl = peerToPeer_client.configureCollection(port=url_listener_port, host=server_host, server_db_name=db_name_server, continuous=continuous, replication_type=replicator_type, endPointType=endPointType, collections=cols_rep_client)

    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)

    # 5. Verify replication is completed.
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not complete " + str(total) + " not equal to " + str(completed)

    # Verify all docs got replicated on peer_server in all the collections and scopes
    server_collection_docs_count = col_obj_server.documentCount(collection_server)
    assert server_collection_docs_count == num_of_docs, "Number of docs mismatch in collection"
    replicator.stop(repl)
    if endPointType == "URLEndPoint":
        peerToPeer_server.server_stop(replicator_tcp_listener, endPointType)


@pytest.mark.p2p
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection", [
    (100, False, "push", False, "URLEndPoint", random_string(6), random_string(6))
])
def test_p2p_sync_default_to_default(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection):
    """
        @summary: peer_server -> Peer_client
        1. Create a named collection in peer_server and peer_client
        2. Create docs on peer_client in default collection a named collection.
        3. Start the peer_server
        4. Start replication from peer_client.
        5. Verify replication is completed.
        6. Verify all docs got replicated on peer_server in all the collections and scopes
    """
    base_url_list = server_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channel = ["peerToPeer"]
    base_url_server = base_url_list[0]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    server_host = host_list[0]

    # 1. Create collections in peer_server and peer_client.
    defaultCollection_server = db_obj_server.defaultCollection(cbl_db_server)
    defaultCollection_client = db_obj_client.defaultCollection(cbl_db_client)

    # 2. Create docs on peer_client in default collection a named collection.
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel, attachments_generator=attachment.generate_2_png_10_10)

    else:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)

    cols_rep_server = []
    cols_rep_client = []

    cols_rep_server.append(defaultCollection_server)
    cols_rep_client.append(defaultCollection_client)

    # 3. Start the peer2
    if endPointType == "URLEndPoint":
        replicator_tcp_listener = peerToPeer_server.server_start(cbl_db_server, collections=cols_rep_server)
        url_listener_port = peerToPeer_server.get_url_listener_port(replicator_tcp_listener)
    else:
        url_listener_port = 5000

    # 4. Start replication from peer_client.
    repl = peerToPeer_client.configureCollection(port=url_listener_port, host=server_host, server_db_name=db_name_server, continuous=continuous, replication_type=replicator_type, endPointType=endPointType, collections=cols_rep_client)

    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)

    # 5. Verify replication is completed.
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not complete " + str(total) + " not equal to " + str(completed)

    # Verify all docs got replicated on peer_server in all the collections and scopes
    server_default_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_default_docs_count == num_of_docs, "Number of docs mismatch in default collection"
    replicator.stop(repl)
    if endPointType == "URLEndPoint":
        peerToPeer_server.server_stop(replicator_tcp_listener, endPointType)
