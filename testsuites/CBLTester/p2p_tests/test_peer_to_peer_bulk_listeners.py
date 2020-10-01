import pytest

from keywords import attachment
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer


@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType, with_certs", [
    (True, "push_pull", "URLEndPoint", True),
    (False, "push", "URLEndPoint", True)
])
def test_peer_to_peer_many_listeners_replicators(params_from_base_test_setup, server_setup, continuous, replicator_type,
                                            endPointType, with_certs):
    """
        @summary:
        1. Start the 10 listeners
        2. Start 10 replicators on client
        3. Verify replication is completed.
        4. Verify all docs got replicated on listener
    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]

    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    peer_to_peer_server = PeerToPeer(base_url_list[0])
    message_url_tcp_listener = server_setup["message_url_tcp_listener"]
    peer_to_peer_server.server_stop(message_url_tcp_listener, "MessageEndPoint")

    server_host = host_list[0]
    num_of_docs = 50
    port_array = []
    repl = []
    listeners = []
    for i in range(10):
        url_listener = peer_to_peer_server.server_start(cbl_db_server, tls_disable=with_certs)
        url_listener_port = peer_to_peer_server.get_url_listener_port(url_listener)
        listeners.append(url_listener)
        port_array.append(url_listener_port)

    db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                   attachments_generator=attachment.generate_png_100_100)

    # Now set up client
    for i in range(10):
        repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server,
                                           client_database=cbl_db_client, continuous=continuous,
                                           replication_type=replicator_type, endPointType=endPointType,
                                           port=port_array[i], tls_disable=with_certs, server_verification_mode=with_certs)

        peerToPeer_client.client_start(repl)
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "replication from client to server did not completed " + str(
            total) + " not equal to " + str(completed)
        server_docs_count = db_obj_server.getCount(cbl_db_server)
        assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
        replicator.stop(repl)
    for i in range(10):
        peer_to_peer_server.server_stop(listeners[i], replicator_type)
