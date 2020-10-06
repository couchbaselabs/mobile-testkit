import pytest
from keywords import attachment
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer


@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endPointType", [
    (10, True, "push_pull", False, "URLEndPoint"),
    (100, False, "push_pull", False, "URLEndPoint")
])
def test_peer_to_peer_mesh_topology(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type,
                                    attachments, endPointType):
    """
        @summary: peer1<-> Peer2, Peer1 <->Peer3, Peer2<->peer1, Peer2<->Peer3
        1. Create docs on peer1.
        2. Start the peer2,3.
        3. Start replication from peer1.
        4. Verify replication is completed.
        5. Verify all docs got replicated on peer2,3
        6. Create docs on peer2
        7. Start replication from peer2.
        8. Verify replication is completed.
        9. Verify all docs got replicated on peer2,3
        10. Create docs on peer3
        11. Start replication from peer3
        12. Verify all docs got replicated on peer1,2
    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]

    peer1_replicator = Replication(base_url_list[0])
    peer2_replicator = Replication(base_url_list[1])
    peer3_replicator = Replication(base_url_list[2])

    peer_to_peer1 = PeerToPeer(base_url_list[0])
    peer_to_peer2 = PeerToPeer(base_url_list[1])
    peer_to_peer3 = PeerToPeer(base_url_list[2])

    db_obj_peer1 = db_obj_list[0]
    db_obj_peer2 = db_obj_list[1]
    db_obj_peer3 = db_obj_list[2]

    cbl_db_peer1 = cbl_db_list[0]
    cbl_db_peer2 = cbl_db_list[1]
    cbl_db_peer3 = cbl_db_list[2]

    db_name_peer1 = db_name_list[0]
    db_name_peer2 = db_name_list[1]
    db_name_peer3 = db_name_list[2]

    peer1_host = host_list[0]
    peer2_host = host_list[1]
    peer3_host = host_list[2]

    peer1_listener = peer_to_peer1.server_start(cbl_db_peer1)
    peer1_listener_port = peer_to_peer1.get_url_listener_port(peer1_listener)

    peer2_listener = peer_to_peer2.server_start(cbl_db_peer2)
    peer2_listener_port = peer_to_peer2.get_url_listener_port(peer2_listener)

    peer3_listener = peer_to_peer3.server_start(cbl_db_peer3)
    peer3_listener_port = peer_to_peer3.get_url_listener_port(peer3_listener)

    if attachments:
        db_obj_peer1.create_bulk_docs(num_of_docs, "p2preplication", db=cbl_db_peer2, channels=channels,
                                      attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_peer1.create_bulk_docs(num_of_docs, "p2preplication", db=cbl_db_peer2, channels=channels)

    # Peer1 connected peer2 replicator and peer3 replicator
    peer2_repl1 = peer_to_peer2.configure(port=peer1_listener_port, host=peer1_host, server_db_name=db_name_peer1,
                                          client_database=cbl_db_peer2,
                                          continuous=continuous, replication_type=replicator_type,
                                          endPointType=endPointType)
    peer_to_peer2.client_start(peer2_repl1)
    peer2_replicator.wait_until_replicator_idle(peer2_repl1)

    peer3_repl1 = peer_to_peer3.configure(port=peer1_listener_port, host=peer1_host, server_db_name=db_name_peer1,
                                          client_database=cbl_db_peer3,
                                          continuous=continuous, replication_type=replicator_type,
                                          endPointType=endPointType)
    peer_to_peer3.client_start(peer3_repl1)
    peer3_replicator.wait_until_replicator_idle(peer3_repl1)

    total = peer2_replicator.getTotal(peer2_repl1)
    completed = peer2_replicator.getCompleted(peer2_repl1)
    assert total == completed, "replication from peer1 to peer2 did not completed " + str(
        total) + " not equal to " + str(completed)

    total = peer3_replicator.getTotal(peer3_repl1)
    completed = peer3_replicator.getCompleted(peer3_repl1)
    assert total == completed, "replication from peer1 to peer3 did not completed " + total + " not equal to " + completed
    server_docs_count1 = db_obj_peer2.getCount(cbl_db_peer2)
    server_docs_count2 = db_obj_peer3.getCount(cbl_db_peer3)
    assert server_docs_count1 == num_of_docs, "Number of docs is not equivalent to number of docs in peer2 "
    assert server_docs_count2 == num_of_docs, "Number of docs is not equivalent to number of docs in peer3 "

    # Peer 2 connecting to peer 1 and Peer3
    if attachments:
        db_obj_peer2.create_bulk_docs(num_of_docs, "replication-peer2", db=cbl_db_peer2, channels=channels,
                                      attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_peer2.create_bulk_docs(num_of_docs, "replication-peer2", db=cbl_db_peer2, channels=channels)

    # Peer2 connected peer1 replicator and peer3 replicator
    peer1_repl1 = peer_to_peer1.configure(port=peer2_listener_port, host=peer2_host, server_db_name=db_name_peer2,
                                          client_database=cbl_db_peer2,
                                          continuous=continuous, replication_type=replicator_type,
                                          endPointType=endPointType)
    peer_to_peer1.client_start(peer1_repl1)
    peer1_replicator.wait_until_replicator_idle(peer1_repl1)

    peer3_repl2 = peer_to_peer3.configure(port=peer2_listener_port, host=peer2_host, server_db_name=db_name_peer2,
                                          client_database=cbl_db_peer3,
                                          continuous=continuous, replication_type=replicator_type,
                                          endPointType=endPointType)
    peer_to_peer3.client_start(peer3_repl2)
    peer3_replicator.wait_until_replicator_idle(peer3_repl2)

    total = peer1_replicator.getTotal(peer1_repl1)
    completed = peer1_replicator.getCompleted(peer1_repl1)
    assert total == completed, "replication from peer2 to peer1 did not completed " + str(
        total) + " not equal to " + str(completed)

    total = peer3_replicator.getTotal(peer3_repl2)
    completed = peer3_replicator.getCompleted(peer3_repl2)
    assert total == completed, "replication from peer2 to peer3 did not completed " + total + " not equal to " + completed

    server_docs_count1 = db_obj_peer1.getCount(cbl_db_peer1)
    server_docs_count2 = db_obj_peer3.getCount(cbl_db_peer3)
    assert server_docs_count1 == num_of_docs * 2, "Number of docs is not equivalent to number of docs in peer1 "
    assert server_docs_count2 == num_of_docs * 2, "Number of docs is not equivalent to number of docs in peer3 "

    # Peer 3 connecting to peer 1 and Peer2
    if attachments:
        db_obj_peer3.create_bulk_docs(num_of_docs, "replication-peer3", db=cbl_db_peer3, channels=channels,
                                      attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_peer3.create_bulk_docs(num_of_docs, "replication-peer3", db=cbl_db_peer3, channels=channels)

    # Peer2 connected peer1 replicator and peer3 replicator
    peer1_repl2 = peer_to_peer1.configure(port=peer3_listener_port, host=peer3_host, server_db_name=db_name_peer3,
                                          client_database=cbl_db_peer1,
                                          continuous=continuous, replication_type=replicator_type,
                                          endPointType=endPointType)
    peer_to_peer1.client_start(peer1_repl2)
    peer1_replicator.wait_until_replicator_idle(peer1_repl2)

    peer2_repl2 = peer_to_peer2.configure(port=peer3_listener_port, host=peer3_host, server_db_name=db_name_peer3,
                                          client_database=cbl_db_peer2,
                                          continuous=continuous, replication_type=replicator_type,
                                          endPointType=endPointType)
    peer_to_peer2.client_start(peer2_repl2)
    peer2_replicator.wait_until_replicator_idle(peer2_repl2)

    total = peer1_replicator.getTotal(peer1_repl2)
    completed = peer1_replicator.getCompleted(peer1_repl2)
    assert total == completed, "replication from peer2 to peer1 did not completed " + str(
        total) + " not equal to " + str(completed)

    total = peer2_replicator.getTotal(peer2_repl2)
    completed = peer2_replicator.getCompleted(peer2_repl2)
    assert total == completed, "replication from peer2 to peer3 did not completed " + total + " not equal to " + completed

    peer1_replicator.stop(peer1_repl1)
    peer1_replicator.stop(peer1_repl2)

    peer2_replicator.stop(peer2_repl1)
    peer2_replicator.stop(peer2_repl2)

    peer3_replicator.stop(peer3_repl1)
    peer3_replicator.stop(peer3_repl2)

    peer_to_peer1.server_stop(peer1_listener, endPointType)
    peer_to_peer2.server_stop(peer2_listener, endPointType)
    peer_to_peer3.server_stop(peer3_listener, endPointType)

    peer1_docs = db_obj_peer1.getCount(cbl_db_peer1)
    peer2_docs = db_obj_peer2.getCount(cbl_db_peer2)
    peer3_docs = db_obj_peer3.getCount(cbl_db_peer3)
    assert peer1_docs == peer3_docs, "Number of docs is not equivalent to number of docs in peer1 "
    assert peer2_docs == peer3_docs, "Number of docs is not equivalent to number of docs in peer3 "


@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endPointType", [
    (10, True, "push_pull", False, "URLEndPoint"),
    (100, False, "pull", False, "URLEndPoint"),
])
def test_peer_to_peer_loop_topology(params_from_base_test_setup, server_setup, num_of_docs, continuous,
                                    replicator_type,
                                    attachments, endPointType):
    """
        @summary: peer1<-> Peer2, Peer2 <->Peer3, Peer3<->peer1
        1. Create docs on peer1.
        2. Start the peer2.
        3. Start replication from peer1.
        4. Verify replication is completed.
        5. Verify all docs got replicated on peer2
        6. Create docs on peer2
        7. Start replication from peer3.
        8. Verify replication is completed.
        9. Verify all docs got replicated on peer3
        10. Create docs on peer3
        11. Start replication from peer3
        12. Verify all docs got replicated on peer1
    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]

    peer1_replicator = Replication(base_url_list[0])
    peer2_replicator = Replication(base_url_list[1])
    peer3_replicator = Replication(base_url_list[2])

    peer_to_peer1 = PeerToPeer(base_url_list[0])
    peer_to_peer2 = PeerToPeer(base_url_list[1])
    peer_to_peer3 = PeerToPeer(base_url_list[2])

    db_obj_peer1 = db_obj_list[0]
    db_obj_peer2 = db_obj_list[1]
    db_obj_peer3 = db_obj_list[2]

    cbl_db_peer1 = cbl_db_list[0]
    cbl_db_peer2 = cbl_db_list[1]
    cbl_db_peer3 = cbl_db_list[2]

    db_name_peer1 = db_name_list[0]
    db_name_peer2 = db_name_list[1]
    db_name_peer3 = db_name_list[2]

    peer1_host = host_list[0]
    peer2_host = host_list[1]
    peer3_host = host_list[2]

    peer1_listener = peer_to_peer1.server_start(cbl_db_peer1)
    peer1_listener_port = peer_to_peer1.get_url_listener_port(peer1_listener)

    peer2_listener = peer_to_peer2.server_start(cbl_db_peer2)
    peer2_listener_port = peer_to_peer2.get_url_listener_port(peer2_listener)

    peer3_listener = peer_to_peer3.server_start(cbl_db_peer3)
    peer3_listener_port = peer_to_peer3.get_url_listener_port(peer3_listener)

    if attachments:
        db_obj_peer1.create_bulk_docs(num_of_docs, "replication1", db=cbl_db_peer1, channels=channels,
                                      attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_peer1.create_bulk_docs(num_of_docs, "replication1", db=cbl_db_peer1, channels=channels)

    # Peer1 connected peer2 replicator
    peer2_repl1 = peer_to_peer2.configure(port=peer1_listener_port, host=peer1_host, server_db_name=db_name_peer1,
                                          client_database=cbl_db_peer2,
                                          continuous=continuous, replication_type=replicator_type,
                                          endPointType=endPointType)
    peer_to_peer2.client_start(peer2_repl1)
    peer2_replicator.wait_until_replicator_idle(peer2_repl1)

    total = peer2_replicator.getTotal(peer2_repl1)
    completed = peer2_replicator.getCompleted(peer2_repl1)
    assert total == completed, "replication from peer1 to peer2 did not completed " + str(
        total) + " not equal to " + str(completed)

    server_docs_count1 = db_obj_peer2.getCount(cbl_db_peer2)
    assert server_docs_count1 == num_of_docs, "Number of docs is not equivalent to number of docs in peer2 "

    # Peer 2 connecting to  Peer3
    if attachments:
        db_obj_peer2.create_bulk_docs(num_of_docs, "replication2", db=cbl_db_peer2, channels=channels,
                                      attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_peer2.create_bulk_docs(num_of_docs, "replication2", db=cbl_db_peer2, channels=channels)

    # Peer2 connected peer1 replicator and peer3 replicator

    peer3_repl1 = peer_to_peer3.configure(port=peer2_listener_port, host=peer2_host, server_db_name=db_name_peer2,
                                          client_database=cbl_db_peer3,
                                          continuous=continuous, replication_type=replicator_type,
                                          endPointType=endPointType)
    peer_to_peer3.client_start(peer3_repl1)
    peer3_replicator.wait_until_replicator_idle(peer3_repl1)

    total = peer3_replicator.getTotal(peer3_repl1)
    completed = peer3_replicator.getCompleted(peer3_repl1)
    assert total == completed, "replication from peer2 to peer3 did not completed " + total + " not equal to " + completed
    peer3_docs = db_obj_peer3.getCount(cbl_db_peer3)
    assert peer3_docs == db_obj_peer2.getCount(cbl_db_peer2), "Number of docs is not equivalent to number of docs in peer3 "

    # Peer 3 connecting to peer 1
    if attachments:
        db_obj_peer3.create_bulk_docs(num_of_docs, "replication3", db=cbl_db_peer3, channels=channels,
                                      attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_peer3.create_bulk_docs(num_of_docs, "replication3", db=cbl_db_peer3, channels=channels)

    # Peer2 connected peer1 replicator and peer3 replicator
    peer1_repl1 = peer_to_peer1.configure(port=peer3_listener_port, host=peer3_host, server_db_name=db_name_peer3,
                                          client_database=cbl_db_peer1,
                                          continuous=continuous, replication_type=replicator_type,
                                          endPointType=endPointType)
    peer_to_peer1.client_start(peer1_repl1)
    peer1_replicator.wait_until_replicator_idle(peer1_repl1)

    total = peer1_replicator.getTotal(peer1_repl1)
    completed = peer1_replicator.getCompleted(peer1_repl1)
    assert total == completed, "replication from peer2 to peer1 did not completed " + str(
        total) + " not equal to " + str(completed)

    server_docs_count1 = db_obj_peer1.getCount(cbl_db_peer1)
    assert server_docs_count1 == num_of_docs * 3, "Number of docs is not equivalent to number of docs in peer1 "

    peer1_replicator.stop(peer1_repl1)
    peer2_replicator.stop(peer2_repl1)
    peer3_replicator.stop(peer3_repl1)

    peer_to_peer1.server_stop(peer1_listener, endPointType)
    peer_to_peer2.server_stop(peer2_listener, endPointType)
    peer_to_peer3.server_stop(peer3_listener, endPointType)
