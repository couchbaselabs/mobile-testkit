import pytest
from keywords import attachment
from CBLClient.PeerToPeer import PeerToPeer
from CBLClient.Collection import Collection
from CBLClient.Replication import Replication
from keywords.utils import random_string


@pytest.mark.p2p
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection", [
    # (10, True, "push_pull", False, "MessageEndPoint", random_string(6), random_string(6)),
    (100, False, "push_pull", False, "URLEndPoint", random_string(6), random_string(6))
])
def test_peer_to_peer(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, attachments, endPointType, scope, collection):
    """
        @summary: peer1 -> Peer2
        1. Create docs on peer1.
        2. Start the peer2
        3. Start replication from peer1.
        4. Verify replication is completed.
        5. Verify all docs got replicated on peer2 in all the collections and scopes
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

    # create collections in cbl1 and cbl2
    collection_server = db_obj_server.createCollection(cbl_db_server, collection, scope)
    collection_client = db_obj_client.createCollection(cbl_db_client, collection, scope)

    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel, attachments_generator=attachment.generate_2_png_10_10, collection=collection_client)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel, collection=collection_client)

    cols_rep_server = []
    cols_rep_client = []

    cols_rep_server.append(collection_server)
    cols_rep_client.append(collection_client)

    if endPointType == "URLEndPoint":
        replicator_tcp_listener = peerToPeer_server.server_start(cbl_db_server, collections=cols_rep_server)
        url_listener_port = peerToPeer_server.get_url_listener_port(replicator_tcp_listener)
    else:
        url_listener_port = 5000

    repl = peerToPeer_client.configureCollection(port=url_listener_port, host=server_host, server_db_name=db_name_server, continuous=continuous, replication_type=replicator_type, endPointType=endPointType, collections=cols_rep_client)

    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + str(total) + " not equal to " + str(completed)
    server_docs_count = col_obj_server.documentCount(collection_server)
    assert server_docs_count == num_of_docs, "Number of docs mismatch"
    replicator.stop(repl)
    if endPointType == "URLEndPoint":
        peerToPeer_server.server_stop(replicator_tcp_listener, endPointType)
